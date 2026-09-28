from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SAEnum, Float, ForeignKey,
    Integer, String, Text, JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserRole(str, Enum):
    ADMIN = "admin"
    QA_MANAGER = "qa_manager"
    QA_EXECUTIVE = "qa_executive"
    INVESTIGATOR = "investigator"
    AUDITOR = "auditor"
    VIEWER = "viewer"


class ComplaintStatus(str, Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    INVESTIGATION = "investigation"
    CAPA = "capa"
    CLOSED = "closed"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.QA_EXECUTIVE)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    complaints = relationship("Complaint", back_populates="assignee", foreign_keys="Complaint.assignee_id")
    audit_logs = relationship("AuditLog", back_populates="user")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255))
    phone = Column(String(50))
    country = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    complaints = relationship("Complaint", back_populates="customer")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    strength = Column(String(100))
    dosage_form = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    complaints = relationship("Complaint", back_populates="product")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(String(50), unique=True, index=True, nullable=False)
    complaint_source = Column(String(255))
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    customer_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    country = Column(String(100))
    complaint_date = Column(DateTime(timezone=True))

    product_name = Column(String(255))
    strength = Column(String(100))
    dosage_form = Column(String(100))
    batch_number = Column(String(100), index=True)
    manufacturing_date = Column(String(50))
    expiry_date = Column(String(50))
    quantity = Column(String(50))

    summary = Column(Text)
    raw_text = Column(Text)
    status = Column(SAEnum(ComplaintStatus), default=ComplaintStatus.PENDING, index=True)
    priority = Column(SAEnum(Priority), default=Priority.MEDIUM)
    risk_level = Column(SAEnum(RiskLevel), default=RiskLevel.MEDIUM)
    severity_score = Column(Float, default=0.0)

    # AI suggested investigation fields
    possible_root_cause = Column(Text)
    affected_batches = Column(Text)
    regulatory_concern = Column(Text)
    impact = Column(Text)
    confidence_score = Column(Float, default=0.0)
    potential_issue = Column(Text)
    suggested_test = Column(Text)
    recommended_action = Column(Text)
    ai_reasoning = Column(Text)
    ai_suggestions = Column(JSON)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    customer = relationship("Customer", back_populates="complaints")
    product = relationship("Product", back_populates="complaints")
    assignee = relationship("User", back_populates="complaints", foreign_keys=[assignee_id])
    investigations = relationship("Investigation", back_populates="complaint", cascade="all, delete-orphan")
    capas = relationship("CAPA", back_populates="complaint", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="complaint", cascade="all, delete-orphan")
    chat_history = relationship("ChatHistory", back_populates="complaint", cascade="all, delete-orphan")


class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=True)
    summary = Column(Text)
    root_cause_analysis = Column(Text)
    fishbone_analysis = Column(JSON)
    five_why_analysis = Column(JSON)
    risk_assessment = Column(Text)
    recommended_capa = Column(Text)
    preventive_actions = Column(Text)
    timeline = Column(Text)
    owner = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    complaint = relationship("Complaint", back_populates="investigations")


class CAPA(Base):
    __tablename__ = "capa"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=True)
    title = Column(String(255))
    corrective_actions = Column(Text)
    preventive_actions = Column(Text)
    owner = Column(String(255))
    due_date = Column(DateTime(timezone=True))
    status = Column(String(50), default="open")
    effectiveness_check = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    complaint = relationship("Complaint", back_populates="capas")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    content_type = Column(String(100))
    size_bytes = Column(Integer, default=0)
    extracted_text = Column(Text)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    complaint = relationship("Complaint", back_populates="attachments")


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=True)
    session_id = Column(String(100), index=True)
    role = Column(String(20), nullable=False)  # user | assistant | system
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    complaint = relationship("Complaint", back_populates="chat_history")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    doc_type = Column(String(100))  # SOP, FDA, WHO_GMP, MANUAL, CAPA_TEMPLATE
    filename = Column(String(255))
    file_path = Column(String(500))
    content = Column(Text)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(String(100))
    details = Column(JSON)
    ip_address = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="audit_logs")
