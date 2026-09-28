from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    require_user,
    verify_password,
)
from app.db.session import get_db
from app.models import (
    Attachment,
    AuditLog,
    CAPA,
    ChatHistory,
    Complaint,
    ComplaintStatus,
    Investigation,
    Priority,
    RiskLevel,
    User,
    UserRole,
)
from app.schemas import (
    AIInvestigationSuggestion,
    CAPAOut,
    ChatRequest,
    ChatResponse,
    ComplaintBulkDelete,
    ComplaintCreate,
    ComplaintExtractRequest,
    ComplaintFields,
    ComplaintOut,
    ComplaintUpdate,
    DashboardStats,
    ExtractResponse,
    InvestigationOut,

    TokenOut,
    UserCreate,
    UserLogin,
    UserOut,
)
from app.services.ai.copilot import (
    chat_with_copilot,
    extract_complaint,
    generate_capa,
    generate_customer_reply,
    generate_investigation,
)
from app.services.documents import extract_text_from_bytes, save_upload

from app.services.pdf import generate_complaint_pdf

router = APIRouter()
settings = get_settings()


def _next_complaint_id(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    count = db.query(Complaint).count() + 1
    return f"CMP-{year}-{count:05d}"


def _log(db: Session, action: str, entity_type: str = None, entity_id: str = None, details=None, user_id=None):
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            details=details,
        )
    )


def _apply_ai_fields(complaint: Complaint, inv) -> None:
    if not inv:
        return
    mapping = {
        "possible_root_cause": inv.possible_root_cause,
        "affected_batches": inv.affected_batches,
        "regulatory_concern": inv.regulatory_concern,
        "impact": inv.impact,
        "confidence_score": inv.confidence_score,
        "potential_issue": inv.potential_issue,
        "suggested_test": inv.suggested_test,
        "recommended_action": inv.recommended_action,
        "ai_reasoning": inv.ai_reasoning,
    }
    for k, v in mapping.items():
        if v is not None:
            setattr(complaint, k, v)
    if inv.risk_level:
        try:
            complaint.risk_level = RiskLevel(inv.risk_level.lower())
        except ValueError:
            pass
    if inv.priority:
        try:
            complaint.priority = Priority(inv.priority.lower())
        except ValueError:
            pass
    complaint.ai_suggestions = inv.model_dump()


# ---------- Auth ----------
@router.post("/auth/register", response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/auth/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token({"sub": user.email, "role": user.role.value})
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(require_user)):
    return user


# ---------- AI ----------
@router.post("/ai/extract", response_model=ExtractResponse)
async def ai_extract(payload: ComplaintExtractRequest, db: Session = Depends(get_db)):
    result = await extract_complaint(payload.text)
    # Duplicate detection by batch
    duplicates = []
    if result.fields.batch_number:
        existing = (
            db.query(Complaint)
            .filter(Complaint.batch_number == result.fields.batch_number)
            .limit(5)
            .all()
        )
        duplicates = [
            {
                "id": c.id,
                "complaint_id": c.complaint_id,
                "product_name": c.product_name,
                "summary": (c.summary or "")[:120],
                "status": c.status.value,
            }
            for c in existing
        ]
    result.duplicates = duplicates
    if payload.session_id:
        db.add(ChatHistory(session_id=payload.session_id, role="user", content=payload.text))
        db.add(ChatHistory(session_id=payload.session_id, role="assistant", content=result.message, metadata_json={"action": "extract"}))
        db.commit()
    return result


@router.post("/ai/chat", response_model=ChatResponse)
async def ai_chat(payload: ChatRequest, db: Session = Depends(get_db)):
    history_rows = (
        db.query(ChatHistory)
        .filter(ChatHistory.session_id == payload.session_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(10)
        .all()
    )
    history = [{"role": h.role, "content": h.content} for h in reversed(history_rows)]
    result = await chat_with_copilot(payload.message, payload.form_data, history)
    fields = result.get("fields")
    investigation = result.get("investigation")
    # Normalize to schema models
    if isinstance(fields, dict):
        fields = ComplaintFields(**fields)
    if isinstance(investigation, dict):
        investigation = AIInvestigationSuggestion(**investigation)
    db.add(
        ChatHistory(
            session_id=payload.session_id,
            complaint_id=payload.complaint_id,
            role="user",
            content=payload.message,
        )
    )
    db.add(
        ChatHistory(
            session_id=payload.session_id,
            complaint_id=payload.complaint_id,
            role="assistant",
            content=result["reply"],
            metadata_json={
                "action": result.get("action"),
                "updated_fields": (
                    {k: v for k, v in fields.model_dump().items() if v not in (None, "", [])}
                    if fields
                    else None
                ),
            },
        )
    )
    db.commit()
    return ChatResponse(
        reply=result["reply"],
        fields=fields,
        investigation=investigation,
        action=result.get("action") or ("fill_form" if fields else None),
    )


@router.post("/ai/investigate", response_model=InvestigationOut)
async def ai_investigate(payload: dict, db: Session = Depends(get_db)):
    form_data = payload.get("form_data") or payload
    complaint_id = payload.get("complaint_id")
    data = await generate_investigation(form_data)
    inv = Investigation(
        complaint_id=complaint_id or 0,
        summary=data.get("summary"),
        root_cause_analysis=data.get("root_cause_analysis"),
        fishbone_analysis=data.get("fishbone_analysis"),
        five_why_analysis=data.get("five_why_analysis"),
        risk_assessment=data.get("risk_assessment"),
        recommended_capa=data.get("recommended_capa"),
        preventive_actions=data.get("preventive_actions"),
        timeline=data.get("timeline"),
        owner=data.get("owner"),
    )
    if complaint_id:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if complaint:
            complaint.status = ComplaintStatus.INVESTIGATION
            db.add(inv)
            db.commit()
            db.refresh(inv)
            return inv
    # ephemeral — store with complaint_id 0 placeholder not allowed; return synthetic
    # Create temp response without DB if no complaint
    db.add(inv) if complaint_id else None
    # Return without persisting when no complaint_id by using a fake object pattern
    class _Tmp:
        pass

    tmp = _Tmp()
    tmp.id = 0
    tmp.complaint_id = complaint_id or 0
    tmp.summary = data.get("summary")
    tmp.root_cause_analysis = data.get("root_cause_analysis")
    tmp.fishbone_analysis = data.get("fishbone_analysis")
    tmp.five_why_analysis = data.get("five_why_analysis")
    tmp.risk_assessment = data.get("risk_assessment")
    tmp.recommended_capa = data.get("recommended_capa")
    tmp.preventive_actions = data.get("preventive_actions")
    tmp.timeline = data.get("timeline")
    tmp.owner = data.get("owner")
    tmp.created_at = datetime.now(timezone.utc)
    return tmp


@router.post("/ai/capa", response_model=CAPAOut)
async def ai_capa(payload: dict, db: Session = Depends(get_db)):
    form_data = payload.get("form_data") or payload
    complaint_id = payload.get("complaint_id")
    data = await generate_capa(form_data)
    capa = CAPA(
        complaint_id=complaint_id or 0,
        title=data.get("title"),
        corrective_actions=data.get("corrective_actions"),
        preventive_actions=data.get("preventive_actions"),
        owner=data.get("owner"),
        status=data.get("status", "open"),
        effectiveness_check=data.get("effectiveness_check"),
    )
    if complaint_id:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if complaint:
            complaint.status = ComplaintStatus.CAPA
            db.add(capa)
            db.commit()
            db.refresh(capa)
            return capa

    class _Tmp:
        pass

    tmp = _Tmp()
    tmp.id = 0
    tmp.complaint_id = complaint_id or 0
    tmp.title = data.get("title")
    tmp.corrective_actions = data.get("corrective_actions")
    tmp.preventive_actions = data.get("preventive_actions")
    tmp.owner = data.get("owner")
    tmp.status = data.get("status", "open")
    tmp.created_at = datetime.now(timezone.utc)
    return tmp


@router.post("/ai/customer-reply")
async def ai_customer_reply(payload: dict):
    form_data = payload.get("form_data") or payload
    reply = await generate_customer_reply(form_data)
    return {"reply": reply}


@router.post("/ai/upload")
async def ai_upload(
    file: UploadFile = File(...),
    session_id: str = Form(default=""),
    db: Session = Depends(get_db),
):
    content = await file.read()
    text = await extract_text_from_bytes(file.filename or "file", content, file.content_type or "")
    path = save_upload(settings.upload_dir, file.filename or "upload.bin", content)
    att = Attachment(
        filename=file.filename or "upload",
        file_path=path,
        content_type=file.content_type,
        size_bytes=len(content),
        extracted_text=text,
    )
    db.add(att)
    db.commit()
    extracted = await extract_complaint(text) if text and not text.startswith("[") else None
    return {
        "filename": file.filename,
        "extracted_text": text,
        "attachment_id": att.id,
        "extraction": extracted,
    }


@router.post("/ai/pdf")
async def ai_pdf(payload: dict):
    report_type = payload.get("report_type") or "Complaint Report"
    data = payload.get("form_data") or payload
    pdf_bytes = generate_complaint_pdf(data, report_type)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="aivoa-{report_type.lower().replace(" ", "-")}.pdf"'},
    )






# ---------- Complaints CRUD ----------
@router.post("/complaints", response_model=ComplaintOut)
def create_complaint(payload: ComplaintCreate, db: Session = Depends(get_db), user: User | None = Depends(get_current_user)):
    complaint = Complaint(
        complaint_id=_next_complaint_id(db),
        **payload.model_dump(exclude_unset=True),
        status=ComplaintStatus.PENDING,
    )
    if payload.risk_level is None and payload.ai_suggestions:
        pass
    db.add(complaint)
    _log(db, "complaint_created", "complaint", complaint.complaint_id, user_id=user.id if user else None)
    db.commit()
    db.refresh(complaint)
    return complaint


@router.get("/complaints", response_model=list[ComplaintOut])
def list_complaints(
    status: str | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(Complaint)
    if status:
        query = query.filter(Complaint.status == status)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Complaint.batch_number.ilike(like))
            | (Complaint.product_name.ilike(like))
            | (Complaint.customer_name.ilike(like))
            | (Complaint.complaint_id.ilike(like))
        )
    return query.order_by(Complaint.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/complaints/bulk-delete")
def delete_complaints(
    payload: ComplaintBulkDelete,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    complaint_ids = set(payload.ids)
    complaints = db.query(Complaint).filter(Complaint.id.in_(complaint_ids)).all()
    if len(complaints) != len(complaint_ids):
        raise HTTPException(404, "One or more complaints were not found")

    for complaint in complaints:
        _log(
            db,
            "complaint_deleted",
            "complaint",
            complaint.complaint_id,
            user_id=user.id if user else None,
        )
        db.delete(complaint)
    db.commit()
    return {"deleted_count": len(complaints), "deleted_ids": sorted(complaint_ids)}


@router.get("/complaints/{complaint_id}", response_model=ComplaintOut)
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(404, "Complaint not found")
    return c


@router.patch("/complaints/{complaint_id}", response_model=ComplaintOut)
def update_complaint(complaint_id: int, payload: ComplaintUpdate, db: Session = Depends(get_db)):
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(404, "Complaint not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    if payload.status == ComplaintStatus.CLOSED:
        c.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return c


@router.post("/complaints/{complaint_id}/advance", response_model=ComplaintOut)
def advance_status(complaint_id: int, db: Session = Depends(get_db)):
    c = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not c:
        raise HTTPException(404, "Complaint not found")
    flow = [
        ComplaintStatus.PENDING,
        ComplaintStatus.UNDER_REVIEW,
        ComplaintStatus.INVESTIGATION,
        ComplaintStatus.CAPA,
        ComplaintStatus.CLOSED,
    ]
    idx = flow.index(c.status) if c.status in flow else 0
    if idx < len(flow) - 1:
        c.status = flow[idx + 1]
        if c.status == ComplaintStatus.CLOSED:
            c.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(c)
    return c


# ---------- Dashboard ----------
@router.get("/dashboard/stats", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db)):
    all_c = db.query(Complaint).all()
    total = len(all_c)
    open_c = sum(1 for c in all_c if c.status != ComplaintStatus.CLOSED)
    critical = sum(1 for c in all_c if c.risk_level == RiskLevel.CRITICAL or c.priority == Priority.URGENT)
    resolved = sum(1 for c in all_c if c.status == ComplaintStatus.CLOSED)
    durations = []
    for c in all_c:
        if c.closed_at and c.created_at:
            closed = c.closed_at if c.closed_at.tzinfo else c.closed_at.replace(tzinfo=timezone.utc)
            created = c.created_at if c.created_at.tzinfo else c.created_at.replace(tzinfo=timezone.utc)
            durations.append((closed - created).total_seconds() / 86400)
    avg = sum(durations) / len(durations) if durations else 0.0

    by_status = {}
    by_risk = {}
    by_month_map: dict[str, int] = {}
    for c in all_c:
        by_status[c.status.value] = by_status.get(c.status.value, 0) + 1
        by_risk[c.risk_level.value] = by_risk.get(c.risk_level.value, 0) + 1
        key = c.created_at.strftime("%Y-%m") if c.created_at else "unknown"
        by_month_map[key] = by_month_map.get(key, 0) + 1
    by_month = [{"month": k, "count": v} for k, v in sorted(by_month_map.items())]

    return DashboardStats(
        total_complaints=total,
        open_complaints=open_c,
        critical_complaints=critical,
        resolved=resolved,
        avg_resolution_days=round(avg, 1),
        by_status=by_status,
        by_month=by_month,
        by_risk=by_risk,
    )


@router.get("/audit-logs")
def audit_logs(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "details": r.details,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version, "session_hint": str(uuid.uuid4())[:8]}
