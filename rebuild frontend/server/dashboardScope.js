const activeLeadStatuses = new Set(["Initial Call", "No Response"]);
const activeReferralStatuses = new Set(["Initial Referral Sent", "Assessment Scheduled", "Assessment Done"]);
const inactiveAuthorizationStatuses = new Set(["Hold", "Terminated", "Deceased"]);

export function isActiveDashboardRow(row) {
  const isReferral = Number(row.active_client) === 1;
  const isAuthorization = isReferral && Number(row.authorization_received) === 1;
  const contactStatus = String(row.last_contact_status || "").trim();
  const careStatus = String(row.care_status || "").trim();
  if (!isReferral) return activeLeadStatuses.has(careStatus || contactStatus);
  if (!isAuthorization) return activeReferralStatuses.has(contactStatus);
  return !inactiveAuthorizationStatuses.has(careStatus);
}

export function filterDashboardRowsByScope(rows, dataScope) {
  if (dataScope === "All") return rows;
  return rows.filter((row) => isActiveDashboardRow(row) === (dataScope === "Active"));
}

export function matchesDashboardFolder(row, { type, dataScope, chicagoOnly = false, includeChicago = false, transferView = false, reportable = false }) {
  if (row.deleted_at) return false;
  if (dataScope !== "All" && isActiveDashboardRow(row) !== (dataScope === "Active")) return false;
  if (!includeChicago && (Number(row.is_chicago_referral) === 1) !== chicagoOnly) return false;
  if (type === "lead" && Number(row.active_client) !== 0) return false;
  if (type === "referral" && !(Number(row.active_client) === 1 && Number(row.authorization_received) !== 1)) return false;
  if (type === "authorization" && !(Number(row.active_client) === 1 && Number(row.authorization_received) === 1)) return false;
  if (transferView && !(row.source === "Transfer" || row.care_status === "Transfer Received")) return false;
  if (reportable && row.care_status === "Not Start") return false;
  return true;
}
