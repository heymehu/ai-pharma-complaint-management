from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field
from app.models import ComplaintStatus, Priority, RiskLevel, UserRole


class ComplaintExtractRequest(BaseModel):
    text: str
    session_id: Optional[str] = None


class ComplaintFields(BaseModel):
    complaint_source: Optional[str] = None
    customer_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    complaint_date: Optional[str] = None
    product_name: Optional[str] = None
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    batch_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    quantity: Optional[str] = None
    summary: Optional[str] = None


class AIInvestigationSuggestion(BaseModel):
    possible_root_cause: Optional[str] = None
    risk_level: Optional[str] = None
    affected_batches: Optional[str] = None
    regulatory_concern: Optional[str] = None
    impact: Optional[str] = None
    confidence_score: Optional[float] = None
    potential_issue: Optional[str] = None
    suggested_test: Optional[str] = None
    priority: Optional[str] = None
    recommended_action: Optional[str] = None
    ai_reasoning: Optional[str] = None
    required_tests: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    regulatory_implications: list[str] = Field(default_factory=list)
    escalation_level: Optional[str] = None
    risk_category: Optional[str] = None
    deviation_possibility: Optional[str] = None


class ExtractResponse(BaseModel):
    fields: ComplaintFields
    investigation: AIInvestigationSuggestion
    message: str
    duplicates: list[dict[str, Any]] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str
    session_id: str
    complaint_id: Optional[int] = None
    form_data: Optional[dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply: str
    fields: Optional[ComplaintFields] = None
    investigation: Optional[AIInvestigationSuggestion] = None
    action: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class ComplaintCreate(BaseModel):
    complaint_source: Optional[str] = None
    customer_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    complaint_date: Optional[datetime] = None
    product_name: Optional[str] = None
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    batch_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    quantity: Optional[str] = None
    summary: Optional[str] = None
    raw_text: Optional[str] = None
    possible_root_cause: Optional[str] = None
    risk_level: Optional[RiskLevel] = None
    priority: Optional[Priority] = None
    affected_batches: Optional[str] = None
    regulatory_concern: Optional[str] = None
    impact: Optional[str] = None
    confidence_score: Optional[float] = None
    potential_issue: Optional[str] = None
    suggested_test: Optional[str] = None
    recommended_action: Optional[str] = None
    ai_reasoning: Optional[str] = None
    ai_suggestions: Optional[dict[str, Any]] = None


class ComplaintBulkDelete(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)


class ComplaintUpdate(ComplaintCreate):
    status: Optional[ComplaintStatus] = None


class ComplaintOut(BaseModel):
    id: int
    complaint_id: str
    complaint_source: Optional[str] = None
    customer_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    complaint_date: Optional[datetime] = None
    product_name: Optional[str] = None
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    batch_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    quantity: Optional[str] = None
    summary: Optional[str] = None
    status: ComplaintStatus
    priority: Priority
    risk_level: RiskLevel
    severity_score: float = 0.0
    possible_root_cause: Optional[str] = None
    affected_batches: Optional[str] = None
    regulatory_concern: Optional[str] = None
    impact: Optional[str] = None
    confidence_score: Optional[float] = None
    potential_issue: Optional[str] = None
    suggested_test: Optional[str] = None
    recommended_action: Optional[str] = None
    ai_reasoning: Optional[str] = None
    ai_suggestions: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvestigationOut(BaseModel):
    id: int
    complaint_id: int
    summary: Optional[str] = None
    root_cause_analysis: Optional[str] = None
    fishbone_analysis: Optional[dict[str, Any]] = None
    five_why_analysis: Optional[list[Any]] = None
    risk_assessment: Optional[str] = None
    recommended_capa: Optional[str] = None
    preventive_actions: Optional[str] = None
    timeline: Optional[str] = None
    owner: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CAPAOut(BaseModel):
    id: int
    complaint_id: int
    title: Optional[str] = None
    corrective_actions: Optional[str] = None
    preventive_actions: Optional[str] = None
    owner: Optional[str] = None
    status: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_complaints: int
    open_complaints: int
    critical_complaints: int
    resolved: int
    avg_resolution_days: float
    by_status: dict[str, int]
    by_month: list[dict[str, Any]]
    by_risk: dict[str, int]


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.QA_EXECUTIVE


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SearchRequest(BaseModel):
    query: str
    semantic: bool = False


class KnowledgeUploadMeta(BaseModel):
    title: str
    doc_type: str = "SOP"
