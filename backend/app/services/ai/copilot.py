"""AI service layer with Gemini / intelligent mock fallback."""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.core.config import get_settings, clear_settings_cache
from app.schemas import AIInvestigationSuggestion, ComplaintFields, ExtractResponse

settings = get_settings()  # initial; runtime calls use get_settings()

EXTRACTION_SYSTEM = """You are AIVOA, an expert pharmaceutical quality complaint extraction engine.
Your job is to extract EXACT structured fields from informal text, emails, OCR, or dictation.

CRITICAL EXTRACTION RULES:
1. Read the full text carefully. Map each fact to the correct field only.
2. Never put narrative sentences into product_name or batch_number.
3. product_name = medicine/product brand or generic name only (e.g. "Dolo").
4. strength = dose strength only (e.g. "500 mg").
5. batch_number = alphanumeric lot/batch code only (e.g. "DXJS54641" or "DGH-287FDA").
6. customer_name = the person reporting (e.g. "Mehul Kumar"), NOT the pharmacy unless no person is named.
7. complaint_source = where purchased / reporting channel (e.g. "Apollo Pharmacy").
8. dosage_form from words like capsule/tablet/syrup (e.g. "Capsule").
9. quantity = numeric amount only (e.g. "10").
10. manufacturing_date / expiry_date keep the stated dates as given (normalize lightly, e.g. "March 2026", "2028").
11. summary = clean 1-3 sentence complaint narrative in professional English.
12. If a value is truly missing, use null — do not invent or guess product names from surrounding words.

Return ONLY valid JSON with this exact shape (no markdown):
{
  "fields": {
    "complaint_source": string|null,
    "customer_name": string|null,
    "email": string|null,
    "phone": string|null,
    "country": string|null,
    "complaint_date": string|null,
    "product_name": string|null,
    "strength": string|null,
    "dosage_form": string|null,
    "batch_number": string|null,
    "manufacturing_date": string|null,
    "expiry_date": string|null,
    "quantity": string|null,
    "summary": string|null
  },
  "investigation": {
    "possible_root_cause": string,
    "risk_level": "low"|"medium"|"high"|"critical",
    "affected_batches": string,
    "regulatory_concern": string,
    "impact": string,
    "confidence_score": number between 0 and 1,
    "potential_issue": string,
    "suggested_test": string,
    "priority": "low"|"medium"|"high"|"urgent",
    "recommended_action": string,
    "ai_reasoning": string,
    "required_tests": [string],
    "missing_information": [string],
    "regulatory_implications": [string],
    "escalation_level": string,
    "risk_category": string,
    "deviation_possibility": string
  },
  "message": string
}
"""

CHAT_SYSTEM = """You are AIVOA AI Copilot for pharmaceutical complaint management.
You help QA teams: extract complaints, summarize, generate investigations, CAPA, FDA reports,
customer replies, root cause suggestions, severity classification, and lab test recommendations.
Be precise, regulatory-aware (FDA 21 CFR, WHO GMP), and concise.
When you extract or update form fields, include a JSON block marked with <<<FORM>>> ... <<<END>>>
using the same fields/investigation schema as extraction.
"""


def _parse_json_blob(text: str) -> dict[str, Any]:
    text = text.strip()
    # Strip markdown fences
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {}


def _mock_extract(text: str) -> ExtractResponse:
    """Rule-based extraction for offline / demo mode (matches Apollo Pharmacy demo)."""
    lower = text.lower()
    fields = ComplaintFields()
    investigation = AIInvestigationSuggestion()
    stop = {"is", "was", "are", "the", "a", "an", "my", "no", "number", "lot", "batch"}

    # Person name: "my name is X" / "I am X"
    name_match = re.search(
        r"(?:my\s+name\s+is|i\s+am)\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,3})",
        text,
        re.I,
    )
    if name_match:
        fields.customer_name = name_match.group(1).strip().title()

    # Pharmacy / hospital source
    pharmacy_match = re.search(
        r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*)\s+(?:Pharmacy|Hospital|Clinic|Distributors?)",
        text,
        re.I,
    )
    if pharmacy_match:
        fields.complaint_source = pharmacy_match.group(0).title().replace("Pharmacy", "Pharmacy")
        # Normalize casing
        fields.complaint_source = re.sub(r"\bpharmacy\b", "Pharmacy", pharmacy_match.group(0), flags=re.I)
        fields.complaint_source = " ".join(
            w.capitalize() if w.lower() != "pharmacy" else "Pharmacy" for w in fields.complaint_source.split()
        )
        if not fields.customer_name:
            fields.customer_name = fields.complaint_source
    elif "apollo" in lower:
        fields.complaint_source = "Apollo Pharmacy"
        if not fields.customer_name:
            fields.customer_name = "Apollo Pharmacy"

    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if email_match:
        fields.email = email_match.group(0)

    phone_match = re.search(
        r"(?:(?:phone|mobile|no\.?|number)\s*(?:is|=|:)?\s*)?(\+?\d[\d\-\s]{8,}\d)",
        text,
        re.I,
    )
    if phone_match:
        phone = re.sub(r"\s+", "", phone_match.group(1))
        if "@" not in phone and len(re.sub(r"\D", "", phone)) >= 10:
            fields.phone = re.sub(r"\D", "", phone)[-10:] if len(re.sub(r"\D", "", phone)) >= 10 else phone

    # Batch: allow optional "is" before the code; reject stop-words
    batch_match = re.search(
        r"(?:batch|lot)\s*(?:no\.?|number|#)?\s*(?:is|=|:)?\s*([A-Za-z0-9][A-Za-z0-9\-/]{2,})",
        text,
        re.I,
    )
    if batch_match and batch_match.group(1).lower() not in stop:
        fields.batch_number = batch_match.group(1).upper()
    else:
        batch_match = re.search(r"\b([A-Z]{2,}[-/]?\d{2,}[A-Z0-9]*)\b", text)
        if batch_match:
            fields.batch_number = batch_match.group(1)

    expiry_match = re.search(
        r"(?:expir(?:y|ation)|exp\.?)\s*(?:date)?\s*(?:is|=|:)?\s*([A-Za-z]+\s+\d{4}|\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        text,
        re.I,
    )
    if expiry_match:
        fields.expiry_date = expiry_match.group(1).strip()

    mfg_match = re.search(
        r"(?:mfg|manufactur(?:ing|ed)?)\s*(?:date)?\s*(?:is|=|:)?\s*([A-Za-z]+\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        text,
        re.I,
    )
    if mfg_match:
        fields.manufacturing_date = mfg_match.group(1).strip().title()

    # Product name + strength: "product name is dolo strength 500 mg"
    product_match = re.search(
        r"(?:product(?:\s+name)?|medicine|drug)\s*(?:is|=|:)?\s*([A-Za-z][A-Za-z0-9\-]+)",
        text,
        re.I,
    )
    if product_match and product_match.group(1).lower() not in stop | {"name", "from"}:
        fields.product_name = product_match.group(1).strip().title()
    elif "discolored capsules" in lower or "discoloured capsules" in lower:
        fields.product_name = "Hard Gelatin Capsules"

    strength_match = re.search(
        r"(?:strength\s*(?:is|=|:)?\s*)?(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|%|iu)\b)",
        text,
        re.I,
    )
    if strength_match:
        fields.strength = re.sub(r"\s+", " ", strength_match.group(1).strip())

    qty_match = re.search(r"(?:quantity|qauntity|qty|units?)\s*(?:is|=|:)?\s*(\d+)", text, re.I)
    if qty_match:
        fields.quantity = qty_match.group(1)

    if "capsule" in lower:
        fields.dosage_form = "Capsule"
    elif "tablet" in lower:
        fields.dosage_form = "Tablet"
    elif "syrup" in lower:
        fields.dosage_form = "Syrup"

    if re.search(r"\bindia\b", lower):
        fields.country = "India"

    # Professional summary
    bits = []
    if fields.customer_name:
        bits.append(fields.customer_name)
    if fields.complaint_source:
        bits.append(f"via {fields.complaint_source}")
    if fields.product_name:
        prod = fields.product_name
        if fields.strength:
            prod += f" {fields.strength}"
        bits.append(f"reported issue with {prod}")
    if fields.batch_number:
        bits.append(f"batch {fields.batch_number}")
    issue = "capsule discoloration" if "discolor" in lower else "a quality concern"
    fields.summary = (
        f"{' '.join(bits)}. Issue: {issue}. Quantity: {fields.quantity or 'not specified'}."
        if bits
        else text.strip()[:800]
    )

    if not fields.complaint_source and "reported" in lower:
        fields.complaint_source = "Customer Report"

    # Investigation heuristics
    discolor = "discolor" in lower or "discolour" in lower
    contamin = "contamin" in lower

    if discolor or contamin:
        investigation.potential_issue = (
            "Possible moisture ingress causing capsule discoloration."
            if discolor
            else "Possible product contamination."
        )
        investigation.possible_root_cause = (
            "Packaging integrity failure leading to moisture ingress and capsule discoloration; "
            "contamination suspicion requires laboratory confirmation."
            if discolor
            else "Potential contamination during manufacturing, packaging, or distribution."
        )
        investigation.suggested_test = "Moisture Content Analysis" if discolor else "Microbial Limit Test"
        investigation.priority = "high"
        investigation.risk_level = "high"
        investigation.recommended_action = (
            "Review packaging integrity." if discolor else "Quarantine affected batch and initiate investigation."
        )
        investigation.required_tests = (
            ["Moisture Content Analysis", "Appearance / Visual Inspection", "Dissolution Test", "Packaging Integrity (Leak) Test"]
            if discolor
            else ["Microbial Limit Test", "Identification of Contaminant", "Assay"]
        )
        investigation.regulatory_concern = (
            "Potential GMP deviation; may require regulatory notification if confirmed quality defect."
        )
        investigation.impact = "Patient safety risk if product quality compromised; possible batch quarantine/recall."
        investigation.affected_batches = fields.batch_number or "Related batches pending identification"
        investigation.confidence_score = 0.86
        investigation.escalation_level = "QA Manager"
        investigation.risk_category = "Product Quality / Stability"
        investigation.deviation_possibility = "High — initiate deviation if lab confirms defect"
        investigation.missing_information = [
            info
            for info in [
                "Manufacturing date" if not fields.manufacturing_date else None,
                "Exact product strength" if not fields.strength else None,
                "Quantity affected" if not fields.quantity else None,
                "Customer contact email/phone" if not fields.email and not fields.phone else None,
                "Photos of affected product",
            ]
            if info
        ]
        investigation.regulatory_implications = [
            "FDA 21 CFR Part 211 – Drug Product Complaints",
            "WHO GMP – Product Quality Review",
            "Evaluate recall classification if confirmed",
        ]
        investigation.ai_reasoning = (
            "Discoloration of capsules commonly correlates with moisture ingress through packaging defects "
            "or storage under high humidity. Customer contamination suspicion elevates risk pending lab confirmation."
        )
    else:
        investigation.potential_issue = "Quality complaint requiring investigation."
        investigation.possible_root_cause = "To be determined pending investigation."
        investigation.suggested_test = "Visual Inspection & Assay"
        investigation.priority = "medium"
        investigation.risk_level = "medium"
        investigation.recommended_action = "Log complaint and assign investigator."
        investigation.confidence_score = 0.55
        investigation.required_tests = ["Visual Inspection", "Assay"]
        investigation.missing_information = ["Additional product details", "Batch documentation"]
        investigation.regulatory_implications = ["FDA 21 CFR Part 211.198"]
        investigation.escalation_level = "QA Executive"
        investigation.risk_category = "Product Quality"
        investigation.deviation_possibility = "Medium"
        investigation.affected_batches = fields.batch_number or "Unknown"
        investigation.impact = "Under assessment"
        investigation.regulatory_concern = "Standard complaint handling required"
        investigation.ai_reasoning = (
            "General pharmaceutical complaint; insufficient detail for high-confidence root cause."
        )

    msg_parts = ["I've extracted the complaint details and filled the form."]
    if fields.batch_number:
        msg_parts.append(f"Batch **{fields.batch_number}** identified.")
    if fields.customer_name:
        msg_parts.append(f"Customer: **{fields.customer_name}**.")
    if fields.product_name:
        msg_parts.append(f"Product: **{fields.product_name}**" + (f" {fields.strength}" if fields.strength else "") + ".")
    if investigation.potential_issue:
        msg_parts.append(f"Suggested investigation: {investigation.potential_issue}")

    return ExtractResponse(
        fields=fields,
        investigation=investigation,
        message=" ".join(msg_parts),
        duplicates=[],
    )


async def _call_gemini(prompt: str, system: str, *, json_mode: bool = False) -> str:
    """Call Gemini using the configured model, trying fallbacks only if provided."""
    from google import genai
    from google.genai import types

    cfg = get_settings()
    if not cfg.google_api_key:
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    client = genai.Client(api_key=cfg.google_api_key)

    last_error: Exception | None = None
    for model_name in cfg.gemini_model_chain:
        try:
            config_kwargs: dict = {"temperature": 0.1, "system_instruction": system}
            if json_mode:
                config_kwargs["response_mime_type"] = "application/json"
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            text = (response.text or "").strip()
            if text:
                return text
        except Exception as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    return ""


def _resolve_provider() -> str:
    cfg = get_settings()
    if cfg.ai_provider == "mock":
        return "mock"
    if cfg.ai_provider == "gemini":
        return "gemini"
    if cfg.google_api_key:
        return "gemini"
    return "mock"


async def llm_complete(prompt: str, system: str = CHAT_SYSTEM, *, json_mode: bool = False) -> str:
    provider = _resolve_provider()
    try:
        if provider == "gemini":
            return await _call_gemini(prompt, system, json_mode=json_mode)
    except Exception as exc:
        return f"[AI fallback] {exc}\n\n{_mock_chat_fallback(prompt)}"
    return _mock_chat_fallback(prompt)


def _mock_chat_fallback(prompt: str) -> str:
    p = prompt.lower()
    if "capa" in p:
        return (
            "**CAPA Draft**\n\n"
            "**Corrective Actions:** Quarantine batch, perform moisture content & packaging integrity tests, "
            "replace defective packaging materials if confirmed.\n\n"
            "**Preventative Actions:** Enhance incoming packaging inspection, monitor warehouse humidity, "
            "retrain packing line operators, update SOP for leak testing frequency.\n\n"
            "**Owner:** QA Manager | **Due:** 30 days | **Effectiveness check:** 90-day trend review."
        )
    if "fda" in p or "report" in p:
        return (
            "**FDA-Ready Complaint Report Outline**\n\n"
            "1. Complaint identification & receipt date\n"
            "2. Product & batch details\n"
            "3. Nature of defect / adverse experience\n"
            "4. Investigation summary & root cause\n"
            "5. CAPA & distribution of affected units\n"
            "6. Regulatory conclusion & recall assessment\n"
        )
    if "customer reply" in p or "reply" in p:
        return (
            "Dear Valued Customer,\n\n"
            "Thank you for reporting this quality concern. We have logged your complaint and initiated a formal "
            "investigation under our Quality Management System. The affected batch has been flagged for laboratory "
            "evaluation. We will share findings and corrective actions within the agreed timeline.\n\n"
            "Regards,\nAIVOA Quality Assurance"
        )
    if "summar" in p:
        return "Complaint summary: Quality defect reported for the identified batch; investigation and lab testing recommended with elevated priority pending confirmation."
    if "root cause" in p or "5 why" in p or "fishbone" in p:
        return (
            "**Root Cause Hypothesis:** Moisture ingress due to packaging seal failure.\n\n"
            "**5 Whys:** Discoloration → Moisture exposure → Seal leak → Inadequate seal check → SOP gap in packing QC.\n\n"
            "**Fishbone:** Man (training), Machine (sealer), Material (foil), Method (SOP), Environment (humidity), Measurement (leak test)."
        )
    if "investigat" in p:
        return (
            "**Investigation Summary:** Initiate formal investigation for reported capsule discoloration. "
            "Quarantine batch, pull retain samples, execute moisture & integrity tests, interview packing supervisors, "
            "and assess related batches manufactured on the same line."
        )
    return (
        "I can help with complaint extraction, investigation, CAPA, FDA reports, customer replies, "
        "severity classification, and lab test suggestions. Paste a complaint, upload a document, or ask a question."
    )


async def extract_complaint(text: str) -> ExtractResponse:
    provider = _resolve_provider()
    if provider == "mock":
        return _mock_extract(text)

    prompt = (
        "Extract EXACT pharmaceutical complaint fields from the text below.\n"
        "Example of correct mapping for informal text:\n"
        'Text: "hi my name is mehul kumar my email is mehul@gmail.com ... product name is dolo '
        'strength 500 mg batch no. is DXJS54641 ... capsules are discolored"\n'
        "Correct fields: customer_name=Mehul Kumar, email=mehul@gmail.com, product_name=Dolo, "
        "strength=500 mg, batch_number=DXJS54641, dosage_form=Capsule.\n\n"
        f"COMPLAINT TEXT:\n{text}"
    )
    try:
        raw = await llm_complete(prompt, EXTRACTION_SYSTEM, json_mode=True)
        if raw.startswith("[AI fallback]"):
            mock = _mock_extract(text)
            reason = raw.split("\n", 1)[0].replace("[AI fallback] ", "")[:180]
            cfg = get_settings()
            mock.message = (
                f"{mock.message}\n\n"
                f"(Gemini {cfg.gemini_model} unavailable: {reason}. Using the local extractor. "
                "Configure GOOGLE_API_KEY to enable the AI model.)"
            )
            return mock

        data = _parse_json_blob(raw)
        if not data.get("fields"):
            return _mock_extract(text)

        fields = ComplaintFields(**(data.get("fields") or {}))
        inv_raw = data.get("investigation") or {}
        investigation = AIInvestigationSuggestion(**inv_raw)

        # Only fill truly empty fields from heuristic mock — never overwrite Gemini values
        mock = _mock_extract(text)
        for key, value in fields.model_dump().items():
            if (value is None or value == "") and getattr(mock.fields, key):
                setattr(fields, key, getattr(mock.fields, key))

        # Prefer Gemini investigation; fill blanks from mock
        for key, value in investigation.model_dump().items():
            if value in (None, "", [], 0) and getattr(mock.investigation, key) not in (None, "", []):
                setattr(investigation, key, getattr(mock.investigation, key))

        message = data.get("message") or (
            f"I've extracted the complaint details with Gemini and filled the form. "
            f"Product **{fields.product_name or '—'}**, batch **{fields.batch_number or '—'}**."
        )
        return ExtractResponse(
            fields=fields,
            investigation=investigation,
            message=message,
            duplicates=[],
        )
    except Exception:
        return _mock_extract(text)


UPDATE_SYSTEM = """You are AIVOA form-update engine for pharmaceutical complaints.
The user is correcting or adding form fields. Return ONLY valid JSON (no markdown):
{
  "fields": {
    "complaint_source": string|null,
    "customer_name": string|null,
    "email": string|null,
    "phone": string|null,
    "country": string|null,
    "complaint_date": string|null,
    "product_name": string|null,
    "strength": string|null,
    "dosage_form": string|null,
    "batch_number": string|null,
    "manufacturing_date": string|null,
    "expiry_date": string|null,
    "quantity": string|null,
    "summary": string|null
  },
  "message": string
}

Rules:
1. Put the NEW corrected values into fields. Leave unchanged fields as null.
2. If user says batch is wrong and gives a new batch, set batch_number to the new value only.
3. If user corrects quantity, set quantity to the new number only.
4. Never keep the old wrong value. Never invent fields the user did not mention.
5. message should briefly confirm what was updated, e.g. "Updated batch number to DXJS54641 and quantity to 10."
"""


def _is_form_update_message(message: str) -> bool:
    m = message.lower()
    triggers = (
        "correct", "update", "change", "fix", "actually", "instead", "wrong",
        "should be", "replace", "set the", "make it", "not ",
        "batch", "quantity", "qty", "product name", "strength",
        "expiry", "manufactur", "customer name", "email", "phone",
    )
    return any(t in m for t in triggers)


def _heuristic_field_updates(message: str) -> dict[str, str]:
    """Parse common correction phrases without an LLM."""
    updates: dict[str, str] = {}
    stop = {
        "is", "was", "are", "the", "a", "an", "my", "no", "number", "lot", "batch",
        "to", "as", "wrong", "incorrect", "invalid", "old", "new", "correct", "please",
    }

    # Prefer explicit correction phrasing first
    batch = re.search(
        r"(?:correct|update|change|fix|set|new)\s+(?:the\s+)?(?:batch|lot)(?:\s*(?:no\.?|number))?\s*(?:to|as|=|:|is)?\s*([A-Za-z0-9][A-Za-z0-9\-/]{2,})",
        message,
        re.I,
    )
    if not batch:
        batch = re.search(
            r"(?:batch|lot)\s*(?:no\.?|number|#)?\s*(?:is|=|:|to|as)\s*(?:wrong[,.]?\s*)?(?:correct(?:\s+batch)?(?:\s*(?:no\.?|number))?\s*(?:is|=|:|to)?)?\s*([A-Za-z0-9][A-Za-z0-9\-/]{2,})",
            message,
            re.I,
        )
    if not batch:
        # Find all batch-like codes and take the last one (usually the correction)
        codes = re.findall(r"\b([A-Z]{2,}[-/]?\d{2,}[A-Z0-9]*)\b", message)
        if codes:
            updates["batch_number"] = codes[-1].upper()
    elif batch.group(1).lower() not in stop:
        updates["batch_number"] = batch.group(1).upper()

    qty_matches = re.findall(
        r"(?:quantity|qauntity|qty|units?)\s*(?:is|=|:|to|as)?\s*(\d+)",
        message,
        re.I,
    )
    if qty_matches:
        updates["quantity"] = qty_matches[-1]

    product = re.search(
        r"(?:product(?:\s+name)?)\s*(?:is|=|:|to|as)?\s*([A-Za-z][A-Za-z0-9\-]+)",
        message,
        re.I,
    )
    if product and product.group(1).lower() not in stop | {"name"}:
        updates["product_name"] = product.group(1).title()

    strength = re.search(
        r"(?:strength)\s*(?:is|=|:|to|as)?\s*(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|%|iu)?)",
        message,
        re.I,
    )
    if strength:
        updates["strength"] = re.sub(r"\s+", " ", strength.group(1).strip())

    if "email" in message.lower() or "mail" in message.lower() or "@" in message:
        email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", message)
        if email:
            updates["email"] = email.group(0)

    phone = re.search(
        r"(?:phone|mobile|no\.?)\s*(?:is|=|:|to|as)?\s*(\+?\d[\d\-\s]{8,}\d)",
        message,
        re.I,
    )
    if phone:
        digits = re.sub(r"\D", "", phone.group(1))
        if len(digits) >= 10:
            updates["phone"] = digits[-10:]

    cust = re.search(
        r"(?:customer(?:\s+name)?|name)\s*(?:is|=|:|to|as)?\s*([A-Za-z]+(?:\s+[A-Za-z]+){0,3})",
        message,
        re.I,
    )
    if cust and cust.group(1).lower() not in stop | {"is", "me", "my"}:
        updates["customer_name"] = cust.group(1).title()

    expiry = re.search(
        r"(?:expir(?:y|ation)|exp\.?)\s*(?:date)?\s*(?:is|=|:|to|as)?\s*([A-Za-z]+\s+\d{4}|\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        message,
        re.I,
    )
    if expiry:
        updates["expiry_date"] = expiry.group(1).strip()

    mfg = re.search(
        r"(?:mfg|manufactur(?:ing|ed)?)\s*(?:date)?\s*(?:is|=|:|to|as)?\s*([A-Za-z]+\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        message,
        re.I,
    )
    if mfg:
        updates["manufacturing_date"] = mfg.group(1).strip().title()

    return updates


async def update_form_fields(
    message: str,
    form_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Apply user corrections onto existing form fields."""
    heuristic = _heuristic_field_updates(message)
    fields_dict: dict[str, Any] = dict(heuristic)

    provider = _resolve_provider()
    if provider != "mock":
        prompt = (
            "Update the complaint form based on the user's correction.\n"
            f"Current form:\n{json.dumps(form_data or {}, default=str)}\n\n"
            f"User correction:\n{message}\n\n"
            "Return JSON with only the fields that should change to the NEW correct values."
        )
        try:
            raw = await llm_complete(prompt, UPDATE_SYSTEM, json_mode=True)
            if not raw.startswith("[AI fallback]"):
                data = _parse_json_blob(raw)
                for k, v in (data.get("fields") or {}).items():
                    if v is not None and v != "":
                        fields_dict[k] = v
                msg = data.get("message")
            else:
                msg = None
        except Exception:
            msg = None
    else:
        msg = None

    if not fields_dict:
        return {
            "reply": (
                "I couldn't find specific field corrections. "
                "Try: \"batch number is DXJS54641\" or \"quantity is 10\"."
            ),
            "fields": None,
            "investigation": None,
            "action": None,
        }

    # Keep investigation batch in sync when batch changes
    investigation = None
    if fields_dict.get("batch_number"):
        investigation = AIInvestigationSuggestion(
            affected_batches=str(fields_dict["batch_number"])
        )

    changed = ", ".join(f"**{k.replace('_', ' ')}** → {v}" for k, v in fields_dict.items())
    reply = msg or f"Updated the form with your corrections: {changed}."
    return {
        "reply": reply,
        "fields": ComplaintFields(**{k: fields_dict.get(k) for k in ComplaintFields.model_fields}),
        "investigation": investigation,
        "action": "fill_form",
    }


async def chat_with_copilot(
    message: str,
    form_data: Optional[dict[str, Any]] = None,
    history: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    # Full complaint paste → extract everything
    looks_like_complaint = len(message) > 80 and any(
        k in message.lower()
        for k in ("batch", "complaint", "reported", "capsule", "tablet", "expiry", "pharmacy", "hospital")
    )
    if looks_like_complaint and not _is_form_update_message(message):
        extracted = await extract_complaint(message)
        return {
            "reply": extracted.message,
            "fields": extracted.fields,
            "investigation": extracted.investigation,
            "action": "fill_form",
        }

    # Corrections / partial updates (batch, quantity, etc.) — always patch the form
    if _is_form_update_message(message) or _heuristic_field_updates(message):
        # If it's a long paste that also contains corrections keywords, still prefer update
        # when current form already has data
        has_existing = bool(form_data) and any(
            form_data.get(k) for k in ("batch_number", "product_name", "customer_name", "summary", "quantity")
        )
        if has_existing or len(message) < 120 or _heuristic_field_updates(message):
            # Long complaint-like text with existing form: treat as full re-extract if very long
            if looks_like_complaint and len(message) > 120 and not has_existing:
                extracted = await extract_complaint(message)
                return {
                    "reply": extracted.message,
                    "fields": extracted.fields,
                    "investigation": extracted.investigation,
                    "action": "fill_form",
                }
            return await update_form_fields(message, form_data)

    if looks_like_complaint:
        extracted = await extract_complaint(message)
        return {
            "reply": extracted.message,
            "fields": extracted.fields,
            "investigation": extracted.investigation,
            "action": "fill_form",
        }

    context = ""
    if form_data:
        context += f"\nCurrent form data:\n{json.dumps(form_data, default=str)}\n"
    if history:
        recent = history[-6:]
        context += "\nRecent conversation:\n" + "\n".join(f"{h['role']}: {h['content']}" for h in recent)

    prompt = (
        f"{context}\n\nUser: {message}\n\n"
        "If the user provides any corrected field values, you MUST include them as:\n"
        "<<<FORM>>>{\"fields\":{...only changed fields...}}<<<END>>>"
    )
    reply = await llm_complete(prompt)

    fields = None
    investigation = None
    form_block = re.search(r"<<<FORM>>>([\s\S]*?)<<<END>>>", reply)
    if form_block:
        data = _parse_json_blob(form_block.group(1))
        if data.get("fields"):
            fields = ComplaintFields(**data["fields"])
        if data.get("investigation"):
            investigation = AIInvestigationSuggestion(**data["investigation"])
        reply = re.sub(r"<<<FORM>>>[\s\S]*?<<<END>>>", "", reply).strip()
    else:
        # Last chance: heuristic parse even for general chat replies
        heur = _heuristic_field_updates(message)
        if heur:
            fields = ComplaintFields(**{k: heur.get(k) for k in ComplaintFields.model_fields})
            reply = (reply + f"\n\nAlso updated: {', '.join(heur.keys())}.").strip()

    return {
        "reply": reply,
        "fields": fields,
        "investigation": investigation,
        "action": "fill_form" if fields else None,
    }


async def generate_investigation(form_data: dict[str, Any]) -> dict[str, Any]:
    provider = _resolve_provider()
    prompt = (
        "Generate a full pharmaceutical complaint investigation as JSON with keys: "
        "summary, root_cause_analysis, fishbone_analysis (dict with man,machine,material,method,environment,measurement), "
        "five_why_analysis (list of {why, answer}), risk_assessment, recommended_capa, preventive_actions, timeline, owner.\n\n"
        f"Complaint data:\n{json.dumps(form_data, default=str)}"
    )
    if provider != "mock":
        try:
            raw = await llm_complete(prompt, EXTRACTION_SYSTEM)
            data = _parse_json_blob(raw)
            if data.get("summary"):
                return data
        except Exception:
            pass

    product = form_data.get("product_name") or "product"
    batch = form_data.get("batch_number") or "unknown"
    return {
        "summary": (
            f"Formal investigation initiated for {product} batch {batch}. "
            f"Issue: {form_data.get('summary') or form_data.get('potential_issue') or 'quality complaint'}."
        ),
        "root_cause_analysis": form_data.get("possible_root_cause")
        or "Suspected packaging integrity failure leading to environmental exposure.",
        "fishbone_analysis": {
            "man": ["Operator training on seal inspection", "Shift handover gaps"],
            "machine": ["Heat sealer calibration drift", "Leak tester downtime"],
            "material": ["Foil laminate moisture barrier variation", "Capsule shell hygroscopicity"],
            "method": ["SOP frequency for integrity checks insufficient"],
            "environment": ["Warehouse RH excursions", "Cold-chain break during transit"],
            "measurement": ["No routine moisture trending on retains"],
        },
        "five_why_analysis": [
            {"why": "Why were capsules discolored?", "answer": "Moisture exposure"},
            {"why": "Why moisture exposure?", "answer": "Packaging seal leak"},
            {"why": "Why seal leak?", "answer": "Inconsistent sealing parameters"},
            {"why": "Why inconsistent sealing?", "answer": "Sealer not calibrated per schedule"},
            {"why": "Why missed calibration?", "answer": "Preventive maintenance SOP gap"},
        ],
        "risk_assessment": (
            f"Risk level: {form_data.get('risk_level') or 'high'}. "
            "Patient impact possible if stability compromised. Batch quarantine recommended until lab clearance."
        ),
        "recommended_capa": form_data.get("recommended_action")
        or "Quarantine batch, complete lab tests, revise sealing SOP, calibrate equipment.",
        "preventive_actions": (
            "Increase seal integrity sampling, install continuous RH monitoring, "
            "add packaging material CoA moisture checks, CAPA effectiveness review at 90 days."
        ),
        "timeline": "Day 0–1 Quarantine & sample | Day 2–7 Lab testing | Day 8–14 RCA | Day 15–30 CAPA implementation",
        "owner": "QA Manager",
    }


async def generate_capa(form_data: dict[str, Any]) -> dict[str, Any]:
    inv = await generate_investigation(form_data)
    return {
        "title": f"CAPA – {form_data.get('product_name') or 'Complaint'} / {form_data.get('batch_number') or 'Batch'}",
        "corrective_actions": inv.get("recommended_capa"),
        "preventive_actions": inv.get("preventive_actions"),
        "owner": inv.get("owner") or "QA Manager",
        "status": "open",
        "effectiveness_check": "Review recurrence rate of similar complaints over 90 days; verify sealing PM compliance.",
    }


async def generate_customer_reply(form_data: dict[str, Any]) -> str:
    name = form_data.get("customer_name") or "Valued Customer"
    batch = form_data.get("batch_number") or "the reported batch"
    return (
        f"Dear {name},\n\n"
        f"Thank you for bringing this matter to our attention. We have registered your complaint regarding "
        f"{form_data.get('product_name') or 'our product'} (Batch {batch}) and initiated a formal quality investigation.\n\n"
        "Our Quality Assurance team is evaluating retain samples and manufacturing records. "
        "We will share the investigation outcome and any corrective actions promptly.\n\n"
        "We appreciate your partnership in maintaining product quality.\n\n"
        "Sincerely,\nQuality Assurance – AIVOA"
    )
