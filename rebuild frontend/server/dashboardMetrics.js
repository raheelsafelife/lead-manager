export const DASHBOARD_METRIC_VERSION = "2026-06-16.1";

export const DASHBOARD_METRIC_DEFINITIONS = {
  totalLeads: "Non-deleted lead records visible in the selected dashboard scope.",
  referrals: "Visible leads with active_client = 1.",
  authorizations: "Visible referrals with authorization_received = 1 and care_status is not Care Start.",
  careStarts: "Visible authorized referrals with care_status = Care Start.",
  confirmationRate: "Referrals divided by total visible leads.",
  conversionRate: "Care Starts divided by visible referrals.",
  monthlyLeads: "Visible leads grouped by the YYYY-MM portion of created_at.",
  ownership: "Individual scope matches owner_id first and also supports the legacy staff_name assignment."
};

const count = (value) => Number(value || 0);
const isTrue = (value) => Number(value) === 1;
const hasText = (value) => String(value || "").trim().length > 0;
const sourceAliases = new Map([
  ["hhn", "Home Health Notify"]
]);

function canonicalSource(value) {
  const source = String(value || "").trim();
  return sourceAliases.get(source.toLowerCase()) || source || "Unclassified";
}

function group(key, sourceRows) {
  return Object.values(sourceRows.reduce((acc, row) => {
    const name = hasText(row[key]) ? String(row[key]).trim() : "Unclassified";
    acc[name] = acc[name] || { name, count: 0, rowIds: [] };
    acc[name].count += 1;
    acc[name].rowIds.push(row.id);
    return acc;
  }, {})).sort((left, right) => right.count - left.count || String(left.name).localeCompare(String(right.name)));
}

function issue(code, label, rows, severity = "warning") {
  return {
    code,
    label,
    severity,
    count: rows.length,
    rowIds: rows.map((row) => row.id)
  };
}

function check(code, label, actual, expected) {
  return {
    code,
    label,
    actual,
    expected,
    passed: actual === expected
  };
}

function latestTimestamp(rows) {
  return rows.reduce((latest, row) => {
    const value = String(row.updated_at || row.created_at || "");
    return value > latest ? value : latest;
  }, "");
}

export function buildDashboardMetrics(rows, { totalUsers = 0, generatedAt = new Date().toISOString() } = {}) {
  const hydratedRows = rows.map((row) => ({
    ...row,
    full_name: `${row.first_name || ""} ${row.last_name || ""}`.trim(),
    month: /^\d{4}-\d{2}/.test(String(row.created_at || "")) ? String(row.created_at).slice(0, 7) : "Invalid date",
    ccu_name: hasText(row.ccu_name) ? String(row.ccu_name).trim() : "Unclassified",
    agency_name: hasText(row.agency_name) ? String(row.agency_name).trim() : "Unclassified",
    source_label: canonicalSource(row.source),
    auth_label: isTrue(row.authorization_received) ? "Authorized" : "Pending",
    referral_label: isTrue(row.active_client) ? "Referrals" : "Pending"
  }));

  const leadStage = hydratedRows.filter((row) => !isTrue(row.active_client));
  const allReferrals = hydratedRows.filter((row) => isTrue(row.active_client));
  const referralStage = allReferrals.filter((row) => !isTrue(row.authorization_received));
  const allAuthorizations = allReferrals.filter((row) => isTrue(row.authorization_received));
  const careStart = allAuthorizations.filter((row) => row.care_status === "Care Start");
  const authorizationStage = allAuthorizations.filter((row) => row.care_status !== "Care Start");
  const notStart = allAuthorizations.filter((row) => row.care_status === "Not Start");
  const pendingCare = authorizationStage.filter((row) => row.care_status !== "Not Start");

  const charts = {
    staff: group("staff_name", leadStage),
    source: group("source_label", leadStage),
    status: group("last_contact_status", leadStage),
    month: group("month", leadStage).sort((left, right) => String(left.name).localeCompare(String(right.name))),
    event: group("event_name", leadStage.filter((row) => row.source === "Event")),
    wordOfMouth: group("word_of_mouth_type", leadStage.filter((row) => row.source === "Word of Mouth")),
    priority: group("priority", leadStage),
    auth: group("auth_label", authorizationStage),
    ccuSent: group("ccu_name", referralStage),
    ccuConfirmed: group("ccu_name", authorizationStage),
    pipelineStages: [
      { name: "Leads", count: leadStage.length, rowIds: leadStage.map((row) => row.id) },
      { name: "Referrals", count: referralStage.length, rowIds: referralStage.map((row) => row.id) },
      { name: "Authorizations", count: authorizationStage.length, rowIds: authorizationStage.map((row) => row.id) },
      { name: "Care Starts", count: careStart.length, rowIds: careStart.map((row) => row.id) }
    ],
    referralConfirmation: [
      { name: "Referrals", count: referralStage.length, rowIds: referralStage.map((row) => row.id) },
      { name: "Leads", count: leadStage.length, rowIds: leadStage.map((row) => row.id) }
    ],
    leadConversion: [
      { name: "Care Start", count: careStart.length, rowIds: careStart.map((row) => row.id) },
      { name: "Not Start", count: notStart.length, rowIds: notStart.map((row) => row.id) },
      { name: "Pending", count: pendingCare.length, rowIds: pendingCare.map((row) => row.id) }
    ]
  };

  const qualityIssues = [
    issue("authorization_without_referral", "Authorization marked without referral status", hydratedRows.filter((row) => isTrue(row.authorization_received) && !isTrue(row.active_client)), "error"),
    issue("care_start_without_authorization", "Care Start marked without an eligible authorization", hydratedRows.filter((row) => row.care_status === "Care Start" && !(isTrue(row.active_client) && isTrue(row.authorization_received))), "error"),
    issue("referral_without_sent_date", "Referral missing referral-sent date", allReferrals.filter((row) => !hasText(row.referral_sent_date))),
    issue("authorization_without_ccu", "Authorized referral missing CCU", allAuthorizations.filter((row) => row.source !== "Transfer" && !row.ccu_id)),
    issue("missing_owner", "Lead missing stable owner", hydratedRows.filter((row) => !row.owner_id)),
    issue("missing_priority", "Lead missing priority", hydratedRows.filter((row) => !hasText(row.priority))),
    issue("noncanonical_source", "Lead uses a legacy source label", hydratedRows.filter((row) => canonicalSource(row.source) !== String(row.source || "").trim())),
    issue("invalid_created_at", "Lead has an invalid creation timestamp", hydratedRows.filter((row) => row.month === "Invalid date"), "error")
  ].filter((item) => item.count > 0);

  const sum = (items) => items.reduce((total, item) => total + count(item.count), 0);
  const integrityChecks = [
    check("source_total", "Source groups reconcile to lead-stage total", sum(charts.source), leadStage.length),
    check("status_total", "Status groups reconcile to lead-stage total", sum(charts.status), leadStage.length),
    check("month_total", "Monthly groups reconcile to lead-stage total", sum(charts.month), leadStage.length),
    check("pipeline_total", "Pipeline stages reconcile to all records", sum(charts.pipelineStages), hydratedRows.length),
    check("conversion_total", "Conversion pipeline reconciles to all authorizations", sum(charts.leadConversion), allAuthorizations.length),
    check("authorization_order", "Authorizations do not exceed all referrals", allAuthorizations.length <= allReferrals.length, true),
    check("care_start_order", "Care Starts do not exceed all authorizations", careStart.length <= allAuthorizations.length, true)
  ];

  const failedChecks = integrityChecks.filter((item) => !item.passed);
  const errorIssues = qualityIssues.filter((item) => item.severity === "error");

  return {
    stats: {
      total_records: hydratedRows.length,
      total_leads: leadStage.length,
      total_users: count(totalUsers),
      active_clients: referralStage.length,
      authorizations: authorizationStage.length,
      care_starts: careStart.length
    },
    charts,
    rates: {
      confirmation: hydratedRows.length ? (allReferrals.length / hydratedRows.length) * 100 : 0,
      conversion: allAuthorizations.length ? (careStart.length / allAuthorizations.length) * 100 : 0
    },
    rows: hydratedRows,
    trust: {
      status: failedChecks.length || errorIssues.length ? "attention" : qualityIssues.length ? "review" : "verified",
      metricVersion: DASHBOARD_METRIC_VERSION,
      generatedAt,
      sourceUpdatedAt: latestTimestamp(hydratedRows) || null,
      definitions: DASHBOARD_METRIC_DEFINITIONS,
      integrityChecks,
      qualityIssues,
      failedCheckCount: failedChecks.length,
      affectedRecordCount: new Set(qualityIssues.flatMap((item) => item.rowIds)).size
    }
  };
}

export function validateLeadMetricState(lead) {
  const errors = [];
  const referral = isTrue(lead.active_client);
  const authorization = isTrue(lead.authorization_received);

  if (authorization && !referral) errors.push("Authorization requires referral status.");
  if (lead.care_status === "Care Start" && !authorization) errors.push("Care Start requires authorization.");
  if (lead.care_status === "Care Start" && !referral) errors.push("Care Start requires referral status.");
  if (referral && !hasText(lead.referral_sent_date)) errors.push("Referral Sent Date is required for referrals.");

  return errors;
}
