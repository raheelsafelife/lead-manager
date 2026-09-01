import assert from "node:assert/strict";
import test from "node:test";
import { buildDashboardMetrics } from "./dashboardMetrics.js";
import { filterDashboardRowsByScope, matchesDashboardFolder } from "./dashboardScope.js";

const base = { deleted_at: null, source: "Web", last_contact_status: "Initial Call", created_at: "2026-09-01", updated_at: "2026-09-01" };
const rows = [
  { ...base, id: 1, active_client: 0, authorization_received: 0 },
  { ...base, id: 2, active_client: 0, authorization_received: 0, is_chicago_referral: 1 },
  { ...base, id: 3, active_client: 0, authorization_received: 0, last_contact_status: "Not Interested" },
  { ...base, id: 4, active_client: 1, authorization_received: 0, referral_sent_date: "2026-09-01", last_contact_status: "Initial Referral Sent" },
  { ...base, id: 5, active_client: 1, authorization_received: 0, referral_sent_date: "2026-09-01", last_contact_status: "Services Refused", is_chicago_referral: 1 },
  { ...base, id: 6, active_client: 1, authorization_received: 1, referral_sent_date: "2026-09-01", care_status: "Care Start" },
  { ...base, id: 7, active_client: 1, authorization_received: 1, referral_sent_date: "2026-09-01", source: "Transfer", care_status: "Transfer Received" },
  { ...base, id: 8, active_client: 1, authorization_received: 1, referral_sent_date: "2026-09-01", care_status: "Not Start" },
  { ...base, id: 9, active_client: 0, authorization_received: 0, deleted_at: "2026-09-02" }
];

for (const dataScope of ["Active", "Inactive", "All"]) {
  test(`${dataScope} dashboard cards reconcile with folders, charts, and CSV row sets`, () => {
    const visible = filterDashboardRowsByScope(rows.filter((row) => !row.deleted_at), dataScope);
    const metrics = buildDashboardMetrics(visible);
    const folder = (options) => rows.filter((row) => matchesDashboardFolder(row, { dataScope, ...options }));
    assert.equal(metrics.stats.regular_leads, folder({ type: "lead" }).length);
    assert.equal(metrics.stats.chicago_leads, folder({ type: "lead", chicagoOnly: true }).length);
    assert.equal(metrics.stats.regular_referrals, folder({ type: "referral" }).length);
    assert.equal(metrics.stats.chicago_referrals, folder({ type: "referral", chicagoOnly: true }).length);
    assert.equal(metrics.stats.authorizations, folder({ type: "authorization", reportable: true, includeChicago: true }).length);
    assert.equal(metrics.stats.authorizations, metrics.charts.ccuConfirmed.reduce((sum, item) => sum + item.count, 0));
    assert.equal(metrics.stats.transfers, visible.filter((row) => Number(row.authorization_received) === 1 && (row.source === "Transfer" || row.care_status === "Transfer Received")).length);
    assert.ok(metrics.trust.integrityChecks.every((check) => check.passed));
  });
}

test("Active and Inactive partition All and deleted records stay excluded", () => {
  const live = rows.filter((row) => !row.deleted_at);
  assert.equal(filterDashboardRowsByScope(live, "Active").length + filterDashboardRowsByScope(live, "Inactive").length, filterDashboardRowsByScope(live, "All").length);
  const active = buildDashboardMetrics(filterDashboardRowsByScope(live, "Active")).stats;
  const inactive = buildDashboardMetrics(filterDashboardRowsByScope(live, "Inactive")).stats;
  const all = buildDashboardMetrics(filterDashboardRowsByScope(live, "All")).stats;
  for (const key of ["regular_leads", "chicago_leads", "regular_referrals", "chicago_referrals", "authorizations"]) {
    assert.equal(active[key] + inactive[key], all[key], `${key} must partition across Active and Inactive`);
  }
  assert.equal(rows.filter((row) => matchesDashboardFolder(row, { type: "lead", dataScope: "All" })).some((row) => row.deleted_at), false);
});
