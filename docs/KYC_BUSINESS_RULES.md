# YottaFlex KYC – Business Rules Documentation

## 1. Customer-Type-Specific Requirements

| Customer Type | Required Documents | Requires Beneficial Owner | Review Cycle |
|---|---|---|---|
| INDIVIDUAL | Passport (or NID), Utility Bill | No | 24 months |
| SOLE_TRADER | Passport, Utility Bill, Business Licence | No | 18 months |
| PARTNERSHIP | Passport, Partnership Deed, BO Declaration, Audited Financials | Yes (≥25% threshold) | 12 months |
| PRIVATE_COMPANY | Certificate of Incorporation, Articles of Association, Register of Members, BO Declaration, Audited Financials, Passport | Yes | 12 months |
| PUBLIC_COMPANY | Certificate of Incorporation, Company Search Report, Audited Financials, Sanctions Screening | Yes | 12 months |
| TRUST | Trust Deed, Passport, BO Declaration, AML Policy | Yes | 12 months |
| NON_PROFIT | Certificate of Incorporation, AML Policy, Audited Financials | Yes | 18 months |

## 2. Document Validity Rules

- A document is **valid** if:
  - `document_status = VERIFIED`
  - `expiry_date IS NULL OR expiry_date >= reference_date`
- Documents are assessed as of the **reference date** (2026-10-22 for the seed dataset)
- Address documents (Utility Bills, Bank Statements) have a maximum age of **3 months**
- Identity documents have a maximum age of **10 years** from issue
- Financial statements must be no more than **12 months** old

## 3. KYC Completeness Calculation

```
kyc_completeness_pct = (count of fulfilled MANDATORY requirements /
                        total MANDATORY requirements for customer type) × 100
```

- Only **MANDATORY** requirements are counted
- A requirement is fulfilled when a **VERIFIED** document of the required type exists for the customer
- CONDITIONAL and OPTIONAL requirements do not affect the completeness score
- Completeness is recalculated after each document verification

## 4. Risk-Based Requirements

### Risk Level Assignment

| Condition | Assigned Risk Level |
|---|---|
| PEP (Politically Exposed Person) | HIGH |
| Sanctioned | VERY_HIGH |
| Resident in high-risk country | HIGH or VERY_HIGH |
| Standard customer | LOW (50%), MEDIUM (30%), HIGH (15%), VERY_HIGH (5%) |

### Risk-Based Review Frequency

Base review cycle from customer type, adjusted by risk:

| Risk Level | Adjustment |
|---|---|
| LOW | +0 months (no change) |
| MEDIUM | −3 months |
| HIGH | −6 months |
| VERY_HIGH | −9 months |
| Minimum | 3 months |

**Example:** PRIVATE_COMPANY (12 months base) + HIGH risk = 6-month review cycle.

## 5. Beneficial Ownership Rules

- Required for: PARTNERSHIP, PRIVATE_COMPANY, PUBLIC_COMPANY, TRUST, NON_PROFIT
- Minimum ownership threshold for disclosure: **25%**
- Sum of all active beneficial owners' ownership percentages:
  - **Should not exceed 100%** (exceeding is anomaly 3)
  - Should not be less than 25% per disclosed owner if they meet the threshold
- Each beneficial owner must have identity documents verified

## 6. Verification Decisions

| Decision | Meaning |
|---|---|
| PASS | Document accepted; moves to VERIFIED |
| FAIL | Document rejected; moves to REJECTED |
| REFER | Escalated for further review |
| PENDING | Awaiting assessment |

- **Name mismatch:** If the name on the document does not match the customer's full_name, `name_match = FALSE` and the verification is flagged
- **Override:** A verifier may override a FAIL decision; `override_flag = TRUE` and `override_reason` must be recorded

## 7. Onboarding Decision Logic

A customer can only be approved when ALL of the following are true:

1. `kyc_completeness_pct = 100.00`
2. All mandatory documents are VERIFIED and not expired
3. For business customers: at least one beneficial owner is recorded
4. For business customers: total ownership_percentage ≤ 100%
5. No CRITICAL unresolved alerts

If any condition fails, the decision is **REFER** with reasons listed.

## 8. Periodic Review Scheduling

After approval, `next_review_date` is calculated as:

```
next_review_date = approved_date + adjusted_review_months
```

Reviews are triggered by:
- **PERIODIC** — scheduled based on `next_review_date`
- **RISK_CHANGE** — when risk rating changes from LOW/MEDIUM to HIGH/VERY_HIGH
- **DOCUMENT_EXPIRY** — when a mandatory document expires
- **ALERT** — when a CRITICAL alert is raised
- **MANUAL** — analyst-initiated

## 9. Alert Generation Rules

| Trigger | Alert Type | Severity |
|---|---|---|
| Document expires in ≤ 30 days | DOCUMENT_EXPIRING | MEDIUM |
| Document expiry_date < today | DOCUMENT_EXPIRED | HIGH |
| Review case due_date < today and not closed | REVIEW_OVERDUE | HIGH |
| Approved customer with KYC < 100% | KYC_INCOMPLETE | CRITICAL |
| BO ownership sum > 100% | OWNERSHIP_MISMATCH | CRITICAL |
| Verification name_match = FALSE | NAME_MISMATCH | MEDIUM |
| Same document_number for two customers | DUPLICATE_DOCUMENT | CRITICAL |

## 10. Audit Trail Rules

Every important state change produces an **immutable** AuditEvent:

| Event | Trigger |
|---|---|
| CREATE | Record created |
| APPROVE | Customer onboarding approved |
| REJECT | Customer or document rejected |
| VERIFY | Document verification recorded |
| REVIEW_OPEN | Review case opened |
| REVIEW_CLOSE | Review case closed |
| ALERT_RAISED | Alert generated |
| STATUS_CHANGE | Any status field changed |

- Audit records are **append-only** — never updated or deleted
- `old_value` and `new_value` store JSON snapshots of changed fields
- `performed_by` records the officer or system that made the change

## 11. Negative / Exception Scenarios

| Scenario | Label | Detection Method |
|---|---|---|
| Expired document marked VERIFIED | EXPIRED_BUT_MARKED_VALID | expiry_date < today AND document_status = 'VERIFIED' |
| Approved with missing evidence | APPROVED_WITH_MISSING_EVIDENCE | onboarding_status = 'APPROVED' AND kyc_completeness_pct < 100 |
| Ownership sum > 100% | OWNERSHIP_EXCEEDS_100 | GROUP BY customer SUM(ownership_percentage) > 100 |
| Review closed without resolution | REVIEW_CLOSED_WITHOUT_RESOLUTION | closed_without_resolution = TRUE AND resolution IS NULL |
| Duplicate document number | DUPLICATE_DOCUMENT_CROSS_CUSTOMER | Same document_number for different customer_id |
| Name mismatch | NAME_MISMATCH | verification.name_match = FALSE |
| Overdue review | REVIEW_OVERDUE | due_date < today AND status NOT IN (CLOSED_*) |
| Missing ownership records | MISSING_OWNERSHIP | business customer with requires_beneficial_owner = TRUE and 0 BO records |
