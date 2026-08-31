import assert from "node:assert/strict";
import test from "node:test";
import { formatMonthLabel } from "../src/utils/monthLabel.js";

test("monthly chart labels display the month before the year", () => {
  assert.equal(formatMonthLabel("2026-01"), "Jan 2026");
  assert.equal(formatMonthLabel("2026-08"), "Aug 2026");
});

test("monthly chart labels preserve unexpected values", () => {
  assert.equal(formatMonthLabel("Unknown"), "Unknown");
  assert.equal(formatMonthLabel("2026-13"), "2026-13");
});
