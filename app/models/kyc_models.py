"""
YottaFlex KYC – SQLAlchemy ORM Models
All 10 core entities + bridge tables + history structures.

ID conventions:
  Customer       : CUS-000001
  KYCRequirement : KYC-2026-000001
  Document       : DOC-<customer_id>-001
  ReviewCase     : REV-<customer_id>-2026
  Alert          : ALT-2026-000001
  BeneficialOwner: BO-<customer_id>-001
  Verification   : VER-<doc_id>-001
  AuditEvent     : AUD-2026-000001
  RiskRating     : RR-<customer_id>-001
"""
import enum
from datetime import date, datetime
from sqlalchemy import (
    Column, String, Integer, Numeric, Boolean, Date, DateTime,
    Text, Enum as SAEnum, ForeignKey, UniqueConstraint, CheckConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from app.db.session import Base


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CustomerTypeCode(str, enum.Enum):
    INDIVIDUAL = "INDIVIDUAL"
    SOLE_TRADER = "SOLE_TRADER"
    PARTNERSHIP = "PARTNERSHIP"
    PRIVATE_COMPANY = "PRIVATE_COMPANY"
    PUBLIC_COMPANY = "PUBLIC_COMPANY"
    TRUST = "TRUST"
    NON_PROFIT = "NON_PROFIT"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class OnboardingStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"


class DocumentCategory(str, enum.Enum):
    IDENTITY = "IDENTITY"
    ADDRESS = "ADDRESS"
    BUSINESS = "BUSINESS"
    FINANCIAL = "FINANCIAL"
    OWNERSHIP = "OWNERSHIP"
    COMPLIANCE = "COMPLIANCE"
    OTHER = "OTHER"


class DocumentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"


class VerificationDecision(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REFER = "REFER"
    PENDING = "PENDING"


class ReviewCaseStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED_RESOLVED = "CLOSED_RESOLVED"
    CLOSED_NO_ACTION = "CLOSED_NO_ACTION"
    CLOSED_WITHOUT_RESOLUTION = "CLOSED_WITHOUT_RESOLUTION"
    OVERDUE = "OVERDUE"


class ReviewTrigger(str, enum.Enum):
    PERIODIC = "PERIODIC"
    RISK_CHANGE = "RISK_CHANGE"
    DOCUMENT_EXPIRY = "DOCUMENT_EXPIRY"
    ALERT = "ALERT"
    MANUAL = "MANUAL"


class AlertType(str, enum.Enum):
    DOCUMENT_EXPIRING = "DOCUMENT_EXPIRING"
    DOCUMENT_EXPIRED = "DOCUMENT_EXPIRED"
    REVIEW_OVERDUE = "REVIEW_OVERDUE"
    KYC_INCOMPLETE = "KYC_INCOMPLETE"
    OWNERSHIP_MISMATCH = "OWNERSHIP_MISMATCH"
    NAME_MISMATCH = "NAME_MISMATCH"
    DUPLICATE_DOCUMENT = "DUPLICATE_DOCUMENT"
    ANOMALY_DETECTED = "ANOMALY_DETECTED"


class AlertSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    VERIFY = "VERIFY"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REVIEW_OPEN = "REVIEW_OPEN"
    REVIEW_CLOSE = "REVIEW_CLOSE"
    ALERT_RAISED = "ALERT_RAISED"
    ALERT_RESOLVED = "ALERT_RESOLVED"
    ANOMALY_INJECTED = "ANOMALY_INJECTED"
    STATUS_CHANGE = "STATUS_CHANGE"


class RequirementType(str, enum.Enum):
    MANDATORY = "MANDATORY"
    CONDITIONAL = "CONDITIONAL"
    OPTIONAL = "OPTIONAL"


# ---------------------------------------------------------------------------
# 1. CustomerType
# ---------------------------------------------------------------------------

class CustomerType(Base):
    __tablename__ = "customer_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(SAEnum(CustomerTypeCode), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    requires_beneficial_owner = Column(Boolean, default=False, nullable=False)
    min_beneficial_owner_pct = Column(Numeric(5, 2), default=25.00)
    periodic_review_months = Column(Integer, nullable=False, default=12)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    customers = relationship("Customer", back_populates="customer_type")
    kyc_requirements = relationship("KYCRequirement", back_populates="customer_type")

    def __repr__(self):
        return f"<CustomerType {self.code}>"


# ---------------------------------------------------------------------------
# 2. Customer
# ---------------------------------------------------------------------------

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(20), unique=True, nullable=False)   # CUS-000001
    full_name = Column(String(200), nullable=False)
    date_of_birth = Column(Date)
    nationality = Column(String(100))
    country_of_residence = Column(String(100), nullable=False)
    email = Column(String(200))
    phone = Column(String(50))
    address_line1 = Column(String(200))
    address_line2 = Column(String(200))
    city = Column(String(100))
    state_province = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100))

    customer_type_id = Column(Integer, ForeignKey("customer_types.id"), nullable=False)
    onboarding_status = Column(SAEnum(OnboardingStatus), default=OnboardingStatus.PENDING, nullable=False)

    # Business fields (for non-individual customers)
    business_registration_number = Column(String(100))
    business_name = Column(String(200))
    incorporation_date = Column(Date)
    incorporation_country = Column(String(100))

    # KYC tracking
    kyc_completeness_pct = Column(Numeric(5, 2), default=0.00)
    is_pep = Column(Boolean, default=False)                # Politically Exposed Person
    is_sanctioned = Column(Boolean, default=False)
    source_of_funds = Column(String(200))

    onboarding_date = Column(Date)
    approved_date = Column(Date)
    next_review_date = Column(Date)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer_type = relationship("CustomerType", back_populates="customers")
    documents = relationship("Document", back_populates="customer")
    risk_ratings = relationship("RiskRating", back_populates="customer", order_by="RiskRating.effective_from")
    review_cases = relationship("ReviewCase", back_populates="customer")
    alerts = relationship("Alert", back_populates="customer")
    audit_events = relationship("AuditEvent", back_populates="customer")
    beneficial_owners = relationship("BeneficialOwner",
                                     foreign_keys="BeneficialOwner.business_customer_id",
                                     back_populates="business_customer")

    __table_args__ = (
        Index("ix_customers_customer_id", "customer_id"),
        Index("ix_customers_onboarding_status", "onboarding_status"),
        Index("ix_customers_next_review_date", "next_review_date"),
    )

    def __repr__(self):
        return f"<Customer {self.customer_id} {self.full_name}>"


# ---------------------------------------------------------------------------
# 3. KYCRequirement
# ---------------------------------------------------------------------------

class KYCRequirement(Base):
    __tablename__ = "kyc_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_id = Column(String(25), unique=True, nullable=False)   # KYC-2026-000001
    customer_type_id = Column(Integer, ForeignKey("customer_types.id"), nullable=False)
    document_category = Column(SAEnum(DocumentCategory), nullable=False)
    document_type = Column(String(100), nullable=False)
    requirement_type = Column(SAEnum(RequirementType), nullable=False, default=RequirementType.MANDATORY)
    risk_level_applicable = Column(SAEnum(RiskLevel))   # NULL = all risk levels
    description = Column(Text)
    max_age_months = Column(Integer)                    # Maximum document age in months
    is_active = Column(Boolean, default=True, nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    customer_type = relationship("CustomerType", back_populates="kyc_requirements")

    __table_args__ = (
        Index("ix_kyc_req_customer_type", "customer_type_id"),
        Index("ix_kyc_req_category", "document_category"),
    )

    def __repr__(self):
        return f"<KYCRequirement {self.requirement_id}>"


# ---------------------------------------------------------------------------
# 4. Document
# ---------------------------------------------------------------------------

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(30), unique=True, nullable=False)   # DOC-CUS-000001-001
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    document_category = Column(SAEnum(DocumentCategory), nullable=False)
    document_type = Column(String(100), nullable=False)
    document_number = Column(String(100))
    issuing_authority = Column(String(200))
    issuing_country = Column(String(100))
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date)
    document_status = Column(SAEnum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    file_reference = Column(String(500))                # Path/reference to stored file
    notes = Column(Text)
    is_mandatory = Column(Boolean, default=True)

    # For anomaly: flag if used as duplicate across customers
    is_duplicate_suspect = Column(Boolean, default=False)
    duplicate_of_document_id = Column(String(30))      # references document_id string

    # Timestamps
    submitted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="documents")
    verifications = relationship("Verification", back_populates="document",
                                 order_by="Verification.verified_at")

    __table_args__ = (
        Index("ix_documents_customer_id", "customer_id"),
        Index("ix_documents_document_status", "document_status"),
        Index("ix_documents_expiry_date", "expiry_date"),
        Index("ix_documents_document_number", "document_number"),
    )

    def __repr__(self):
        return f"<Document {self.document_id}>"


# ---------------------------------------------------------------------------
# 5. Verification
# ---------------------------------------------------------------------------

class Verification(Base):
    __tablename__ = "verifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    verification_id = Column(String(35), unique=True, nullable=False)  # VER-DOC-CUS-000001-001-001
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    verified_by = Column(String(100), nullable=False)   # officer name or system
    verified_at = Column(DateTime, nullable=False)
    decision = Column(SAEnum(VerificationDecision), nullable=False)
    decision_reason = Column(Text)
    name_match = Column(Boolean)                        # True if name on doc matches customer name
    name_on_document = Column(String(200))
    expiry_check_passed = Column(Boolean)
    authenticity_check_passed = Column(Boolean)
    override_flag = Column(Boolean, default=False)      # True if decision was manually overridden
    override_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="verifications")

    __table_args__ = (
        Index("ix_verifications_document_id", "document_id"),
        Index("ix_verifications_decision", "decision"),
        Index("ix_verifications_verified_at", "verified_at"),
    )

    def __repr__(self):
        return f"<Verification {self.verification_id} {self.decision}>"


# ---------------------------------------------------------------------------
# 6. RiskRating
# ---------------------------------------------------------------------------

class RiskRating(Base):
    __tablename__ = "risk_ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    risk_rating_id = Column(String(25), unique=True, nullable=False)   # RR-CUS-000001-001
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    risk_level = Column(SAEnum(RiskLevel), nullable=False)
    risk_score = Column(Numeric(5, 2))                  # 0–100
    assessed_by = Column(String(100))
    assessed_at = Column(DateTime, nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)                         # NULL = current
    rationale = Column(Text)
    pep_flag = Column(Boolean, default=False)
    sanctions_flag = Column(Boolean, default=False)
    geographic_risk = Column(String(50))
    industry_risk = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="risk_ratings")

    __table_args__ = (
        Index("ix_risk_ratings_customer_id", "customer_id"),
        Index("ix_risk_ratings_effective_from", "effective_from"),
    )

    def __repr__(self):
        return f"<RiskRating {self.risk_rating_id} {self.risk_level}>"


# ---------------------------------------------------------------------------
# 7. ReviewCase
# ---------------------------------------------------------------------------

class ReviewCase(Base):
    __tablename__ = "review_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(String(25), unique=True, nullable=False)        # REV-CUS-000001-2026
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    trigger = Column(SAEnum(ReviewTrigger), nullable=False)
    status = Column(SAEnum(ReviewCaseStatus), default=ReviewCaseStatus.OPEN, nullable=False)
    opened_at = Column(DateTime, nullable=False)
    due_date = Column(Date, nullable=False)
    closed_at = Column(DateTime)
    assigned_to = Column(String(100))
    findings = Column(Text)
    resolution = Column(Text)
    # Anomaly: closed_without_resolution flag
    closed_without_resolution = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="review_cases")
    alerts = relationship("Alert", back_populates="review_case")

    __table_args__ = (
        Index("ix_review_cases_customer_id", "customer_id"),
        Index("ix_review_cases_status", "status"),
        Index("ix_review_cases_due_date", "due_date"),
    )

    def __repr__(self):
        return f"<ReviewCase {self.review_id} {self.status}>"


# ---------------------------------------------------------------------------
# 8. BeneficialOwner
# ---------------------------------------------------------------------------

class BeneficialOwner(Base):
    __tablename__ = "beneficial_owners"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bo_id = Column(String(25), unique=True, nullable=False)            # BO-CUS-000001-001
    business_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    # The BO may also be a registered customer (optional link)
    individual_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)

    full_name = Column(String(200), nullable=False)
    date_of_birth = Column(Date)
    nationality = Column(String(100))
    country_of_residence = Column(String(100))
    ownership_percentage = Column(Numeric(5, 2), nullable=False)
    control_type = Column(String(100))                  # direct, indirect, etc.
    is_pep = Column(Boolean, default=False)
    is_sanctioned = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    verification_date = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    business_customer = relationship("Customer",
                                     foreign_keys=[business_customer_id],
                                     back_populates="beneficial_owners")
    individual_customer = relationship("Customer",
                                       foreign_keys=[individual_customer_id])

    __table_args__ = (
        Index("ix_bo_business_customer_id", "business_customer_id"),
        CheckConstraint(
            "ownership_percentage >= 0 AND ownership_percentage <= 100",
            name="ck_bo_ownership_pct_range"
        ),
    )

    def __repr__(self):
        return f"<BeneficialOwner {self.bo_id} {self.full_name} {self.ownership_percentage}%>"


# ---------------------------------------------------------------------------
# 9. Alert
# ---------------------------------------------------------------------------

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(20), unique=True, nullable=False)         # ALT-2026-000001
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    review_case_id = Column(Integer, ForeignKey("review_cases.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)

    alert_type = Column(SAEnum(AlertType), nullable=False)
    severity = Column(SAEnum(AlertSeverity), nullable=False)
    status = Column(SAEnum(AlertStatus), default=AlertStatus.OPEN, nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    triggered_at = Column(DateTime, nullable=False)
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    resolved_by = Column(String(100))
    resolution_notes = Column(Text)
    # For anomaly tracking
    is_anomaly = Column(Boolean, default=False)
    anomaly_label = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="alerts")
    review_case = relationship("ReviewCase", back_populates="alerts")
    document = relationship("Document")

    __table_args__ = (
        Index("ix_alerts_customer_id", "customer_id"),
        Index("ix_alerts_alert_type", "alert_type"),
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_triggered_at", "triggered_at"),
    )

    def __repr__(self):
        return f"<Alert {self.alert_id} {self.alert_type} {self.status}>"


# ---------------------------------------------------------------------------
# 10. AuditEvent
# ---------------------------------------------------------------------------

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_id = Column(String(20), unique=True, nullable=False)         # AUD-2026-000001
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    entity_type = Column(String(50), nullable=False)                   # Customer, Document, etc.
    entity_id = Column(String(50), nullable=False)                     # The ID of the affected record
    action = Column(SAEnum(AuditAction), nullable=False)
    performed_by = Column(String(100), nullable=False)
    performed_at = Column(DateTime, nullable=False)
    old_value = Column(Text)                                           # JSON snapshot of previous state
    new_value = Column(Text)                                           # JSON snapshot of new state
    ip_address = Column(String(45))
    session_id = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="audit_events")

    __table_args__ = (
        Index("ix_audit_events_customer_id", "customer_id"),
        Index("ix_audit_events_entity_type", "entity_type"),
        Index("ix_audit_events_performed_at", "performed_at"),
        Index("ix_audit_events_action", "action"),
    )

    def __repr__(self):
        return f"<AuditEvent {self.audit_id} {self.action} on {self.entity_type}:{self.entity_id}>"


# ---------------------------------------------------------------------------
# Bridge: CustomerDocumentRequirement (tracks fulfilment per customer)
# ---------------------------------------------------------------------------

class CustomerDocumentRequirement(Base):
    """Tracks which KYC requirements each customer has fulfilled."""
    __tablename__ = "customer_document_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    requirement_id = Column(Integer, ForeignKey("kyc_requirements.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)   # NULL if not yet fulfilled
    is_fulfilled = Column(Boolean, default=False, nullable=False)
    fulfilled_at = Column(DateTime)
    waived = Column(Boolean, default=False)
    waiver_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("customer_id", "requirement_id", name="uq_customer_requirement"),
        Index("ix_cdr_customer_id", "customer_id"),
    )
