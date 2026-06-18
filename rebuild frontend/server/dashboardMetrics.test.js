import assert from "node:assert/strict";
import test from "node:test";
import { buildDashboardMetrics, validateLeadMetricState } from "./dashboardMetrics.js";

const base = {
  staff_name: "Alex",
  owner_id: 1,
  source: "Web",
  last_contact_status: "Initial Call",
  priority: "Not Called",
  created_at: "2026-06-01 10:00:00",
  updated_at: "2026-06-01 10:00:00"
};

test("canonical dashboard metrics reconcile charts and rates", () => {
  const rows = [
    { ...base, id: 1, active_client: 0, authorization_received: 0 },
    { ...base, id: 2, active_client: 1, authorization_received: 0, referral_sent_date: "2026-06-02", ccu_id: 1, ccu_name: "CCU A" },
    { ...base, id: 3, active_client: 1, authorization_received: 1, referral_sent_date: "2026-06-03", ccu_id: 1, ccu_name: "CCU A", care_status: "Not Start" },
    { ...base, id: 4, active_client: 1, authorization_received: 1, referral_sent_date: "2026-06-04", ccu_id: 1, ccu_name: "CCU A", care_status: "Care Start" }
  ];

  const result = buildDashboardMetrics(rows, { totalUsers: 4, generatedAt: "2026-06-16T00:00:00.000Z" });

  assert.equal(result.stats.total_leads, 1);
  assert.equal(result.stats.total_records, 4);
  assert.equal(result.stats.active_clients, 1);
  assert.equal(result.stats.authorizations, 1);
  assert.equal(result.stats.care_starts, 1);
  assert.equal(result.rates.confirmation, 3 / 4 * 100);
  assert.equal(result.rates.conversion, 50);
  assert.equal(result.charts.ccuConfirmed[0].count, 1);
  assert.deepEqual(result.charts.pipelineStages.map(({ name, count }) => ({ name, count })), [
    { name: "Leads", count: 1 },
    { name: "Referrals", count: 1 },
    { name: "Authorizations", count: 1 },
    { name: "Care Starts", count: 1 }
  ]);
  assert.ok(result.trust.integrityChecks.every((item) => item.passed));
  assert.equal(result.trust.status, "verified");
});

test("historical contradictions are reported without inflating canonical authorization counts", () => {
  const rows = [
    { ...base, id: 1, active_client: 0, authorization_received: 1 },
    { ...base, id: 2, active_client: 1, authorization_received: 1, referral_sent_date: null, ccu_id: null }
  ];

  const result = buildDashboardMetrics(rows);

  assert.equal(result.stats.authorizations, 1);
  assert.equal(result.charts.ccuConfirmed[0].name, "Unclassified");
  assert.equal(result.trust.status, "attention");
  assert.equal(result.trust.qualityIssues.find((item) => item.code === "authorization_without_referral").count, 1);
  assert.equal(result.trust.qualityIssues.find((item) => item.code === "referral_without_sent_date").count, 1);
});

test("new metric states reject impossible workflow combinations", () => {
  assert.deepEqual(validateLeadMetricState({ active_client: 0, authorization_received: 1 }), ["Authorization requires referral status."]);
  assert.deepEqual(validateLeadMetricState({ active_client: 1, authorization_received: 0, care_status: "Care Start", referral_sent_date: "2026-06-01" }), ["Care Start requires authorization."]);
  assert.deepEqual(validateLeadMetricState({ active_client: 1, authorization_received: 0 }), ["Referral Sent Date is required for referrals."]);
  assert.deepEqual(validateLeadMetricState({ active_client: 1, authorization_received: 1, care_status: "Care Start", referral_sent_date: "2026-06-01" }), []);
});

test("legacy source aliases are combined under the canonical graph label", () => {
  const result = buildDashboardMetrics([
    { ...base, id: 1, source: "HHN", active_client: 0, authorization_received: 0 },
    { ...base, id: 2, source: "Home Health Notify", active_client: 0, authorization_received: 0 }
  ]);

  assert.deepEqual(result.charts.source.map(({ name, count }) => ({ name, count })), [
    { name: "Home Health Notify", count: 2 }
  ]);
  assert.equal(result.trust.qualityIssues.find((item) => item.code === "noncanonical_source").count, 1);
});
