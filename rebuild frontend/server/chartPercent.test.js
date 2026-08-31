import assert from "node:assert/strict";
import test from "node:test";
import { formatPercentage, percentageOf } from "../src/utils/chartPercent.js";

test("chart percentages calculate and round to one decimal place", () => {
  assert.equal(percentageOf(37, 194), 37 / 194 * 100);
  assert.equal(formatPercentage(37, 194), "19.1%");
  assert.equal(formatPercentage(43, 43), "100.0%");
});

test("chart percentages safely handle empty and invalid totals", () => {
  assert.equal(formatPercentage(0, 0), "0.0%");
  assert.equal(formatPercentage(5, undefined), "0.0%");
});
