
import { useCallback, useEffect, useMemo, useState } from 'react'
import './App.css'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

const ENDPOINTS = {
  customers: '/api/v1/customers/?skip=0&limit=500',
  documents: '/api/v1/documents/?skip=0&limit=500',
  reviews: '/api/v1/reviews/?skip=0&limit=500',
  alerts: '/api/v1/alerts/?skip=0&limit=500',
  verifications: '/api/v1/verifications/?skip=0&limit=500',
  risk_monitoring: '/api/v1/risk-monitoring/?skip=0&limit=500',
  audit_logs: '/api/v1/audit-logs/?skip=0&limit=1000',
}

const navigation = [
  {
    section: 'WORKSPACE',
    items: [
      ['▦', 'Dashboard'],
      ['♙', 'Customers'],
      ['▤', 'Documents'],
      ['✓', 'Verifications'],
      ['◷', 'Reviews'],
    ],
  },
  {
    section: 'RISK & COMPLIANCE',
    items: [
      ['⚠', 'Alerts'],
      ['◎', 'Risk Monitoring'],
      ['▧', 'Audit Logs'],
    ],
  },
]

const PAGE_KEYS = {
  Customers: 'customers',
  Documents: 'documents',
  Verifications: 'verifications',
  Reviews: 'reviews',
  Alerts: 'alerts',
  'Risk Monitoring': 'risk_monitoring',
  'Audit Logs': 'audit_logs',
}

async function fetchList(endpoint, signal) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    signal,
    headers: { Accept: 'application/json' },
  })

  if (!response.ok) {
    let message = `HTTP ${response.status}`

    try {
      const error = await response.json()
      message = error.detail || error.message || message
    } catch {
      // Keep the default HTTP error.
    }

    throw new Error(message)
  }

  const result = await response.json()

  if (Array.isArray(result)) return result
  if (Array.isArray(result.items)) return result.items
  if (Array.isArray(result.results)) return result.results

  throw new Error('Unexpected API response format')
}

function formatStatus(value) {
  if (value === null || value === undefined || value === '') {
    return 'Unknown'
  }

  return String(value)
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(/\b\w/g, letter => letter.toUpperCase())
}

function formatDate(value, includeTime = false) {
  if (!value) return '—'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return value

  return includeTime
    ? date.toLocaleString()
    : date.toLocaleDateString()
}

function StatusBadge({ value, type = 'status' }) {
  const normalized = String(value || 'unknown')
    .toLowerCase()
    .replaceAll('_', '-')
    .replaceAll(' ', '-')

  return (
    <span className={`${type} ${normalized}`}>
      {formatStatus(value)}
    </span>
  )
}

function BooleanValue({
  value,
  trueLabel = 'Yes',
  falseLabel = 'No',
}) {
  if (value === null || value === undefined) return '—'

  return value ? trueLabel : falseLabel
}

// Format audit event snapshots.
function formatAuditValue(value) {
  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return 'Not recorded'
  }

  if (typeof value === 'string') {
    try {
      return JSON.stringify(JSON.parse(value), null, 2)
    } catch {
      return value
    }
  }

  return JSON.stringify(value, null, 2)
}

function App() {
  const [activePage, setActivePage] = useState('Dashboard')
  const [selectedAuditEvent, setSelectedAuditEvent] = useState(null)
  const [search, setSearch] = useState('')

  const [riskLevelFilter, setRiskLevelFilter] = useState('ALL')

  // Audit Logs filters and sorting.
  const [auditActionFilter, setAuditActionFilter] = useState('ALL')
  const [auditEntityFilter, setAuditEntityFilter] = useState('ALL')
  const [auditSort, setAuditSort] = useState('desc')

  const [data, setData] = useState({
    customers: [],
    documents: [],
    reviews: [],
    alerts: [],
    verifications: [],
    risk_monitoring: [],
    audit_logs: [],
  })

  const [loading, setLoading] = useState(true)
  const [errors, setErrors] = useState({})
  const [lastUpdated, setLastUpdated] = useState(null)

  // --------------------------------------------------
  // LOAD BACKEND DATA
  // --------------------------------------------------

  const loadData = useCallback(async (signal) => {
    setLoading(true)

    const entries = Object.entries(ENDPOINTS)

    const results = await Promise.allSettled(
      entries.map(async ([key, endpoint]) => ({
        key,
        rows: await fetchList(endpoint, signal),
      }))
    )

    if (signal?.aborted) return

    const nextErrors = {}
    const updates = {}

    results.forEach((result, index) => {
      const key = entries[index][0]

      if (result.status === 'fulfilled') {
        updates[key] = result.value.rows
      } else {
        nextErrors[key] =
          result.reason?.message || 'Unable to load data'
      }
    })

    setData(previous => ({
      ...previous,
      ...updates,
    }))

    setErrors(nextErrors)
    setLastUpdated(new Date())
    setLoading(false)
  }, [])

  // Initial API loading.
  useEffect(() => {
    const controller = new AbortController()

    loadData(controller.signal)

    return () => controller.abort()
  }, [loadData])

  // Set browser tab title.
  useEffect(() => {
    document.title = 'ProofPath | KYC & Compliance'
  }, [])
  // Close audit details using the Escape key.
  useEffect(() => {
    if (!selectedAuditEvent) return

    const handleKeyDown = event => {
      if (event.key === 'Escape') {
        setSelectedAuditEvent(null)
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [selectedAuditEvent])

  // --------------------------------------------------
  // BACKEND RECORDS
  // --------------------------------------------------

  const customers = data.customers
  const documents = data.documents
  const reviews = data.reviews
  const alerts = data.alerts
  const verifications = data.verifications
  const riskMonitoring = data.risk_monitoring
  const auditLogs = data.audit_logs

  // --------------------------------------------------
  // DASHBOARD STATISTICS
  // --------------------------------------------------

  const approvedCount = customers.filter(
    customer => customer.onboarding_status === 'APPROVED'
  ).length

  const awaitingCount = customers.filter(
    customer =>
      ['PENDING', 'IN_PROGRESS'].includes(
        customer.onboarding_status
      )
  ).length

  const rejectedCount = customers.filter(
    customer => customer.onboarding_status === 'REJECTED'
  ).length

  const suspendedCount = customers.filter(
    customer => customer.onboarding_status === 'SUSPENDED'
  ).length

  const averageKyc = customers.length
    ? Math.round(
        customers.reduce(
          (total, customer) =>
            total + Number(customer.kyc_completeness_pct || 0),
          0
        ) / customers.length
      )
    : 0

  // Risk statistics.
  const highRiskCount = riskMonitoring.filter(
    item =>
      ['HIGH', 'VERY_HIGH', 'CRITICAL'].includes(
        String(item.risk_level || '').toUpperCase()
      )
  ).length

  const lowRiskCount = riskMonitoring.filter(
    item =>
      String(item.risk_level || '').toUpperCase() === 'LOW'
  ).length

  const mediumRiskCount = riskMonitoring.filter(
    item =>
      String(item.risk_level || '').toUpperCase() === 'MEDIUM'
  ).length

  // --------------------------------------------------
  // SELECT RECORDS FOR ACTIVE PAGE
  // --------------------------------------------------

  const selectedRows = useMemo(() => {
    const rowsByPage = {
      Customers: data.customers,
      Documents: data.documents,
      Verifications: data.verifications,
      Reviews: data.reviews,
      Alerts: data.alerts,
      'Risk Monitoring': data.risk_monitoring,
      'Audit Logs': data.audit_logs,
    }

    return rowsByPage[activePage] || []
  }, [activePage, data])

  // --------------------------------------------------
  // SEARCH AND FILTER
  // --------------------------------------------------

  const filteredRows = useMemo(() => {
    return selectedRows.filter(row => {
      const matchesSearch = JSON.stringify(row)
        .toLowerCase()
        .includes(search.toLowerCase())

      const matchesRiskLevel =
        activePage !== 'Risk Monitoring' ||
        riskLevelFilter === 'ALL' ||
        String(row.risk_level || '').toUpperCase() ===
          riskLevelFilter

      const matchesAuditAction =
        activePage !== 'Audit Logs' ||
        auditActionFilter === 'ALL' ||
        String(row.action || '').toUpperCase() ===
          auditActionFilter

      const matchesAuditEntity =
        activePage !== 'Audit Logs' ||
        auditEntityFilter === 'ALL' ||
        String(row.entity_type || '') === auditEntityFilter

      return (
        matchesSearch &&
        matchesRiskLevel &&
        matchesAuditAction &&
        matchesAuditEntity
      )
    })
  }, [
    selectedRows,
    search,
    activePage,
    riskLevelFilter,
    auditActionFilter,
    auditEntityFilter,
  ])

  // Audit Logs sorting.
  const displayedRows = useMemo(() => {
    if (activePage !== 'Audit Logs') {
      return filteredRows
    }

    return [...filteredRows].sort((a, b) => {
      const first = new Date(
        a.performed_at || a.created_at || 0
      ).getTime()

      const second = new Date(
        b.performed_at || b.created_at || 0
      ).getTime()

      const safeFirst = Number.isNaN(first) ? 0 : first
      const safeSecond = Number.isNaN(second) ? 0 : second

      return auditSort === 'asc'
        ? safeFirst - safeSecond
        : safeSecond - safeFirst
    })
  }, [filteredRows, activePage, auditSort])

  // Search customers independently for the dashboard.
  const filteredCustomers = customers.filter(customer =>
    `${customer.full_name || ''} ${customer.customer_id || ''}`
      .toLowerCase()
      .includes(search.toLowerCase())
  )

  // --------------------------------------------------
  // DASHBOARD CARDS
  // --------------------------------------------------

  const stats = [
    {
      label: 'Total Customers',
      value: customers.length,
      icon: '👥',
      change: 'Live customer records',
    },
    {
      label: 'Total Documents',
      value: documents.length,
      icon: '📄',
      change: 'Document records',
    },
    {
      label: 'Verifications',
      value: verifications.length,
      icon: '✓',
      change: 'Verification records',
    },
    {
      label: 'Total Alerts',
      value: alerts.length,
      icon: '⚠️',
      change: 'Alert records',
    },
  ]

  // Audit summary values are calculated from records returned by
  // the Audit Logs endpoint.
  const auditActionCount = new Set(
    auditLogs.map(event => event.action).filter(Boolean)
  ).size

  const auditEntityCount = new Set(
    auditLogs.map(event => event.entity_type).filter(Boolean)
  ).size

  const auditUserCount = new Set(
    auditLogs.map(event => event.performed_by).filter(Boolean)
  ).size

  // --------------------------------------------------
  // PAGE NAVIGATION
  // --------------------------------------------------

  function navigateTo(page) {
    setActivePage(page)
    setSearch('')
    setRiskLevelFilter('ALL')
    setAuditActionFilter('ALL')
    setAuditEntityFilter('ALL')
    setAuditSort('desc')
  }

  const isDataPage = Object.keys(PAGE_KEYS).includes(activePage)

  const activePageKey = PAGE_KEYS[activePage]

  const activePageError = activePageKey
    ? errors[activePageKey]
    : null

  // --------------------------------------------------
  // TABLE RENDERING
  // --------------------------------------------------

  function renderTable() {
    if (loading && selectedRows.length === 0) {
      return (
        <p className="table-message">
          Loading records from backend...
        </p>
      )
    }

    if (activePageError && selectedRows.length === 0) {
      return (
        <p className="table-message">
          Unable to load {activePage}: {activePageError}
        </p>
      )
    }

    if (displayedRows.length === 0) {
      return (
        <p className="table-message">
          No matching records found.
        </p>
      )
    }

    // CUSTOMERS TABLE
    if (activePage === 'Customers') {
      return (
        <table>
          <thead>
            <tr>
              <th>CUSTOMER</th>
              <th>TYPE</th>
              <th>STATUS</th>
              <th>KYC COMPLETE</th>
              <th>COUNTRY</th>
            </tr>
          </thead>

          <tbody>
            {displayedRows.map(customer => (
              <tr key={customer.customer_id}>
                <td>
                  <strong>{customer.full_name || '—'}</strong>
                  <small>{customer.customer_id}</small>
                </td>

                <td>{formatStatus(customer.customer_type)}</td>

                <td>
                  <StatusBadge value={customer.onboarding_status} />
                </td>

                <td>
                  {Number(
                    customer.kyc_completeness_pct || 0
                  ).toFixed(2)}%
                </td>

                <td>
                  {customer.country_of_residence || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )
    }

    // DOCUMENTS TABLE
    if (activePage === 'Documents') {
      return (
        <table>
          <thead>
            <tr>
              <th>DOCUMENT ID</th>
              <th>DOCUMENT TYPE</th>
              <th>STATUS</th>
              <th>ISSUE DATE</th>
              <th>EXPIRY DATE</th>
              <th>DUPLICATE</th>
            </tr>
          </thead>

          <tbody>
            {displayedRows.map(document => (
              <tr key={document.document_id}>
                <td>
                  <strong>{document.document_id}</strong>
                </td>

                <td>{formatStatus(document.document_type)}</td>

                <td>
                  <StatusBadge value={document.document_status} />
                </td>

                <td>{formatDate(document.issue_date)}</td>
                <td>{formatDate(document.expiry_date)}</td>

                <td>
                  <BooleanValue value={document.is_duplicate_suspect} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )
    }

    // VERIFICATIONS TABLE
    if (activePage === 'Verifications') {
      return (
        <table>
          <thead>
            <tr>
              <th>VERIFICATION ID</th>
              <th>DOCUMENT ID</th>
              <th>OFFICER</th>
              <th>DECISION</th>
              <th>NAME MATCH</th>
              <th>EXPIRY CHECK</th>
              <th>AUTHENTICITY</th>
              <th>VERIFIED DATE</th>
            </tr>
          </thead>

          <tbody>
            {displayedRows.map(verification => (
              <tr key={verification.verification_id}>
                <td>
                  <strong>
                    {verification.verification_id || '—'}
                  </strong>
                </td>

                <td>
                  {verification.document_number ||
                    verification.document?.document_id ||
                    verification.document_id ||
                    '—'}
                </td>

                <td>{verification.verified_by || '—'}</td>

                <td>
                  <StatusBadge value={verification.decision} />
                </td>

                <td>
                  <BooleanValue value={verification.name_match} />
                </td>

                <td>
                  <BooleanValue
                    value={verification.expiry_check_passed}
                    trueLabel="Passed"
                    falseLabel="Failed"
                  />
                </td>

                <td>
                  <BooleanValue
                    value={verification.authenticity_check_passed}
                    trueLabel="Passed"
                    falseLabel="Failed"
                  />
                </td>

                <td>{formatDate(verification.verified_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )
    }

    // REVIEWS TABLE
    if (activePage === 'Reviews') {
      return (
        <table>
          <thead>
            <tr>
              <th>REVIEW ID</th>
              <th>TRIGGER</th>
              <th>STATUS</th>
              <th>OPENED</th>
              <th>DUE DATE</th>
              <th>UNRESOLVED</th>
            </tr>
          </thead>

          <tbody>
            {displayedRows.map(review => (
              <tr key={review.review_id}>
                <td>
                  <strong>{review.review_id}</strong>
                </td>

                <td>{formatStatus(review.trigger)}</td>

                <td>
                  <StatusBadge value={review.status} />
                </td>

                <td>{formatDate(review.opened_at)}</td>
                <td>{formatDate(review.due_date)}</td>

                <td>
                  <BooleanValue
                    value={review.closed_without_resolution}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )
    }

    // ALERTS TABLE
    if (activePage === 'Alerts') {
      return (
        <table>
          <thead>
            <tr>
              <th>ALERT</th>
              <th>TYPE</th>
              <th>SEVERITY</th>
              <th>STATUS</th>
              <th>ANOMALY</th>
            </tr>
          </thead>

          <tbody>
            {displayedRows.map(alert => (
              <tr key={alert.alert_id}>
                <td>
                  <strong>{alert.title || '—'}</strong>
                  <small>{alert.alert_id}</small>
                </td>

                <td>{formatStatus(alert.alert_type)}</td>

                <td>
                  <StatusBadge
                    value={alert.severity}
                    type="severity"
                  />
                </td>

                <td>
                  <StatusBadge value={alert.status} />
                </td>

                <td>
                  {alert.is_anomaly
                    ? formatStatus(alert.anomaly_label)
                    : 'No'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )
    }

    // RISK MONITORING TABLE
    if (activePage === 'Risk Monitoring') {
      return (
        <table>
          <thead>
            <tr>
              <th>RISK RATING ID</th>
              <th>CUSTOMER</th>
              <th>RISK LEVEL</th>
              <th>RISK SCORE</th>
              <th>PEP</th>
              <th>SANCTIONS</th>
              <th>GEOGRAPHIC RISK</th>
              <th>INDUSTRY RISK</th>
              <th>ASSESSED BY</th>
              <th>LAST ASSESSED</th>
            </tr>
          </thead>

          <tbody>
            {displayedRows.map((rating, index) => (
              <tr
                key={
                  rating.risk_rating_id ||
                  rating.id ||
                  `${rating.customer_id}-${index}`
                }
              >
                <td>
                  <strong>
                    {rating.risk_rating_id ||
                      rating.rating_id ||
                      rating.id ||
                      '—'}
                  </strong>
                </td>

                <td>
                  <strong>
                    {rating.customer_name ||
                      rating.customer?.full_name ||
                      rating.full_name ||
                      '—'}
                  </strong>

                  <small>
                    {rating.customer_id ||
                      rating.customer?.customer_id ||
                      '—'}
                  </small>
                </td>

                <td>
                  <StatusBadge
                    value={rating.risk_level}
                    type="risk-level"
                  />
                </td>

                <td>
                  {rating.risk_score == null
                    ? '—'
                    : Number(rating.risk_score).toFixed(2)}
                </td>

                <td>
                  <BooleanValue
                    value={
                      rating.pep_flag ??
                      rating.customer_is_pep ??
                      rating.is_pep
                    }
                  />
                </td>

                <td>
                  <BooleanValue
                    value={
                      rating.sanctions_flag ??
                      rating.customer_is_sanctioned ??
                      rating.is_sanctioned
                    }
                  />
                </td>

                <td>
                  {rating.geographic_risk
                    ? formatStatus(rating.geographic_risk)
                    : '—'}
                </td>

                <td>
                  {rating.industry_risk
                    ? formatStatus(rating.industry_risk)
                    : '—'}
                </td>

                <td>{rating.assessed_by || '—'}</td>

                <td>
                  {formatDate(
                    rating.assessed_at ||
                    rating.last_assessed_at ||
                    rating.created_at
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )
    }

    // AUDIT LOGS TABLE
    if (activePage === 'Audit Logs') {
      return (
        <table className="audit-table">
          <thead>
            <tr>
              <th>AUDIT ID</th>
              <th>PERFORMED BY</th>
              <th>ACTION</th>
              <th>ENTITY TYPE</th>
              <th>ENTITY ID</th>
              <th>CUSTOMER</th>
              <th>IP ADDRESS</th>
              <th>DATE &amp; TIME</th>
              <th>NOTES</th>
            </tr>
          </thead>

          <tbody>
            {displayedRows.map(event => (
              <tr key={event.audit_id}>
                <td>
                  <button
                    type="button"
                    className="audit-id-button"
                    onClick={() => setSelectedAuditEvent(event)}
                  >
                    {event.audit_id || '—'}
                  </button>
                </td>

                <td>{event.performed_by || '—'}</td>

                <td>
                  <StatusBadge
                    value={event.action}
                    type="audit-action"
                  />
                </td>

                <td>{formatStatus(event.entity_type)}</td>

                <td>{event.entity_id || '—'}</td>

                <td>
                  <strong>{event.customer_name || '—'}</strong>
                  <small>{event.customer_id || ''}</small>
                </td>

                <td>{event.ip_address || '—'}</td>

                <td>
                  {formatDate(
                    event.performed_at || event.created_at,
                    true
                  )}
                </td>

                <td
                  className="audit-notes"
                  title={event.notes || ''}
                >
                  {event.notes || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )
    }

    return null
  }

  // --------------------------------------------------
  // MAIN UI
  // --------------------------------------------------

  return (
    <div className="app">

      {/* SIDEBAR */}

      <aside className="sidebar">

        <div className="brand">
          <div className="brand-icon">P</div>

          <div>
            <h2>ProofPath</h2>
            <span>KYC &amp; COMPLIANCE</span>
          </div>
        </div>

        <div className="nav-menu">

          {navigation.map(group => (
            <div className="nav-group" key={group.section}>

              <p className="nav-heading">
                {group.section}
              </p>

              {group.items.map(([icon, label]) => (
                <button
                  key={label}
                  className={`nav-item ${
                    activePage === label ? 'active' : ''
                  }`}
                  onClick={() => navigateTo(label)}
                >
                  <span>{icon}</span>
                  {label}
                </button>
              ))}

            </div>
          ))}

        </div>

        <div className="sidebar-bottom">

          <div className="profile">
            <div className="avatar">AD</div>

            <div>
              <strong>Admin User</strong>
              <span>Administrator</span>
            </div>
          </div>

        </div>

      </aside>

      {/* MAIN CONTENT */}

      <main className="main">

        {/* TOP BAR */}

        <header className="topbar">

          <div>
            <span className="breadcrumb">
              Workspace /
            </span>

            <strong>{activePage}</strong>
          </div>

          <div className="top-actions">

            <span className="system-status">
              <i />

              {Object.keys(errors).length
                ? 'API Partially Available'
                : loading
                  ? 'Connecting...'
                  : 'API Connected'}
            </span>

            <button
              className="notification"
              title="Refresh all data"
              onClick={() => loadData()}
            >
              ↻
            </button>

            <div className="avatar">AD</div>

          </div>

        </header>

        {/* PAGE CONTENT */}

        <div className="content">

          {/* PAGE HEADING */}

          <div className="welcome">

            <div>

              <p className="eyebrow">
                OVERVIEW
              </p>

              <h1>
                {activePage === 'Dashboard'
                  ? 'Good morning, Admin 👋'
                  : activePage}
              </h1>

              <p className="subtitle">
                {activePage === 'Dashboard'
                  ? 'Here is your live ProofPath KYC & Compliance overview.'
                  : `Manage and monitor your ${activePage.toLowerCase()} activity.`}
              </p>

            </div>

            <button
              className="primary-btn"
              onClick={() => navigateTo('Customers')}
            >
              + View Customers
            </button>

          </div>

          {/* DASHBOARD */}

          {activePage === 'Dashboard' && (
            <>

              <div className="stats-grid">

                {stats.map((stat, index) => (
                  <div className="stat-card" key={stat.label}>

                    <div className="stat-top">
                      <span>{stat.label}</span>

                      <span className={`stat-icon icon-${index}`}>
                        {stat.icon}
                      </span>
                    </div>

                    <h2>
                      {loading ? '—' : stat.value}
                    </h2>

                    <p>{stat.change}</p>

                  </div>
                ))}

              </div>

              <div className="section-grid">

                {/* RECENT CUSTOMERS */}

                <section className="panel customer-panel">

                  <div className="panel-header">

                    <div>
                      <h3>Recent Customers</h3>
                      <p>
                        Latest customer records from PostgreSQL
                      </p>
                    </div>

                    <button
                      className="text-btn"
                      onClick={() => navigateTo('Customers')}
                    >
                      View all →
                    </button>

                  </div>

                  <div className="search-box">
                    <span>⌕</span>

                    <input
                      placeholder="Search customers..."
                      value={search}
                      onChange={event =>
                        setSearch(event.target.value)
                      }
                    />
                  </div>

                  <div className="table-wrap">

                    {errors.customers ? (
                      <p className="table-message">
                        {errors.customers}
                      </p>
                    ) : (

                      <table>

                        <thead>
                          <tr>
                            <th>CUSTOMER</th>
                            <th>TYPE</th>
                            <th>STATUS</th>
                            <th>KYC COMPLETE</th>
                          </tr>
                        </thead>

                        <tbody>

                          {loading ? (
                            <tr>
                              <td colSpan="4">Loading...</td>
                            </tr>
                          ) : filteredCustomers.length > 0 ? (

                            filteredCustomers
                              .slice(0, 5)
                              .map(customer => (

                                <tr key={customer.customer_id}>

                                  <td>
                                    <strong>
                                      {customer.full_name || '—'}
                                    </strong>

                                    <small>
                                      {customer.customer_id}
                                    </small>
                                  </td>

                                  <td>
                                    {formatStatus(customer.customer_type)}
                                  </td>

                                  <td>
                                    <StatusBadge
                                      value={customer.onboarding_status}
                                    />
                                  </td>

                                  <td>
                                    {Number(
                                      customer.kyc_completeness_pct || 0
                                    ).toFixed(2)}%
                                  </td>

                                </tr>

                              ))

                          ) : (

                            <tr>
                              <td colSpan="4">
                                No customers found.
                              </td>
                            </tr>

                          )}

                        </tbody>

                      </table>

                    )}

                  </div>

                </section>

                {/* COMPLIANCE OVERVIEW */}

                <section className="panel activity-panel">

                  <div className="panel-header">

                    <div>
                      <h3>Compliance Overview</h3>
                      <p>
                        Live customer status distribution
                      </p>
                    </div>

                  </div>

                  {[
                    ['Approved Customers', approvedCount, '#5d57ce'],
                    ['Awaiting Action', awaitingCount, '#46a4e8'],
                    ['Rejected Customers', rejectedCount, '#e8a15d'],
                    ['Suspended Customers', suspendedCount, '#9a75d8'],
                    [
                      'Average KYC Completeness',
                      `${averageKyc}%`,
                      '#38a68a',
                    ],
                    [
                      'High / Very High Risk',
                      highRiskCount,
                      '#e16b6b',
                    ],
                  ].map(([label, value, color]) => {

                    const percentage =
                      label === 'Average KYC Completeness'
                        ? averageKyc
                        : label === 'High / Very High Risk'
                          ? riskMonitoring.length
                            ? (highRiskCount / riskMonitoring.length) * 100
                            : 0
                          : customers.length
                            ? (value / customers.length) * 100
                            : 0

                    return (

                      <div
                        className="compliance-item"
                        key={label}
                      >

                        <div>
                          <span>{label}</span>

                          <strong>
                            {loading ? '—' : value}
                          </strong>
                        </div>

                        <div className="progress">

                          <span
                            style={{
                              width: `${Math.min(100, percentage)}%`,
                              background: color,
                            }}
                          />

                        </div>

                      </div>

                    )
                  })}

                  <div className="info-box">
                    <span>ℹ</span>

                    <p>
                      Statistics are retrieved from your live
                      FastAPI and PostgreSQL backend.
                    </p>
                  </div>

                </section>

              </div>

            </>
          )}

          {/* LIVE DATA MODULES */}

          {isDataPage && (

            <section className="panel data-panel">

              <div className="panel-header">

                <div>
                  <h3>{activePage} Records</h3>

                  <p>
                    {loading
                      ? 'Loading records...'
                      : `${selectedRows.length} records retrieved from PostgreSQL`}
                  </p>
                </div>

                <button
                  className="text-btn"
                  onClick={() => loadData()}
                >
                  ↻ Refresh
                </button>

              </div>

              {/* RISK SUMMARY CARDS */}

              {activePage === 'Risk Monitoring' && (

                <div className="risk-summary-grid">

                  {[
                    ['Total Monitored', riskMonitoring.length, 'total'],
                    ['Low Risk', lowRiskCount, 'low'],
                    ['Medium Risk', mediumRiskCount, 'medium'],
                    ['High / Very High', highRiskCount, 'high'],
                  ].map(([label, value, tone]) => (

                    <div
                      className={`risk-summary-card ${tone}`}
                      key={label}
                    >
                      <span>{label}</span>
                      <strong>{loading ? '—' : value}</strong>
                    </div>

                  ))}

                </div>

              )}

              {/* AUDIT SUMMARY CARDS */}

              {activePage === 'Audit Logs' && (

                <div className="risk-summary-grid audit-summary-grid">

                  {[
                    ['Audit Events', auditLogs.length],
                    ['Action Types', auditActionCount],
                    ['Entity Types', auditEntityCount],
                    ['Users', auditUserCount],
                  ].map(([label, value]) => (

                    <div
                      className="risk-summary-card"
                      key={label}
                    >
                      <span>{label}</span>
                      <strong>{loading ? '—' : value}</strong>
                    </div>

                  ))}

                </div>

              )}

              {/* SEARCH */}

              <div className="search-box">

                <span>⌕</span>

                <input
                  placeholder={`Search ${activePage.toLowerCase()}...`}
                  value={search}
                  onChange={event =>
                    setSearch(event.target.value)
                  }
                />

              </div>

              {/* RISK LEVEL FILTER */}

              {activePage === 'Risk Monitoring' && (

                <div className="risk-filter">

                  <label htmlFor="risk-level-filter">
                    Filter by Risk Level:
                  </label>

                  <select
                    id="risk-level-filter"
                    value={riskLevelFilter}
                    onChange={event =>
                      setRiskLevelFilter(event.target.value)
                    }
                  >
                    <option value="ALL">All Risk Levels</option>
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="VERY_HIGH">Very High</option>
                    <option value="CRITICAL">Critical</option>
                  </select>

                </div>

              )}

              {/* AUDIT LOG FILTERS */}

              {activePage === 'Audit Logs' && (

                <div className="audit-filters">

                  <div>
                    <label htmlFor="audit-action-filter">
                      Action
                    </label>

                    <select
                      id="audit-action-filter"
                      value={auditActionFilter}
                      onChange={event =>
                        setAuditActionFilter(event.target.value)
                      }
                    >
                      <option value="ALL">All Actions</option>

                      {[
                        ...new Set(
                          auditLogs
                            .map(event => event.action)
                            .filter(Boolean)
                        ),
                      ].sort().map(action => (
                        <option value={action} key={action}>
                          {formatStatus(action)}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label htmlFor="audit-entity-filter">
                      Entity
                    </label>

                    <select
                      id="audit-entity-filter"
                      value={auditEntityFilter}
                      onChange={event =>
                        setAuditEntityFilter(event.target.value)
                      }
                    >
                      <option value="ALL">All Entities</option>

                      {[
                        ...new Set(
                          auditLogs
                            .map(event => event.entity_type)
                            .filter(Boolean)
                        ),
                      ].sort().map(entity => (
                        <option value={entity} key={entity}>
                          {formatStatus(entity)}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label htmlFor="audit-sort">
                      Date Sorting
                    </label>

                    <select
                      id="audit-sort"
                      value={auditSort}
                      onChange={event =>
                        setAuditSort(event.target.value)
                      }
                    >
                      <option value="desc">Newest First</option>
                      <option value="asc">Oldest First</option>
                    </select>
                  </div>

                </div>

              )}

              {/* API ERROR */}

              {activePageError && (

                <div className="api-message error">
                  {activePageError}
                </div>

              )}

              {/* DATA TABLE */}

              <div className="table-wrap">
                {renderTable()}
              </div>

              {/* TABLE FOOTER */}

              <p className="table-footer">

                Showing {displayedRows.length} of {selectedRows.length} records

                {lastUpdated && (
                  <span>
                    {' '}| Last refreshed: {lastUpdated.toLocaleTimeString()}
                  </span>
                )}

              </p>

            </section>

          )}

          {/* MODULES WITHOUT BACKEND ENDPOINTS */}

          {!isDataPage && activePage !== 'Dashboard' && (

            <section className="panel page-placeholder">

              <div className="placeholder-icon">
                ▦
              </div>

              <h2>{activePage}</h2>

              <p>
                This module does not currently have a dedicated
                backend endpoint in your project.
              </p>

              <button
                className="primary-btn"
                onClick={() => navigateTo('Dashboard')}
              >
                Return to Dashboard
              </button>

            </section>

          )}

          {/* FOOTER */}

          <footer>
            <span>© 2026 ProofPath KYC & Compliance Platform</span>
            <span>Secure Compliance Management</span>
          </footer>

        </div>

        {/* AUDIT EVENT DETAILS MODAL */}

        {selectedAuditEvent && (
          <div
            className="audit-modal-backdrop"
            onClick={() => setSelectedAuditEvent(null)}
          >
            <section
              className="audit-modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="audit-modal-title"
              onClick={event => event.stopPropagation()}
            >

              {/* MODAL HEADER */}

              <div className="audit-modal-header">

                <div>
                  <p className="eyebrow">
                    AUDIT INVESTIGATION
                  </p>

                  <h2 id="audit-modal-title">
                    Audit Event Details
                  </h2>

                  <span>
                    {selectedAuditEvent.audit_id}
                  </span>
                </div>

                <button
                  type="button"
                  className="audit-close"
                  onClick={() => setSelectedAuditEvent(null)}
                  aria-label="Close audit details"
                >
                  ×
                </button>

              </div>

              {/* EVENT INFORMATION */}

              <div className="audit-detail-grid">

                <div className="audit-detail-item">
                  <label>Action</label>

                  <StatusBadge
                    value={selectedAuditEvent.action}
                    type="audit-action"
                  />
                </div>

                <div className="audit-detail-item">
                  <label>Performed By</label>

                  <strong>
                    {selectedAuditEvent.performed_by || 'Not recorded'}
                  </strong>
                </div>

                <div className="audit-detail-item">
                  <label>Entity Type</label>

                  <strong>
                    {selectedAuditEvent.entity_type || 'Not recorded'}
                  </strong>
                </div>

                <div className="audit-detail-item">
                  <label>Entity ID</label>

                  <strong>
                    {selectedAuditEvent.entity_id || 'Not recorded'}
                  </strong>
                </div>

                <div className="audit-detail-item">
                  <label>Customer</label>

                  <strong>
                    {selectedAuditEvent.customer_name || 'Not recorded'}
                  </strong>

                  <small>
                    {selectedAuditEvent.customer_id || ''}
                  </small>
                </div>

                <div className="audit-detail-item">
                  <label>Date & Time</label>

                  <strong>
                    {formatDate(
                      selectedAuditEvent.performed_at ||
                      selectedAuditEvent.created_at,
                      true
                    )}
                  </strong>
                </div>

                <div className="audit-detail-item">
                  <label>IP Address</label>

                  <strong>
                    {selectedAuditEvent.ip_address || 'Not recorded'}
                  </strong>
                </div>

                <div className="audit-detail-item">
                  <label>Session ID</label>

                  <strong>
                    {selectedAuditEvent.session_id || 'Not recorded'}
                  </strong>
                </div>

              </div>

              {/* PREVIOUS VALUE */}

              <div className="audit-snapshot-section">

                <h3>Previous Value</h3>

                <pre>
                  {formatAuditValue(selectedAuditEvent.old_value)}
                </pre>

              </div>

              {/* UPDATED VALUE */}

              <div className="audit-snapshot-section">

                <h3>Updated Value</h3>

                <pre>
                  {formatAuditValue(selectedAuditEvent.new_value)}
                </pre>

              </div>

              {/* NOTES */}

              <div className="audit-snapshot-section">

                <h3>Audit Notes</h3>

                <p>
                  {selectedAuditEvent.notes || 'No additional notes recorded.'}
                </p>

              </div>

              {/* FOOTER */}

              <div className="audit-modal-footer">

                <button
                  type="button"
                  className="primary-btn"
                  onClick={() => setSelectedAuditEvent(null)}
                >
                  Close Details
                </button>

              </div>

            </section>
          </div>
        )}

      </main>

    </div>
  )
}

export default App
