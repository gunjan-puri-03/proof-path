"""
YottaFlex KYC – Synthetic Data Generator
=========================================
Fixed seed: 20261022

Generates:
  - Customer types (master data)
  - 8,000 customers (full mode) / 100 customers (starter mode)
  - 20,000 documents (full) / 300 (starter)
  - 1,000 business entities linked to customers
  - 3,000 review cases (full) / 50 (starter)
  - KYC requirements
  - Risk ratings
  - Beneficial owners
  - Verifications
  - Alerts
  - Audit events

ID conventions:
  Customer       : CUS-000001
  KYCRequirement : KYC-2026-000001
  Document       : DOC-<short_cust_id>-<seq>  e.g. DOC-CUS-000001-001
  ReviewCase     : REV-<short_cust_id>-2026
  Alert          : ALT-2026-000001
  BeneficialOwner: BO-<short_cust_id>-001
  Verification   : VER-<short_doc_id>-001
  AuditEvent     : AUD-2026-000001
  RiskRating     : RR-<short_cust_id>-001
"""
import random
import hashlib
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from faker import Faker
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.models.kyc_models import (
    Base, CustomerType, Customer, KYCRequirement, Document, Verification,
    RiskRating, ReviewCase, BeneficialOwner, Alert, AuditEvent,
    CustomerDocumentRequirement,
    CustomerTypeCode, RiskLevel, OnboardingStatus, DocumentCategory,
    DocumentStatus, VerificationDecision, ReviewCaseStatus, ReviewTrigger,
    AlertType, AlertSeverity, AlertStatus, AuditAction, RequirementType,
)

SEED = 20261022
fake = Faker()
Faker.seed(SEED)
random.seed(SEED)

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

DOCUMENT_TYPES_BY_CATEGORY = {
    DocumentCategory.IDENTITY: [
        "Passport", "National ID Card", "Driver's Licence",
        "Birth Certificate", "Residence Permit",
    ],
    DocumentCategory.ADDRESS: [
        "Utility Bill", "Bank Statement", "Council Tax Letter",
        "Tenancy Agreement", "Government Letter",
    ],
    DocumentCategory.BUSINESS: [
        "Certificate of Incorporation", "Business Licence",
        "Partnership Deed", "Articles of Association", "Memorandum of Association",
        "Company Search Report", "Annual Return",
    ],
    DocumentCategory.FINANCIAL: [
        "Audited Financial Statements", "Bank Reference Letter",
        "Tax Return", "Source of Funds Declaration",
    ],
    DocumentCategory.OWNERSHIP: [
        "Share Register", "Register of Members",
        "Shareholder Agreement", "Beneficial Ownership Declaration",
    ],
    DocumentCategory.COMPLIANCE: [
        "AML Policy", "Sanctions Screening Report",
        "PEP Declaration", "Risk Assessment Report",
    ],
}

COUNTRIES = [
    "United Kingdom", "United States", "India", "Canada", "Australia",
    "Germany", "France", "Singapore", "United Arab Emirates", "South Africa",
    "Nigeria", "Kenya", "Ghana", "Brazil", "China", "Japan",
    "Hong Kong", "Switzerland", "Netherlands", "Sweden",
]

HIGH_RISK_COUNTRIES = ["Nigeria", "Kenya", "Ghana", "China", "Hong Kong"]

ISSUERS = {
    DocumentCategory.IDENTITY: [
        "Home Office", "DVLA", "Passport Agency", "National Identity Authority",
    ],
    DocumentCategory.ADDRESS: [
        "Local Council", "Utility Company", "Bank", "HMRC",
    ],
    DocumentCategory.BUSINESS: [
        "Companies House", "Business Registry", "Chamber of Commerce",
    ],
    DocumentCategory.FINANCIAL: [
        "External Auditor", "Chartered Accountant", "HMRC",
    ],
    DocumentCategory.OWNERSHIP: [
        "Company Secretary", "Legal Counsel", "Companies House",
    ],
    DocumentCategory.COMPLIANCE: [
        "Compliance Team", "Risk Department", "External Consultant",
    ],
}

OFFICERS = [
    "Alice Johnson", "Bob Smith", "Carol Williams", "David Brown",
    "Emma Davis", "Frank Wilson", "Grace Moore", "Henry Taylor",
    "Isabella Anderson", "James Thomas", "Karen Jackson", "Liam White",
    "Mia Harris", "Noah Martin", "Olivia Thompson", "Peter Garcia",
    "Quinn Martinez", "Rachel Robinson", "Samuel Clark", "Tara Lewis",
    "System", "Automated KYC", "Batch Process",
]


# ---------------------------------------------------------------------------
# ID generators
# ---------------------------------------------------------------------------

def make_customer_id(seq: int) -> str:
    return f"CUS-{seq:06d}"

def make_kyc_req_id(seq: int, year: int = 2026) -> str:
    return f"KYC-{year}-{seq:06d}"

def make_doc_id(customer_id: str, seq: int) -> str:
    return f"DOC-{customer_id}-{seq:03d}"

def make_rev_id(customer_id: str, year: int = 2026, seq: int = 1) -> str:
    return f"REV-{customer_id}-{year}-{seq:02d}"

def make_alert_id(seq: int, year: int = 2026) -> str:
    return f"ALT-{year}-{seq:06d}"

def make_bo_id(customer_id: str, seq: int) -> str:
    return f"BO-{customer_id}-{seq:03d}"

def make_ver_id(doc_id: str, seq: int) -> str:
    return f"VER-{doc_id}-{seq:03d}"

def make_audit_id(seq: int, year: int = 2026) -> str:
    return f"AUD-{year}-{seq:06d}"

def make_rr_id(customer_id: str, seq: int) -> str:
    return f"RR-{customer_id}-{seq:03d}"


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    if delta <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta))

def years_ago(n: int) -> date:
    today = date(2026, 10, 22)
    return date(today.year - n, today.month, today.day)

def months_from_now(n: int, base: date = None) -> date:
    base = base or date(2026, 10, 22)
    month = base.month + n
    year = base.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return date(year, month, min(base.day, 28))


def add_years(value: date, years: int) -> date:
    """Add calendar years, clamping leap-day dates to February 28."""
    target_year = value.year + years
    try:
        return value.replace(year=target_year)
    except ValueError:
        if value.month == 2 and value.day == 29:
            return value.replace(year=target_year, day=28)
        raise


REFERENCE_DATE = date(2026, 10, 22)
REFERENCE_DATETIME = datetime.combine(REFERENCE_DATE, datetime.min.time())


# ---------------------------------------------------------------------------
# STEP 1: Customer Types (master data)
# ---------------------------------------------------------------------------

CUSTOMER_TYPE_SPECS = [
    {
        "code": CustomerTypeCode.INDIVIDUAL,
        "name": "Individual",
        "description": "Natural person customer",
        "requires_beneficial_owner": False,
        "periodic_review_months": 24,
    },
    {
        "code": CustomerTypeCode.SOLE_TRADER,
        "name": "Sole Trader",
        "description": "Individual operating a business in their own name",
        "requires_beneficial_owner": False,
        "periodic_review_months": 18,
    },
    {
        "code": CustomerTypeCode.PARTNERSHIP,
        "name": "Partnership",
        "description": "Partnership or limited partnership",
        "requires_beneficial_owner": True,
        "periodic_review_months": 12,
    },
    {
        "code": CustomerTypeCode.PRIVATE_COMPANY,
        "name": "Private Limited Company",
        "description": "Private limited company",
        "requires_beneficial_owner": True,
        "periodic_review_months": 12,
    },
    {
        "code": CustomerTypeCode.PUBLIC_COMPANY,
        "name": "Public Limited Company",
        "description": "Public listed company",
        "requires_beneficial_owner": True,
        "periodic_review_months": 12,
    },
    {
        "code": CustomerTypeCode.TRUST,
        "name": "Trust",
        "description": "Trust or foundation",
        "requires_beneficial_owner": True,
        "periodic_review_months": 12,
    },
    {
        "code": CustomerTypeCode.NON_PROFIT,
        "name": "Non-Profit Organisation",
        "description": "Charity, NGO or non-profit entity",
        "requires_beneficial_owner": True,
        "periodic_review_months": 18,
    },
]


def seed_customer_types(db: Session) -> Dict[str, CustomerType]:
    types = {}
    for spec in CUSTOMER_TYPE_SPECS:
        ct = CustomerType(
            code=spec["code"],
            name=spec["name"],
            description=spec["description"],
            requires_beneficial_owner=spec["requires_beneficial_owner"],
            periodic_review_months=spec["periodic_review_months"],
            is_active=True,
            created_at=datetime(2026, 1, 1),
        )
        db.add(ct)
        types[spec["code"].value] = ct
    db.flush()
    return types


# ---------------------------------------------------------------------------
# STEP 2: KYC Requirements
# ---------------------------------------------------------------------------

KYC_REQUIREMENTS_SPEC = [
    # INDIVIDUAL
    {"ct": CustomerTypeCode.INDIVIDUAL, "cat": DocumentCategory.IDENTITY,
     "doc": "Passport", "type": RequirementType.MANDATORY, "max_age": 120},
    {"ct": CustomerTypeCode.INDIVIDUAL, "cat": DocumentCategory.ADDRESS,
     "doc": "Utility Bill", "type": RequirementType.MANDATORY, "max_age": 3},
    {"ct": CustomerTypeCode.INDIVIDUAL, "cat": DocumentCategory.IDENTITY,
     "doc": "Driver's Licence", "type": RequirementType.CONDITIONAL, "max_age": 120},
    # SOLE_TRADER
    {"ct": CustomerTypeCode.SOLE_TRADER, "cat": DocumentCategory.IDENTITY,
     "doc": "Passport", "type": RequirementType.MANDATORY, "max_age": 120},
    {"ct": CustomerTypeCode.SOLE_TRADER, "cat": DocumentCategory.ADDRESS,
     "doc": "Utility Bill", "type": RequirementType.MANDATORY, "max_age": 3},
    {"ct": CustomerTypeCode.SOLE_TRADER, "cat": DocumentCategory.BUSINESS,
     "doc": "Business Licence", "type": RequirementType.MANDATORY, "max_age": 24},
    # PARTNERSHIP
    {"ct": CustomerTypeCode.PARTNERSHIP, "cat": DocumentCategory.IDENTITY,
     "doc": "Passport", "type": RequirementType.MANDATORY, "max_age": 120},
    {"ct": CustomerTypeCode.PARTNERSHIP, "cat": DocumentCategory.BUSINESS,
     "doc": "Partnership Deed", "type": RequirementType.MANDATORY, "max_age": None},
    {"ct": CustomerTypeCode.PARTNERSHIP, "cat": DocumentCategory.OWNERSHIP,
     "doc": "Beneficial Ownership Declaration", "type": RequirementType.MANDATORY, "max_age": 12},
    {"ct": CustomerTypeCode.PARTNERSHIP, "cat": DocumentCategory.FINANCIAL,
     "doc": "Audited Financial Statements", "type": RequirementType.MANDATORY, "max_age": 12},
    # PRIVATE_COMPANY
    {"ct": CustomerTypeCode.PRIVATE_COMPANY, "cat": DocumentCategory.BUSINESS,
     "doc": "Certificate of Incorporation", "type": RequirementType.MANDATORY, "max_age": None},
    {"ct": CustomerTypeCode.PRIVATE_COMPANY, "cat": DocumentCategory.BUSINESS,
     "doc": "Articles of Association", "type": RequirementType.MANDATORY, "max_age": None},
    {"ct": CustomerTypeCode.PRIVATE_COMPANY, "cat": DocumentCategory.OWNERSHIP,
     "doc": "Register of Members", "type": RequirementType.MANDATORY, "max_age": 12},
    {"ct": CustomerTypeCode.PRIVATE_COMPANY, "cat": DocumentCategory.OWNERSHIP,
     "doc": "Beneficial Ownership Declaration", "type": RequirementType.MANDATORY, "max_age": 12},
    {"ct": CustomerTypeCode.PRIVATE_COMPANY, "cat": DocumentCategory.FINANCIAL,
     "doc": "Audited Financial Statements", "type": RequirementType.MANDATORY, "max_age": 12},
    {"ct": CustomerTypeCode.PRIVATE_COMPANY, "cat": DocumentCategory.IDENTITY,
     "doc": "Passport", "type": RequirementType.MANDATORY, "max_age": 120},
    # PUBLIC_COMPANY
    {"ct": CustomerTypeCode.PUBLIC_COMPANY, "cat": DocumentCategory.BUSINESS,
     "doc": "Certificate of Incorporation", "type": RequirementType.MANDATORY, "max_age": None},
    {"ct": CustomerTypeCode.PUBLIC_COMPANY, "cat": DocumentCategory.BUSINESS,
     "doc": "Company Search Report", "type": RequirementType.MANDATORY, "max_age": 3},
    {"ct": CustomerTypeCode.PUBLIC_COMPANY, "cat": DocumentCategory.FINANCIAL,
     "doc": "Audited Financial Statements", "type": RequirementType.MANDATORY, "max_age": 12},
    {"ct": CustomerTypeCode.PUBLIC_COMPANY, "cat": DocumentCategory.COMPLIANCE,
     "doc": "Sanctions Screening Report", "type": RequirementType.MANDATORY, "max_age": 12},
    # TRUST
    {"ct": CustomerTypeCode.TRUST, "cat": DocumentCategory.BUSINESS,
     "doc": "Trust Deed", "type": RequirementType.MANDATORY, "max_age": None},
    {"ct": CustomerTypeCode.TRUST, "cat": DocumentCategory.IDENTITY,
     "doc": "Passport", "type": RequirementType.MANDATORY, "max_age": 120},
    {"ct": CustomerTypeCode.TRUST, "cat": DocumentCategory.OWNERSHIP,
     "doc": "Beneficial Ownership Declaration", "type": RequirementType.MANDATORY, "max_age": 12},
    {"ct": CustomerTypeCode.TRUST, "cat": DocumentCategory.COMPLIANCE,
     "doc": "AML Policy", "type": RequirementType.MANDATORY, "max_age": 24},
    # NON_PROFIT
    {"ct": CustomerTypeCode.NON_PROFIT, "cat": DocumentCategory.BUSINESS,
     "doc": "Certificate of Incorporation", "type": RequirementType.MANDATORY, "max_age": None},
    {"ct": CustomerTypeCode.NON_PROFIT, "cat": DocumentCategory.COMPLIANCE,
     "doc": "AML Policy", "type": RequirementType.MANDATORY, "max_age": 24},
    {"ct": CustomerTypeCode.NON_PROFIT, "cat": DocumentCategory.FINANCIAL,
     "doc": "Audited Financial Statements", "type": RequirementType.MANDATORY, "max_age": 12},
]


def seed_kyc_requirements(db: Session, customer_types: Dict[str, CustomerType]) -> List[KYCRequirement]:
    reqs = []
    for i, spec in enumerate(KYC_REQUIREMENTS_SPEC, 1):
        ct = customer_types[spec["ct"].value]
        req = KYCRequirement(
            requirement_id=make_kyc_req_id(i),
            customer_type_id=ct.id,
            document_category=spec["cat"],
            document_type=spec["doc"],
            requirement_type=spec["type"],
            max_age_months=spec.get("max_age"),
            is_active=True,
            effective_from=date(2026, 1, 1),
            effective_to=None,
            created_at=datetime(2026, 1, 1),
        )
        db.add(req)
        reqs.append(req)
    db.flush()
    return reqs


# ---------------------------------------------------------------------------
# STEP 3: Generate Customers
# ---------------------------------------------------------------------------

def _pick_risk_level(country: str, is_pep: bool) -> RiskLevel:
    if is_pep:
        return RiskLevel.HIGH
    if country in HIGH_RISK_COUNTRIES:
        return random.choice([RiskLevel.HIGH, RiskLevel.VERY_HIGH])
    weights = [0.5, 0.3, 0.15, 0.05]
    return random.choices(list(RiskLevel), weights=weights, k=1)[0]


def generate_customers(
    db: Session,
    customer_types: Dict[str, CustomerType],
    count: int,
    target_business_entities: Optional[int] = None,
) -> List[Customer]:
    customers = []
    ct_list = list(customer_types.values())

    # Keep type variation, but make the required business-entity volume exact.
    weight_by_code = {
        CustomerTypeCode.INDIVIDUAL: 65,
        CustomerTypeCode.SOLE_TRADER: 15,
        CustomerTypeCode.PARTNERSHIP: 5,
        CustomerTypeCode.PRIVATE_COMPANY: 7,
        CustomerTypeCode.PUBLIC_COMPANY: 2,
        CustomerTypeCode.TRUST: 3,
        CustomerTypeCode.NON_PROFIT: 3,
    }
    if target_business_entities is None:
        # Backward-compatible proportional mode for callers that omit a target.
        assigned_types = random.choices(
            ct_list,
            weights=[weight_by_code.get(ct.code, 1) for ct in ct_list],
            k=count,
        )
    else:
        target_business_entities = max(0, min(count, target_business_entities))
        business_types = [ct for ct in ct_list if ct.requires_beneficial_owner]
        non_business_types = [ct for ct in ct_list if not ct.requires_beneficial_owner]
        business_choices = random.choices(
            business_types,
            weights=[weight_by_code.get(ct.code, 1) for ct in business_types],
            k=target_business_entities,
        ) if target_business_entities else []
        non_business_count = count - target_business_entities
        non_business_choices = random.choices(
            non_business_types,
            weights=[weight_by_code.get(ct.code, 1) for ct in non_business_types],
            k=non_business_count,
        ) if non_business_count else []
        assigned_types = business_choices + non_business_choices
        random.shuffle(assigned_types)

    for seq, ct in enumerate(assigned_types, 1):
        is_individual = ct.code in (CustomerTypeCode.INDIVIDUAL, CustomerTypeCode.SOLE_TRADER)
        country = random.choice(COUNTRIES)
        is_pep = random.random() < 0.03    # 3% PEP
        is_sanctioned = random.random() < 0.005

        onboard_date = random_date(date(2020, 1, 1), date(2026, 9, 30))
        approved = random.random() < 0.75   # 75% are approved

        status = OnboardingStatus.APPROVED if approved else random.choice([
            OnboardingStatus.PENDING, OnboardingStatus.IN_PROGRESS,
            OnboardingStatus.REJECTED, OnboardingStatus.SUSPENDED,
        ])

        approved_date = None
        if status == OnboardingStatus.APPROVED:
            approved_date = onboard_date + timedelta(days=random.randint(3, 30))

        full_name = fake.name() if is_individual else fake.company()
        cust_id = make_customer_id(seq)

        c = Customer(
            customer_id=cust_id,
            full_name=full_name,
            date_of_birth=random_date(years_ago(70), years_ago(18)) if is_individual else None,
            nationality=random.choice(COUNTRIES) if is_individual else None,
            country_of_residence=country,
            email=fake.email(),
            phone=fake.phone_number()[:50],
            address_line1=fake.street_address()[:200],
            city=fake.city()[:100],
            state_province=fake.state()[:100] if hasattr(fake, 'state') else "N/A",
            postal_code=fake.postcode()[:20],
            country=country,
            customer_type_id=ct.id,
            onboarding_status=status,
            is_pep=is_pep,
            is_sanctioned=is_sanctioned,
            source_of_funds=random.choice([
                "Employment", "Business Income", "Investments",
                "Inheritance", "Property Sale", "Pension",
            ]),
            onboarding_date=onboard_date,
            approved_date=approved_date,
            kyc_completeness_pct=Decimal("0.00"),
            created_at=datetime.combine(onboard_date, datetime.min.time()),
            updated_at=datetime.combine(onboard_date, datetime.min.time()),
        )

        # Business fields
        if not is_individual:
            c.business_name = full_name
            c.business_registration_number = fake.numerify("##########")
            c.incorporation_date = random_date(years_ago(20), years_ago(1))
            c.incorporation_country = country

        db.add(c)
        customers.append(c)

        if seq % 500 == 0:
            db.flush()
            print(f"  Generated {seq}/{count} customers...")

    db.flush()
    return customers


# ---------------------------------------------------------------------------
# STEP 4: Risk Ratings
# ---------------------------------------------------------------------------

def generate_risk_ratings(
    db: Session,
    customers: List[Customer],
) -> List[RiskRating]:
    ratings = []
    rr_seq = 1

    for cust in customers:
        country = cust.country_of_residence or "United Kingdom"
        risk_level = _pick_risk_level(country, cust.is_pep)
        risk_score = {
            RiskLevel.LOW: random.uniform(10, 30),
            RiskLevel.MEDIUM: random.uniform(31, 60),
            RiskLevel.HIGH: random.uniform(61, 85),
            RiskLevel.VERY_HIGH: random.uniform(86, 100),
        }[risk_level]

        assessed_at = datetime.combine(
            cust.onboarding_date + timedelta(days=random.randint(0, 5)),
            datetime.min.time()
        )

        rr = RiskRating(
            risk_rating_id=make_rr_id(cust.customer_id, 1),
            customer_id=cust.id,
            risk_level=risk_level,
            risk_score=Decimal(str(round(risk_score, 2))),
            assessed_by=random.choice(OFFICERS[:20]),
            assessed_at=assessed_at,
            effective_from=cust.onboarding_date,
            effective_to=None,
            pep_flag=cust.is_pep,
            sanctions_flag=cust.is_sanctioned,
            geographic_risk=("HIGH" if country in HIGH_RISK_COUNTRIES else "LOW"),
            industry_risk=random.choice(["LOW", "MEDIUM", "HIGH"]),
            created_at=assessed_at,
        )
        db.add(rr)
        ratings.append(rr)
        rr_seq += 1

        if rr_seq % 500 == 0:
            db.flush()

    db.flush()
    return ratings


# ---------------------------------------------------------------------------
# STEP 5: Beneficial Owners (for business customers)
# ---------------------------------------------------------------------------

def generate_beneficial_owners(
    db: Session,
    customers: List[Customer],
) -> List[BeneficialOwner]:
    bos = []
    bo_seq_global = 1

    business_customers = [
        c for c in customers
        if c.customer_type and c.customer_type.requires_beneficial_owner
    ]

    for bc in business_customers:
        num_owners = random.randint(1, 4)
        # Normal case: percentages sum to ~100%
        percentages = _split_ownership(num_owners)

        for bo_seq, pct in enumerate(percentages, 1):
            bo = BeneficialOwner(
                bo_id=make_bo_id(bc.customer_id, bo_seq),
                business_customer_id=bc.id,
                individual_customer_id=None,
                full_name=fake.name(),
                date_of_birth=random_date(years_ago(65), years_ago(25)),
                nationality=random.choice(COUNTRIES),
                country_of_residence=random.choice(COUNTRIES),
                ownership_percentage=Decimal(str(pct)),
                control_type=random.choice(["Direct", "Indirect", "Joint"]),
                is_pep=random.random() < 0.05,
                is_sanctioned=False,
                is_verified=random.random() < 0.8,
                verification_date=bc.onboarding_date + timedelta(days=random.randint(1, 30)) if random.random() < 0.8 else None,
                is_active=True,
                created_at=datetime.combine(bc.onboarding_date, datetime.min.time()),
            updated_at=datetime.combine(bc.onboarding_date, datetime.min.time()),
            )
            db.add(bo)
            bos.append(bo)
            bo_seq_global += 1

        if bo_seq_global % 200 == 0:
            db.flush()

    db.flush()
    return bos


def _split_ownership(n: int) -> List[Decimal]:
    """Split ownership into exact two-decimal percentages totaling 100%."""

    if n < 1:
        raise ValueError("Number of owners must be at least 1")

    if n == 1:
        return [Decimal("100.00")]

    # Generate unique cut points in integer cents.
    cuts = sorted(random.sample(range(1, 10000), n - 1))

    boundaries = [0] + cuts + [10000]

    # Calculate exact ownership percentages.
    percentages = [
        Decimal(boundaries[i + 1] - boundaries[i]) / Decimal("100")
        for i in range(n)
    ]

    return percentages


# ---------------------------------------------------------------------------
# STEP 6: Documents
# ---------------------------------------------------------------------------

def _get_requirements_for_customer(customer: Customer, all_reqs: List[KYCRequirement]) -> List[KYCRequirement]:
    return [r for r in all_reqs if r.customer_type_id == customer.customer_type_id]



def generate_documents(
    db: Session,
    customers: List[Customer],
    all_reqs: List[KYCRequirement],
    target_total: int,
) -> Tuple[List[Document], Dict[int, int]]:
    """Generate mandatory and additional documents for customers."""

    documents = []
    doc_seq_per_customer: Dict[int, int] = {}
    total_so_far = 0

    # Step 1: Generate mandatory documents for every customer.
    for cust in customers:

        reqs = _get_requirements_for_customer(cust, all_reqs)

        mandatory_reqs = [
            r for r in reqs
            if r.requirement_type == RequirementType.MANDATORY
        ]

        seq = doc_seq_per_customer.get(cust.id, 1)

        # Approved customers must receive all mandatory evidence.
        ensure_kyc_valid = (
            cust.onboarding_status == OnboardingStatus.APPROVED
        )

        for req in mandatory_reqs:

            # Preserve randomized evidence generation for
            # customers who are not approved.
            should_generate = (
                ensure_kyc_valid or random.random() < 0.90
            )

            if should_generate:
                doc = _create_document(
                    cust,
                    req.document_type,
                    req.document_category,
                    seq,
                    ensure_kyc_valid=ensure_kyc_valid,
                    max_age_months=req.max_age_months,
                )

                db.add(doc)
                documents.append(doc)

                seq += 1
                total_so_far += 1

        doc_seq_per_customer[cust.id] = seq

        if total_so_far > 0 and total_so_far % 1000 == 0:
            db.flush()
            print(f"  Generated {total_so_far} documents...")

    # Step 2: Add extra documents to reach the target.
    remaining = target_total - total_so_far

    if remaining > 0:
        extra_per_customer = max(
            1, remaining // len(customers)
        )

        for cust in customers[:min(len(customers), remaining)]:

            for _ in range(min(extra_per_customer, 3)):

                cat = random.choice(list(DocumentCategory))

                doc_type = random.choice(
                    DOCUMENT_TYPES_BY_CATEGORY.get(
                        cat, ["Generic Document"]
                    )
                )

                seq = doc_seq_per_customer.get(cust.id, 1)

                doc = _create_document(
                    cust,
                    doc_type,
                    cat,
                    seq,
                )

                db.add(doc)
                documents.append(doc)

                seq += 1
                doc_seq_per_customer[cust.id] = seq
                total_so_far += 1

                if total_so_far >= target_total:
                    break

            if total_so_far >= target_total:
                break

    db.flush()

    print(f"  Total documents generated: {total_so_far}")

    return documents, doc_seq_per_customer


def _create_document(
    customer: Customer,
    doc_type: str,
    doc_category: DocumentCategory,
    seq: int,
    ensure_kyc_valid: bool = False,
    max_age_months: Optional[int] = None,
) -> Document:

    if ensure_kyc_valid:
        # Generate recent evidence for approved customers.
        max_age_days = (
            max_age_months * 30
            if max_age_months is not None
            else 365
        )

        # Keep a safety margin so short-validity documents
        # do not expire on the evaluation date.
        safe_windows = {
            DocumentCategory.IDENTITY: 365,
            DocumentCategory.ADDRESS: 60,
            DocumentCategory.FINANCIAL: 180,
            DocumentCategory.OWNERSHIP: 180,
        }

        safe_days = min(
            max_age_days,
            safe_windows.get(doc_category, 365),
        )

        earliest_date = REFERENCE_DATE - timedelta(days=safe_days)

        if customer.onboarding_date:
            earliest_date = max(
                earliest_date,
                customer.onboarding_date,
            )

        issue_date = random_date(
            earliest_date,
            REFERENCE_DATE,
        )

    else:
        # Retain existing historical document generation.
        issue_date = random_date(
            customer.onboarding_date - timedelta(days=365 * 5),
            customer.onboarding_date,
        )

    # Set expiry based on document category.
    if doc_category == DocumentCategory.IDENTITY:
        expiry_date = add_years(issue_date, random.randint(5, 10))

    elif doc_category == DocumentCategory.ADDRESS:
        expiry_date = issue_date + timedelta(days=90)

    elif doc_category in (
        DocumentCategory.FINANCIAL,
        DocumentCategory.OWNERSHIP,
    ):
        expiry_date = add_years(issue_date, 1)

    else:
        expiry_date = None

    is_expired = (
        expiry_date is not None
        and expiry_date < REFERENCE_DATE
    )

    if ensure_kyc_valid:
        if is_expired:
            raise ValueError(
                f"Approved customer's mandatory document is expired: "
                f"{customer.customer_id} / {doc_type}"
            )

        status = DocumentStatus.VERIFIED

    elif is_expired:
        status = DocumentStatus.EXPIRED

    else:
        status = random.choices(
            [
                DocumentStatus.VERIFIED,
                DocumentStatus.SUBMITTED,
                DocumentStatus.PENDING,
                DocumentStatus.REJECTED,
            ],
            weights=[0.70, 0.15, 0.10, 0.05],
            k=1,
        )[0]

    submitted_on = min(
        issue_date + timedelta(days=random.randint(1, 30)),
        REFERENCE_DATE,
    )

    if ensure_kyc_valid:
        available_days = (REFERENCE_DATE - issue_date).days

        submitted_on = issue_date + timedelta(
            days=random.randint(0, min(10, available_days))
        )

    doc = Document(
        document_id=make_doc_id(customer.customer_id, seq),
        customer_id=customer.id,
        document_category=doc_category,
        document_type=doc_type,
        document_number=fake.numerify("??-########"),
        issuing_authority=random.choice(
            ISSUERS.get(doc_category, ["Authority"])
        ),
        issuing_country=customer.country_of_residence or "United Kingdom",
        issue_date=issue_date,
        expiry_date=expiry_date,
        document_status=status,
        is_mandatory=True,
        submitted_at=datetime.combine(
            submitted_on,
            datetime.min.time(),
        ),
        created_at=datetime.combine(
            customer.onboarding_date,
            datetime.min.time(),
        ),
        updated_at=datetime.combine(
            customer.onboarding_date,
            datetime.min.time(),
        ),
    )

    return doc

# ---------------------------------------------------------------------------
# STEP 7: Verifications
# ---------------------------------------------------------------------------

def generate_verifications(
    db: Session,
    documents: List[Document],
    customers: List[Customer],
) -> List[Verification]:
    """Generate at least one verification per submitted/verified/rejected document."""
    verifications = []
    ver_seq_per_doc: Dict[int, int] = {}

    # Build a quick customer lookup
    cust_by_id = {c.id: c for c in customers}

    for doc in documents:
        if doc.document_status not in (DocumentStatus.VERIFIED, DocumentStatus.REJECTED,
                                       DocumentStatus.SUBMITTED):
            continue

        cust = cust_by_id.get(doc.customer_id)
        if not cust:
            continue

        seq = ver_seq_per_doc.get(doc.id, 1)
        verification_start = doc.submitted_at.date()
        verified_at = datetime.combine(
            random_date(verification_start, REFERENCE_DATE),
            datetime.min.time()
        )

        name_match = random.random() > 0.05  # 5% name mismatch
        decision = VerificationDecision.PASS if doc.document_status == DocumentStatus.VERIFIED else \
                   VerificationDecision.FAIL if doc.document_status == DocumentStatus.REJECTED else \
                   VerificationDecision.PENDING

        ver = Verification(
            verification_id=make_ver_id(doc.document_id, seq),
            document_id=doc.id,
            verified_by=random.choice(OFFICERS),
            verified_at=verified_at,
            decision=decision,
            decision_reason=("Document verified successfully" if decision == VerificationDecision.PASS
                             else "Document rejected — insufficient quality" if decision == VerificationDecision.FAIL
                             else "Pending review"),
            name_match=name_match,
            name_on_document=cust.full_name if name_match else fake.name(),
            expiry_check_passed=doc.expiry_date is None or doc.expiry_date >= REFERENCE_DATE,
            authenticity_check_passed=decision == VerificationDecision.PASS,
            override_flag=False,
            created_at=verified_at,
        )
        db.add(ver)
        verifications.append(ver)
        ver_seq_per_doc[doc.id] = seq + 1

        if len(verifications) % 1000 == 0:
            db.flush()

    db.flush()
    return verifications


# ---------------------------------------------------------------------------
# STEP 8: KYC Completeness (update per customer)
# ---------------------------------------------------------------------------

def update_kyc_completeness(
    db: Session,
    customers: List[Customer],
    all_reqs: List[KYCRequirement],
    documents: List[Document],
) -> None:
    """Calculate and update kyc_completeness_pct for each customer."""
    # Build doc lookup by customer
    docs_by_customer: Dict[int, List[Document]] = {}
    for doc in documents:
        docs_by_customer.setdefault(doc.customer_id, []).append(doc)

    # Build CDR records
    cdr_records = []
    for cust in customers:
        reqs = [r for r in all_reqs
                if r.customer_type_id == cust.customer_type_id
                and r.requirement_type == RequirementType.MANDATORY]
        if not reqs:
            cust.kyc_completeness_pct = Decimal("100.00")
            continue

        fulfilled = 0
        cust_docs = docs_by_customer.get(cust.id, [])
        fulfilled_doc_types = {d.document_type for d in cust_docs
                               if d.document_status == DocumentStatus.VERIFIED}

        for req in reqs:
            is_fulfilled = req.document_type in fulfilled_doc_types
            if is_fulfilled:
                fulfilled += 1
            # find matching doc
            matched_doc = next(
                (d for d in cust_docs if d.document_type == req.document_type
                 and d.document_status == DocumentStatus.VERIFIED),
                None
            )
            cdr = CustomerDocumentRequirement(
                customer_id=cust.id,
                requirement_id=req.id,
                document_id=matched_doc.id if matched_doc else None,
                is_fulfilled=is_fulfilled,
                fulfilled_at=matched_doc.submitted_at if matched_doc else None,
                created_at=datetime.combine(cust.onboarding_date, datetime.min.time()),
                updated_at=datetime.combine(cust.onboarding_date, datetime.min.time()),
            )
            cdr_records.append(cdr)

        pct = round(fulfilled / len(reqs) * 100, 2)
        cust.kyc_completeness_pct = Decimal(str(pct))

    db.bulk_save_objects(cdr_records)
    db.flush()


# ---------------------------------------------------------------------------
# STEP 9: Review Cases
# ---------------------------------------------------------------------------

def generate_review_cases(
    db: Session,
    customers: List[Customer],
    target: int,
) -> List[ReviewCase]:
    reviews = []
    rev_seq_per_cust: Dict[int, int] = {}

    # Prioritise approved customers and high-risk
    eligible = [c for c in customers if c.onboarding_status == OnboardingStatus.APPROVED]
    if len(eligible) < target:
        eligible = customers

    sample = random.choices(eligible, k=min(target, len(eligible)))

    for cust in sample:
        seq = rev_seq_per_cust.get(cust.id, 1)
        year = random.choice([2024, 2025, 2026])
        trigger = random.choice(list(ReviewTrigger))
        opened_at = datetime.combine(
            random_date(date(year, 1, 1), REFERENCE_DATE),
            datetime.min.time()
        )
        due_days = random.randint(14, 90)
        due_date = (opened_at + timedelta(days=due_days)).date()

        # 70% resolved
        if random.random() < 0.70:
            closed_at = opened_at + timedelta(days=random.randint(1, due_days))
            status = ReviewCaseStatus.CLOSED_RESOLVED
            resolution = "All documents verified. Customer approved for continued onboarding."
        else:
            closed_at = None
            # Is it overdue?
            status = ReviewCaseStatus.OVERDUE if due_date < REFERENCE_DATE else ReviewCaseStatus.IN_PROGRESS
            resolution = None

        rev_id = make_rev_id(cust.customer_id, year, seq)
        review = ReviewCase(
            review_id=rev_id,
            customer_id=cust.id,
            trigger=trigger,
            status=status,
            opened_at=opened_at,
            due_date=due_date,
            closed_at=closed_at,
            assigned_to=random.choice(OFFICERS[:20]),
            findings="Periodic review initiated per policy." if trigger == ReviewTrigger.PERIODIC else
                     f"{trigger.value} triggered review.",
            resolution=resolution,
            closed_without_resolution=False,
            created_at=opened_at,
            updated_at=opened_at,
        )
        db.add(review)
        reviews.append(review)
        rev_seq_per_cust[cust.id] = seq + 1

        if len(reviews) % 500 == 0:
            db.flush()

    db.flush()
    return reviews


# ---------------------------------------------------------------------------
# STEP 10: Alerts
# ---------------------------------------------------------------------------

def generate_alerts(
    db: Session,
    customers: List[Customer],
    documents: List[Document],
    review_cases: List[ReviewCase],
) -> List[Alert]:
    alerts = []
    alert_seq = 1

    docs_by_customer: Dict[int, List[Document]] = {}
    for doc in documents:
        docs_by_customer.setdefault(doc.customer_id, []).append(doc)

    rev_by_customer: Dict[int, List[ReviewCase]] = {}
    for rev in review_cases:
        rev_by_customer.setdefault(rev.customer_id, []).append(rev)

    for cust in customers:
        cust_docs = docs_by_customer.get(cust.id, [])
        cust_revs = rev_by_customer.get(cust.id, [])

        # Document expiry alerts
        for doc in cust_docs:
            if doc.expiry_date:
                days_to_expiry = (doc.expiry_date - REFERENCE_DATE).days
                if days_to_expiry < 0:
                    # Expired
                    alert = _make_alert(
                        alert_seq, cust, AlertType.DOCUMENT_EXPIRED,
                        AlertSeverity.HIGH, AlertStatus.OPEN,
                        f"Document {doc.document_id} expired on {doc.expiry_date}",
                        doc_id=doc.id,
                    )
                    db.add(alert)
                    alerts.append(alert)
                    alert_seq += 1
                elif days_to_expiry <= 30:
                    # Expiring soon
                    alert = _make_alert(
                        alert_seq, cust, AlertType.DOCUMENT_EXPIRING,
                        AlertSeverity.MEDIUM, AlertStatus.OPEN,
                        f"Document {doc.document_id} expires in {days_to_expiry} days",
                        doc_id=doc.id,
                    )
                    db.add(alert)
                    alerts.append(alert)
                    alert_seq += 1

        # Overdue review alerts
        for rev in cust_revs:
            if rev.status == ReviewCaseStatus.OVERDUE:
                alert = _make_alert(
                    alert_seq, cust, AlertType.REVIEW_OVERDUE,
                    AlertSeverity.HIGH, AlertStatus.OPEN,
                    f"Review {rev.review_id} is overdue (due {rev.due_date})",
                    review_case_id=rev.id,
                )
                db.add(alert)
                alerts.append(alert)
                alert_seq += 1

        # KYC incomplete
        if float(cust.kyc_completeness_pct or 0) < 100.0 and \
                cust.onboarding_status == OnboardingStatus.APPROVED:
            alert = _make_alert(
                alert_seq, cust, AlertType.KYC_INCOMPLETE,
                AlertSeverity.CRITICAL, AlertStatus.OPEN,
                f"Customer {cust.customer_id} approved but KYC only {cust.kyc_completeness_pct}% complete",
            )
            db.add(alert)
            alerts.append(alert)
            alert_seq += 1

        if alert_seq % 500 == 0:
            db.flush()

    db.flush()
    return alerts


def _make_alert(
    seq: int,
    customer: Customer,
    alert_type: AlertType,
    severity: AlertSeverity,
    status: AlertStatus,
    description: str,
    doc_id: Optional[int] = None,
    review_case_id: Optional[int] = None,
) -> Alert:
    return Alert(
        alert_id=make_alert_id(seq),
        customer_id=customer.id,
        document_id=doc_id,
        review_case_id=review_case_id,
        alert_type=alert_type,
        severity=severity,
        status=status,
        title=f"{alert_type.value.replace('_', ' ').title()} — {customer.customer_id}",
        description=description,
        triggered_at=REFERENCE_DATETIME,
        is_anomaly=False,
        created_at=REFERENCE_DATETIME,
        updated_at=REFERENCE_DATETIME,
    )


# ---------------------------------------------------------------------------
# STEP 11: Audit Events
# ---------------------------------------------------------------------------

def generate_audit_events(
    db: Session,
    customers: List[Customer],
    documents: List[Document],
    reviews: List[ReviewCase],
) -> List[AuditEvent]:
    events = []
    audit_seq = 1

    for cust in customers:
        # Customer created
        ev = _make_audit(audit_seq, cust, "Customer", cust.customer_id,
                         AuditAction.CREATE, "System",
                         datetime.combine(cust.onboarding_date, datetime.min.time()))
        db.add(ev)
        events.append(ev)
        audit_seq += 1

        # Onboarding status change
        if cust.onboarding_status == OnboardingStatus.APPROVED:
            ev = _make_audit(audit_seq, cust, "Customer", cust.customer_id,
                             AuditAction.APPROVE, random.choice(OFFICERS[:20]),
                             datetime.combine(cust.approved_date or cust.onboarding_date,
                                              datetime.min.time()),
                             notes=f"Customer onboarding approved")
            db.add(ev)
            events.append(ev)
            audit_seq += 1

        if audit_seq % 500 == 0:
            db.flush()

    # Document events
    for doc in documents[:min(len(documents), 5000)]:
        ev = _make_audit(audit_seq, None, "Document", doc.document_id,
                         AuditAction.CREATE, "System",
                         doc.created_at or REFERENCE_DATETIME,
                         customer_id=doc.customer_id)
        db.add(ev)
        events.append(ev)
        audit_seq += 1

        if doc.document_status == DocumentStatus.VERIFIED:
            ev = _make_audit(audit_seq, None, "Document", doc.document_id,
                             AuditAction.VERIFY, random.choice(OFFICERS),
                             doc.submitted_at or REFERENCE_DATETIME,
                             customer_id=doc.customer_id)
            db.add(ev)
            events.append(ev)
            audit_seq += 1

        if audit_seq % 500 == 0:
            db.flush()

    # Review events
    for rev in reviews:
        ev = _make_audit(audit_seq, None, "ReviewCase", rev.review_id,
                         AuditAction.REVIEW_OPEN, random.choice(OFFICERS[:20]),
                         rev.opened_at, customer_id=rev.customer_id)
        db.add(ev)
        events.append(ev)
        audit_seq += 1

        if rev.closed_at:
            ev = _make_audit(audit_seq, None, "ReviewCase", rev.review_id,
                             AuditAction.REVIEW_CLOSE, random.choice(OFFICERS[:20]),
                             rev.closed_at, customer_id=rev.customer_id)
            db.add(ev)
            events.append(ev)
            audit_seq += 1

        if audit_seq % 500 == 0:
            db.flush()

    db.flush()
    return events


def _make_audit(
    seq: int,
    customer,
    entity_type: str,
    entity_id: str,
    action: AuditAction,
    performed_by: str,
    performed_at: datetime,
    notes: str = None,
    customer_id: int = None,
) -> AuditEvent:
    return AuditEvent(
        audit_id=make_audit_id(seq),
        customer_id=customer.id if customer else customer_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        performed_by=performed_by,
        performed_at=performed_at,
        notes=notes,
        created_at=performed_at,
    )


# ---------------------------------------------------------------------------
# STEP 12: Anomaly Injection
# ---------------------------------------------------------------------------

def inject_anomalies(
    db: Session,
    customers: List[Customer],
    documents: List[Document],
    reviews: List[ReviewCase],
    beneficial_owners_map: Dict[int, List[BeneficialOwner]],
    alert_seq_start: int,
    audit_seq_start: int,
) -> Dict:
    """
    Inject exactly 5 labelled anomalies into the existing data.
    Returns ground-truth metadata for each anomaly.
    """
    ground_truth = []
    alert_seq = alert_seq_start
    audit_seq = audit_seq_start

    # --- Anomaly 1: Document expired but marked VERIFIED ---
    # Pick a document with expiry_date in the past but set it to VERIFIED
    expired_cand = [d for d in documents if d.expiry_date and d.expiry_date < REFERENCE_DATE
                    and d.document_status != DocumentStatus.VERIFIED][:5]
    if not expired_cand:
        expired_cand = documents[:5]
    anom1_doc = expired_cand[0]
    old_status = anom1_doc.document_status.value
    anom1_doc.document_status = DocumentStatus.VERIFIED
    if not anom1_doc.expiry_date or anom1_doc.expiry_date >= REFERENCE_DATE:
        anom1_doc.expiry_date = REFERENCE_DATE - timedelta(days=random.randint(10, 90))
    anom1_doc.notes = "[ANOMALY-1] Expired document incorrectly marked as VERIFIED"

    # Find the customer for the alert
    anom1_cust = db.query(Customer).filter(Customer.id == anom1_doc.customer_id).first()
    alert1 = Alert(
        alert_id=make_alert_id(alert_seq),
        customer_id=anom1_doc.customer_id,
        document_id=anom1_doc.id,
        alert_type=AlertType.ANOMALY_DETECTED,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.OPEN,
        title=f"ANOMALY-1: Expired document marked VERIFIED — {anom1_doc.document_id}",
        description=f"Document {anom1_doc.document_id} expired on {anom1_doc.expiry_date} but status is VERIFIED",
        triggered_at=REFERENCE_DATETIME,
        is_anomaly=True,
        anomaly_label="EXPIRED_BUT_MARKED_VALID",
        created_at=REFERENCE_DATETIME,
        updated_at=REFERENCE_DATETIME,
    )
    db.add(alert1)
    alert_seq += 1
    ground_truth.append({
        "anomaly_id": 1,
        "label": "EXPIRED_BUT_MARKED_VALID",
        "description": "Document expired but marked as VERIFIED",
        "affected_entity": "Document",
        "affected_id": anom1_doc.document_id,
        "customer_id": anom1_cust.customer_id if anom1_cust else None,
        "detail": f"expiry_date={anom1_doc.expiry_date}, status=VERIFIED",
    })

    # --- Anomaly 2: Customer approved with missing mandatory evidence ---
    # Select a non-approved customer with exactly 0% KYC completeness.
    # Exclude the customer already used for anomaly 1.
    zero_completeness = sorted(
        [
            c for c in customers
            if c.id != anom1_doc.customer_id
            and c.onboarding_status != OnboardingStatus.APPROVED
            and Decimal(str(c.kyc_completeness_pct or 0)) == Decimal("0.00")
        ],
        key=lambda c: c.customer_id,
    )

    if not zero_completeness:
        raise ValueError(
            "Cannot inject anomaly 2: no eligible customer has 0% KYC completeness."
        )

    anom2_cust = zero_completeness[0]
    anom2_cust.onboarding_status = OnboardingStatus.APPROVED
    anom2_cust.approved_date = REFERENCE_DATE

    alert2 = Alert(
        alert_id=make_alert_id(alert_seq),
        customer_id=anom2_cust.id,
        alert_type=AlertType.ANOMALY_DETECTED,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.OPEN,
        title=f"ANOMALY-2: Approved with incomplete KYC ? {anom2_cust.customer_id}",
        description=(
            f"Customer {anom2_cust.customer_id} approved with only "
            f"{anom2_cust.kyc_completeness_pct}% KYC completeness"
        ),
        triggered_at=REFERENCE_DATETIME,
        is_anomaly=True,
        anomaly_label="APPROVED_WITH_MISSING_EVIDENCE",
        created_at=REFERENCE_DATETIME,
        updated_at=REFERENCE_DATETIME,
    )
    db.add(alert2)
    alert_seq += 1
    ground_truth.append({
        "anomaly_id": 2,
        "label": "APPROVED_WITH_MISSING_EVIDENCE",
        "description": "Customer approved with missing mandatory evidence",
        "affected_entity": "Customer",
        "affected_id": anom2_cust.customer_id,
        "customer_id": anom2_cust.customer_id,
        "detail": (
            f"kyc_completeness={anom2_cust.kyc_completeness_pct}%, "
            "onboarding_status=APPROVED"
        ),
    })

    # --- Anomaly 3: Ownership percentages exceed 100% ---
    # Select a business customer with at least three active beneficial owners.
    eligible_business_customers = [
        c for c in customers
        if c.customer_type
        and c.customer_type.requires_beneficial_owner
        and sum(
            1 for bo in beneficial_owners_map.get(c.id, [])
            if bo.is_active
        ) >= 3
    ]

    if not eligible_business_customers:
        raise ValueError(
            "Cannot inject anomaly 3: no business customer has at least "
            "three active beneficial owners."
        )

    anom3_cust = eligible_business_customers[0]

    anom3_bos = db.query(BeneficialOwner).filter(
        BeneficialOwner.business_customer_id == anom3_cust.id,
        BeneficialOwner.is_active == True
    ).all()

    if len(anom3_bos) < 3:
        raise ValueError(
            f"Expected at least three active beneficial owners for "
            f"{anom3_cust.customer_id}."
        )

    # Three owners at 40% each guarantee a total greater than 100%.
    for bo in anom3_bos[:3]:
        bo.ownership_percentage = Decimal("40.00")

    total_now = sum(
        (bo.ownership_percentage for bo in anom3_bos),
        Decimal("0.00")
    )

    alert3 = Alert(
        alert_id=make_alert_id(alert_seq),
        customer_id=anom3_cust.id,
        alert_type=AlertType.OWNERSHIP_MISMATCH,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.OPEN,
        title=f"ANOMALY-3: Ownership exceeds 100% ? {anom3_cust.customer_id}",
        description=(
            f"Beneficial ownership total for {anom3_cust.customer_id} "
            f"= {total_now:.2f}%"
        ),
        triggered_at=REFERENCE_DATETIME,
        is_anomaly=True,
        anomaly_label="OWNERSHIP_EXCEEDS_100",
        created_at=REFERENCE_DATETIME,
        updated_at=REFERENCE_DATETIME,
    )
    db.add(alert3)
    alert_seq += 1
    ground_truth.append({
        "anomaly_id": 3,
        "label": "OWNERSHIP_EXCEEDS_100",
        "description": "Ownership percentages exceed 100%",
        "affected_entity": "BeneficialOwner",
        "affected_id": f"{anom3_cust.customer_id} (multiple BOs)",
        "customer_id": anom3_cust.customer_id,
        "detail": f"total_ownership_pct={total_now:.2f}%",
    })

    # --- Anomaly 4: Review closes without resolution ---
    open_reviews = [
        r for r in reviews
        if r.status in (
            ReviewCaseStatus.IN_PROGRESS,
            ReviewCaseStatus.OPEN,
        )
    ]

    if not open_reviews:
        raise ValueError(
            "Cannot inject anomaly 4: no open review case is available."
        )

    anom4_rev = open_reviews[0]
    anom4_rev.status = ReviewCaseStatus.CLOSED_WITHOUT_RESOLUTION
    anom4_rev.closed_at = datetime.combine(
        REFERENCE_DATE,
        datetime.min.time()
    )
    anom4_rev.closed_without_resolution = True
    anom4_rev.resolution = None
    anom4_rev.findings = "[ANOMALY-4] Case closed without adequate resolution"

    anom4_cust = db.query(Customer).filter(
        Customer.id == anom4_rev.customer_id
    ).first()

    alert4 = Alert(
        alert_id=make_alert_id(alert_seq),
        customer_id=anom4_rev.customer_id,
        review_case_id=anom4_rev.id,
        alert_type=AlertType.ANOMALY_DETECTED,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        title=f"ANOMALY-4: Review closed without resolution ? {anom4_rev.review_id}",
        description=(
            f"Review case {anom4_rev.review_id} was closed without "
            "formal resolution"
        ),
        triggered_at=REFERENCE_DATETIME,
        is_anomaly=True,
        anomaly_label="REVIEW_CLOSED_WITHOUT_RESOLUTION",
        created_at=REFERENCE_DATETIME,
        updated_at=REFERENCE_DATETIME,
    )
    db.add(alert4)
    alert_seq += 1
    ground_truth.append({
        "anomaly_id": 4,
        "label": "REVIEW_CLOSED_WITHOUT_RESOLUTION",
        "description": "Review case closed without resolution",
        "affected_entity": "ReviewCase",
        "affected_id": anom4_rev.review_id,
        "customer_id": anom4_cust.customer_id if anom4_cust else None,
        "detail": (
            f"closed_at={anom4_rev.closed_at}, resolution=None"
        ),
    })

    # --- Anomaly 5: Duplicate document used across unrelated customers ---
    # Pick a document, duplicate its number for another customer
    if len(documents) >= 20:
        orig_doc = documents[10]
        dup_target_docs = [d for d in documents
                           if d.customer_id != orig_doc.customer_id
                           and d.document_type == orig_doc.document_type][:3]
        if dup_target_docs:
            dup_doc = dup_target_docs[0]
            dup_doc.document_number = orig_doc.document_number  # Same number!
            dup_doc.is_duplicate_suspect = True
            dup_doc.duplicate_of_document_id = orig_doc.document_id
            orig_doc.is_duplicate_suspect = True

            dup_cust = db.query(Customer).filter(Customer.id == dup_doc.customer_id).first()
            alert5 = Alert(
                alert_id=make_alert_id(alert_seq),
                customer_id=dup_doc.customer_id,
                document_id=dup_doc.id,
                alert_type=AlertType.DUPLICATE_DOCUMENT,
                severity=AlertSeverity.CRITICAL,
                status=AlertStatus.OPEN,
                title=f"ANOMALY-5: Duplicate document number — {dup_doc.document_id}",
                description=f"Document number {dup_doc.document_number} used in {orig_doc.document_id} "
                            f"and {dup_doc.document_id} for different customers",
                triggered_at=REFERENCE_DATETIME,
                is_anomaly=True,
                anomaly_label="DUPLICATE_DOCUMENT_CROSS_CUSTOMER",
                created_at=REFERENCE_DATETIME,
            )
            db.add(alert5)
            alert_seq += 1
            ground_truth.append({
                "anomaly_id": 5,
                "label": "DUPLICATE_DOCUMENT_CROSS_CUSTOMER",
                "description": "Duplicate document number used across unrelated customers",
                "affected_entity": "Document",
                "affected_id": f"{orig_doc.document_id} / {dup_doc.document_id}",
                "customer_id": f"{db.query(Customer).get(orig_doc.customer_id).customer_id if db.query(Customer).get(orig_doc.customer_id) else 'N/A'} / {dup_cust.customer_id if dup_cust else 'N/A'}",
                "detail": f"document_number={dup_doc.document_number}",
            })

    db.flush()
    return {"anomalies": ground_truth, "alert_seq": alert_seq, "audit_seq": audit_seq}


# ---------------------------------------------------------------------------
# STEP 13: Next review date population
# ---------------------------------------------------------------------------

def populate_review_dates(customers: List[Customer], risk_ratings: List[RiskRating]) -> None:
    """Set next_review_date on approved customers based on risk."""
    rr_by_cust = {}
    for rr in risk_ratings:
        if rr.effective_to is None:
            rr_by_cust[rr.customer_id] = rr

    for cust in customers:
        if cust.onboarding_status != OnboardingStatus.APPROVED:
            continue
        rr = rr_by_cust.get(cust.id)
        risk_level = rr.risk_level if rr else RiskLevel.MEDIUM
        base_months = cust.customer_type.periodic_review_months if cust.customer_type else 12
        risk_adj = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: -3,
                    RiskLevel.HIGH: -6, RiskLevel.VERY_HIGH: -9}
        months = max(3, base_months + risk_adj.get(risk_level, 0))
        start = cust.approved_date or REFERENCE_DATE
        yr = start.year + (start.month + months - 1) // 12
        mo = (start.month + months - 1) % 12 + 1
        cust.next_review_date = date(yr, mo, min(start.day, 28))


# ---------------------------------------------------------------------------
# Main generator function
# ---------------------------------------------------------------------------

def run_generator(mode: str = "full", seed: int = SEED) -> Dict:
    """
    Main entry point.
    mode: 'full' or 'starter'
    Returns summary dict with record counts.
    """
    random.seed(seed)
    Faker.seed(seed)

    # Dataset sizes
    if mode == "starter":
        num_customers = 100
        num_documents = 300
        num_reviews = 50
        num_business_entities = 12
    else:
        num_customers = 8000
        num_documents = 20000
        num_reviews = 3000
        num_business_entities = 1000

    print(f"\n{'='*60}")
    print(f"YottaFlex KYC Data Generator — mode={mode}, seed={seed}")
    print(f"{'='*60}")

    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Clear existing data (order matters for FK constraints)
        print("Clearing existing data...")
        for tbl in [
            "audit_events", "alerts", "customer_document_requirements",
            "verifications", "documents", "review_cases", "risk_ratings",
            "beneficial_owners", "kyc_requirements", "customers", "customer_types",
        ]:
            db.execute(text(f'DELETE FROM {tbl}'))
        db.commit()

        print("Step 1: Seeding customer types...")
        customer_types = seed_customer_types(db)
        db.commit()

        print("Step 2: Seeding KYC requirements...")
        all_reqs = seed_kyc_requirements(db, customer_types)
        db.commit()

        print(f"Step 3: Generating {num_customers} customers...")
        customers = generate_customers(
            db, customer_types, num_customers,
            target_business_entities=num_business_entities,
        )
        db.commit()

        print(f"Step 4: Generating risk ratings...")
        risk_ratings = generate_risk_ratings(db, customers)
        db.commit()

        print(f"Step 5: Populating next review dates...")
        populate_review_dates(customers, risk_ratings)
        db.commit()

        print(f"Step 6: Generating beneficial owners...")
        bos = generate_beneficial_owners(db, customers)
        db.commit()

        print(f"Step 7: Generating {num_documents} documents...")
        documents, _ = generate_documents(db, customers, all_reqs, num_documents)
        db.commit()

        print(f"Step 8: Generating verifications...")
        verifications = generate_verifications(db, documents, customers)
        db.commit()

        print(f"Step 9: Updating KYC completeness...")
        update_kyc_completeness(db, customers, all_reqs, documents)
        db.commit()

        print(f"Step 10: Generating {num_reviews} review cases...")
        reviews = generate_review_cases(db, customers, num_reviews)
        db.commit()

        print(f"Step 11: Generating alerts...")
        alerts = generate_alerts(db, customers, documents, reviews)
        db.commit()

        print(f"Step 12: Generating audit events...")
        audit_events = generate_audit_events(db, customers, documents, reviews)
        db.commit()

        print(f"Step 13: Injecting anomalies...")
        bo_map: Dict[int, List[BeneficialOwner]] = {}
        for bo in bos:
            bo_map.setdefault(bo.business_customer_id, []).append(bo)

        anomaly_result = inject_anomalies(
            db, customers, documents, reviews, bo_map,
            alert_seq_start=len(alerts) + 1,
            audit_seq_start=len(audit_events) + 1,
        )

        # SQLAlchemy onupdate defaults use wall-clock time; normalize generated
        # update timestamps to the fixed dataset reference date for reproducibility.
        for model in (
            Customer, Document, ReviewCase, BeneficialOwner, Alert,
            CustomerDocumentRequirement,
        ):
            for record in db.query(model).all():
                if hasattr(record, "updated_at"):
                    record.updated_at = REFERENCE_DATETIME

        db.commit()

        summary = {
            "mode": mode,
            "seed": seed,
            "customer_types": len(CUSTOMER_TYPE_SPECS),
            "kyc_requirements": len(all_reqs),
            "customers": len(customers),
            "risk_ratings": len(risk_ratings),
            "beneficial_owners": len(bos),
            "documents": len(documents),
            "verifications": len(verifications),
            "review_cases": len(reviews),
            "alerts": len(alerts),
            "audit_events": len(audit_events),
            "anomalies": len(anomaly_result["anomalies"]),
            "ground_truth": anomaly_result["anomalies"],
        }

        print(f"\n{'='*60}")
        print("Generation complete! Summary:")
        for k, v in summary.items():
            if k != "ground_truth":
                print(f"  {k:30s}: {v}")
        print(f"{'='*60}\n")

        return summary

    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="YottaFlex KYC Data Generator")
    parser.add_argument("--mode", choices=["starter", "full"], default="full")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    result = run_generator(mode=args.mode, seed=args.seed)

    # Export the operational dataset and the separate ground-truth sidecar.
    from data_generator.exporter import run_all_exports
    export_db = SessionLocal()
    try:
        run_all_exports(
            export_db,
            ground_truth=result.get("ground_truth", []),
            run_id="run1",
        )
    finally:
        export_db.close()

    print(json.dumps(result, indent=2, default=str))
