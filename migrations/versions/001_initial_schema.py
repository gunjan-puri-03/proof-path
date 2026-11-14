"""Initial migration — create all KYC tables.

Revision ID: 001_initial
Revises:
Create Date: 2026-11-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # customer_types
    op.create_table(
        'customer_types',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('requires_beneficial_owner', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('min_beneficial_owner_pct', sa.Numeric(5, 2), server_default='25.00'),
        sa.Column('periodic_review_months', sa.Integer(), nullable=False, server_default='12'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # customers
    op.create_table(
        'customers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('customer_id', sa.String(20), nullable=False, unique=True),
        sa.Column('full_name', sa.String(200), nullable=False),
        sa.Column('date_of_birth', sa.Date()),
        sa.Column('nationality', sa.String(100)),
        sa.Column('country_of_residence', sa.String(100), nullable=False),
        sa.Column('email', sa.String(200)),
        sa.Column('phone', sa.String(50)),
        sa.Column('address_line1', sa.String(200)),
        sa.Column('address_line2', sa.String(200)),
        sa.Column('city', sa.String(100)),
        sa.Column('state_province', sa.String(100)),
        sa.Column('postal_code', sa.String(20)),
        sa.Column('country', sa.String(100)),
        sa.Column('customer_type_id', sa.Integer(), sa.ForeignKey('customer_types.id'), nullable=False),
        sa.Column('onboarding_status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('business_registration_number', sa.String(100)),
        sa.Column('business_name', sa.String(200)),
        sa.Column('incorporation_date', sa.Date()),
        sa.Column('incorporation_country', sa.String(100)),
        sa.Column('kyc_completeness_pct', sa.Numeric(5, 2), server_default='0.00'),
        sa.Column('is_pep', sa.Boolean(), server_default='false'),
        sa.Column('is_sanctioned', sa.Boolean(), server_default='false'),
        sa.Column('source_of_funds', sa.String(200)),
        sa.Column('onboarding_date', sa.Date()),
        sa.Column('approved_date', sa.Date()),
        sa.Column('next_review_date', sa.Date()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_customers_customer_id', 'customers', ['customer_id'])
    op.create_index('ix_customers_onboarding_status', 'customers', ['onboarding_status'])
    op.create_index('ix_customers_next_review_date', 'customers', ['next_review_date'])

    # kyc_requirements
    op.create_table(
        'kyc_requirements',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('requirement_id', sa.String(25), nullable=False, unique=True),
        sa.Column('customer_type_id', sa.Integer(), sa.ForeignKey('customer_types.id'), nullable=False),
        sa.Column('document_category', sa.String(20), nullable=False),
        sa.Column('document_type', sa.String(100), nullable=False),
        sa.Column('requirement_type', sa.String(20), nullable=False, server_default='MANDATORY'),
        sa.Column('risk_level_applicable', sa.String(20)),
        sa.Column('description', sa.Text()),
        sa.Column('max_age_months', sa.Integer()),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # risk_ratings
    op.create_table(
        'risk_ratings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('risk_rating_id', sa.String(25), nullable=False, unique=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('risk_level', sa.String(20), nullable=False),
        sa.Column('risk_score', sa.Numeric(5, 2)),
        sa.Column('assessed_by', sa.String(100)),
        sa.Column('assessed_at', sa.DateTime(), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date()),
        sa.Column('rationale', sa.Text()),
        sa.Column('pep_flag', sa.Boolean(), server_default='false'),
        sa.Column('sanctions_flag', sa.Boolean(), server_default='false'),
        sa.Column('geographic_risk', sa.String(50)),
        sa.Column('industry_risk', sa.String(50)),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_risk_ratings_customer_id', 'risk_ratings', ['customer_id'])

    # beneficial_owners
    op.create_table(
        'beneficial_owners',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('bo_id', sa.String(25), nullable=False, unique=True),
        sa.Column('business_customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('individual_customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('full_name', sa.String(200), nullable=False),
        sa.Column('date_of_birth', sa.Date()),
        sa.Column('nationality', sa.String(100)),
        sa.Column('country_of_residence', sa.String(100)),
        sa.Column('ownership_percentage', sa.Numeric(5, 2), nullable=False),
        sa.Column('control_type', sa.String(100)),
        sa.Column('is_pep', sa.Boolean(), server_default='false'),
        sa.Column('is_sanctioned', sa.Boolean(), server_default='false'),
        sa.Column('is_verified', sa.Boolean(), server_default='false'),
        sa.Column('verification_date', sa.Date()),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.CheckConstraint('ownership_percentage >= 0 AND ownership_percentage <= 100',
                           name='ck_bo_ownership_pct_range'),
    )
    op.create_index('ix_bo_business_customer_id', 'beneficial_owners', ['business_customer_id'])

    # documents
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('document_id', sa.String(30), nullable=False, unique=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('document_category', sa.String(20), nullable=False),
        sa.Column('document_type', sa.String(100), nullable=False),
        sa.Column('document_number', sa.String(100)),
        sa.Column('issuing_authority', sa.String(200)),
        sa.Column('issuing_country', sa.String(100)),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('expiry_date', sa.Date()),
        sa.Column('document_status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('file_reference', sa.String(500)),
        sa.Column('notes', sa.Text()),
        sa.Column('is_mandatory', sa.Boolean(), server_default='true'),
        sa.Column('is_duplicate_suspect', sa.Boolean(), server_default='false'),
        sa.Column('duplicate_of_document_id', sa.String(30)),
        sa.Column('submitted_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_documents_customer_id', 'documents', ['customer_id'])
    op.create_index('ix_documents_document_status', 'documents', ['document_status'])
    op.create_index('ix_documents_expiry_date', 'documents', ['expiry_date'])
    op.create_index('ix_documents_document_number', 'documents', ['document_number'])

    # verifications
    op.create_table(
        'verifications',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('verification_id', sa.String(35), nullable=False, unique=True),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('verified_by', sa.String(100), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=False),
        sa.Column('decision', sa.String(20), nullable=False),
        sa.Column('decision_reason', sa.Text()),
        sa.Column('name_match', sa.Boolean()),
        sa.Column('name_on_document', sa.String(200)),
        sa.Column('expiry_check_passed', sa.Boolean()),
        sa.Column('authenticity_check_passed', sa.Boolean()),
        sa.Column('override_flag', sa.Boolean(), server_default='false'),
        sa.Column('override_reason', sa.Text()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_verifications_document_id', 'verifications', ['document_id'])
    op.create_index('ix_verifications_decision', 'verifications', ['decision'])

    # review_cases
    op.create_table(
        'review_cases',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('review_id', sa.String(25), nullable=False, unique=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('trigger', sa.String(20), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='OPEN'),
        sa.Column('opened_at', sa.DateTime(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('closed_at', sa.DateTime()),
        sa.Column('assigned_to', sa.String(100)),
        sa.Column('findings', sa.Text()),
        sa.Column('resolution', sa.Text()),
        sa.Column('closed_without_resolution', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_review_cases_customer_id', 'review_cases', ['customer_id'])
    op.create_index('ix_review_cases_status', 'review_cases', ['status'])
    op.create_index('ix_review_cases_due_date', 'review_cases', ['due_date'])

    # alerts
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('alert_id', sa.String(20), nullable=False, unique=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('review_case_id', sa.Integer(), sa.ForeignKey('review_cases.id'), nullable=True),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('documents.id'), nullable=True),
        sa.Column('alert_type', sa.String(30), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='OPEN'),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('triggered_at', sa.DateTime(), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime()),
        sa.Column('resolved_at', sa.DateTime()),
        sa.Column('resolved_by', sa.String(100)),
        sa.Column('resolution_notes', sa.Text()),
        sa.Column('is_anomaly', sa.Boolean(), server_default='false'),
        sa.Column('anomaly_label', sa.String(100)),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_alerts_customer_id', 'alerts', ['customer_id'])
    op.create_index('ix_alerts_alert_type', 'alerts', ['alert_type'])
    op.create_index('ix_alerts_status', 'alerts', ['status'])

    # audit_events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('audit_id', sa.String(20), nullable=False, unique=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(50), nullable=False),
        sa.Column('action', sa.String(30), nullable=False),
        sa.Column('performed_by', sa.String(100), nullable=False),
        sa.Column('performed_at', sa.DateTime(), nullable=False),
        sa.Column('old_value', sa.Text()),
        sa.Column('new_value', sa.Text()),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('session_id', sa.String(100)),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_audit_events_customer_id', 'audit_events', ['customer_id'])
    op.create_index('ix_audit_events_entity_type', 'audit_events', ['entity_type'])
    op.create_index('ix_audit_events_performed_at', 'audit_events', ['performed_at'])

    # customer_document_requirements (bridge)
    op.create_table(
        'customer_document_requirements',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('requirement_id', sa.Integer(), sa.ForeignKey('kyc_requirements.id'), nullable=False),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('documents.id'), nullable=True),
        sa.Column('is_fulfilled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('fulfilled_at', sa.DateTime()),
        sa.Column('waived', sa.Boolean(), server_default='false'),
        sa.Column('waiver_reason', sa.Text()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('customer_id', 'requirement_id', name='uq_customer_requirement'),
    )
    op.create_index('ix_cdr_customer_id', 'customer_document_requirements', ['customer_id'])


def downgrade() -> None:
    op.drop_table('customer_document_requirements')
    op.drop_table('audit_events')
    op.drop_table('alerts')
    op.drop_table('review_cases')
    op.drop_table('verifications')
    op.drop_table('documents')
    op.drop_table('beneficial_owners')
    op.drop_table('risk_ratings')
    op.drop_table('kyc_requirements')
    op.drop_table('customers')
    op.drop_table('customer_types')
