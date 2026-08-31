from datetime import datetime, timezone
from sqlalchemy import String, Integer, BigInteger, Boolean, Float, DateTime, Text, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="operator")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    identifier: Mapped[str] = mapped_column(String, primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Run(Base):
    __tablename__ = "runs"
    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    currency: Mapped[str] = mapped_column(String, default="INR")
    status: Mapped[str] = mapped_column(String, default="CREATED")
    rules_version: Mapped[str] = mapped_column(String, default="v1.0")
    assumptions_version: Mapped[str] = mapped_column(String, default="v1.0")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    source_checksums: Mapped[dict] = mapped_column(JSON, default=dict)
    summary_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_fixture: Mapped[bool] = mapped_column(Boolean, default=False)


class Source(Base):
    __tablename__ = "sources"
    source_id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    source_type: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String)
    checksum: Mapped[str] = mapped_column(String)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="LOADED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("run_id", "source_type", name="uq_run_source_type"),)


class InvalidRecord(Base):
    __tablename__ = "invalid_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    source_type: Mapped[str] = mapped_column(String)
    row_number: Mapped[int] = mapped_column(Integer)
    raw: Mapped[dict] = mapped_column(JSON)
    errors: Mapped[list] = mapped_column(JSON)


class OrderRecord(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    source_record_id: Mapped[str] = mapped_column(String)
    internal_order_id: Mapped[str] = mapped_column(String)
    razorpay_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String, nullable=True)
    order_date: Mapped[str] = mapped_column(String)
    gross_amount_minor: Mapped[int] = mapped_column(BigInteger)
    refund_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    expected_net_amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String, default="INR")
    status: Mapped[str] = mapped_column(String, default="paid")
    customer_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    raw: Mapped[dict] = mapped_column(JSON)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of: Mapped[str | None] = mapped_column(String, nullable=True)
    __table_args__ = (UniqueConstraint("run_id", "source_record_id", name="uq_order_rec"),)


class SettlementRecord(Base):
    __tablename__ = "settlements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    source_record_id: Mapped[str] = mapped_column(String)
    settlement_id: Mapped[str] = mapped_column(String)
    payment_id: Mapped[str | None] = mapped_column(String, nullable=True)
    order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    utr: Mapped[str | None] = mapped_column(String, nullable=True)
    settlement_date: Mapped[str] = mapped_column(String)
    gross_amount_minor: Mapped[int] = mapped_column(BigInteger)
    fee_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tax_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    net_amount_minor: Mapped[int] = mapped_column(BigInteger)
    method: Mapped[str | None] = mapped_column(String, nullable=True)
    adjustment_type: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String, default="INR")
    raw: Mapped[dict] = mapped_column(JSON)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of: Mapped[str | None] = mapped_column(String, nullable=True)
    __table_args__ = (UniqueConstraint("run_id", "source_record_id", name="uq_settlement_rec"),)


class BankRecord(Base):
    __tablename__ = "bank_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    source_record_id: Mapped[str] = mapped_column(String)
    bank_entry_id: Mapped[str] = mapped_column(String)
    value_date: Mapped[str] = mapped_column(String)
    utr: Mapped[str | None] = mapped_column(String, nullable=True)
    narration: Mapped[str] = mapped_column(String)
    credit_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    debit_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    account_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String, default="INR")
    raw: Mapped[dict] = mapped_column(JSON)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of: Mapped[str | None] = mapped_column(String, nullable=True)
    __table_args__ = (UniqueConstraint("run_id", "source_record_id", name="uq_bank_rec"),)


class PaymentRecord(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    source_record_id: Mapped[str] = mapped_column(String)
    payment_id: Mapped[str] = mapped_column(String)
    order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_amount_minor: Mapped[int] = mapped_column(BigInteger)
    refund_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    payment_status: Mapped[str] = mapped_column(String)
    payment_date: Mapped[str] = mapped_column(String)
    currency: Mapped[str] = mapped_column(String, default="INR")
    raw: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("run_id", "source_record_id", name="uq_payment_rec"),)


class MatchDecision(Base):
    __tablename__ = "matches"
    match_id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    plane: Mapped[str] = mapped_column(String)
    match_type: Mapped[str] = mapped_column(String)
    source_a_ids: Mapped[list] = mapped_column(JSON)
    source_b_ids: Mapped[list] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float)
    evidence: Mapped[dict] = mapped_column(JSON)
    decision: Mapped[str] = mapped_column(String)
    rules_version: Mapped[str] = mapped_column(String, default="v1.0")
    reviewer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExceptionRecord(Base):
    __tablename__ = "exceptions"
    exception_id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, index=True)
    exception_code: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String)
    record_ids: Mapped[list] = mapped_column(JSON)
    amount_at_risk_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String, default="OPEN")
    recommended_action: Mapped[str] = mapped_column(String)
    explanation: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    ai_explanation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    match_id: Mapped[str | None] = mapped_column(String, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_action: Mapped[str | None] = mapped_column(String, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_event_id: Mapped[str] = mapped_column(String, unique=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    run_id: Mapped[str] = mapped_column(String, index=True)
    actor: Mapped[str] = mapped_column(String)
    step: Mapped[str] = mapped_column(String)
    source_record_ids: Mapped[list] = mapped_column(JSON, default=list)
    exception_id: Mapped[str | None] = mapped_column(String, nullable=True)
    match_id: Mapped[str | None] = mapped_column(String, nullable=True)
    rules_version: Mapped[str] = mapped_column(String, default="v1.0")
    assumptions_version: Mapped[str] = mapped_column(String, default="v1.0")
    model_version: Mapped[str] = mapped_column(String, default="none")
    decision: Mapped[str] = mapped_column(String, default="")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    human_gate: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    outcome: Mapped[str] = mapped_column(Text, default="")
    previous_event_hash: Mapped[str] = mapped_column(String, default="")
    event_hash: Mapped[str] = mapped_column(String, default="")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String, unique=True)
    event_type: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
