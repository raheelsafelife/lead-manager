import assert from "node:assert/strict";
import test from "node:test";
import { cached, clearDataCaches } from "./dataCache.js";

test("a data mutation invalidates cached dashboard totals immediately", async () => {
  let total = 29;
  const load = () => cached("dashboard:all:Active:base", 120_000, async () => total);
  assert.equal(await load(), 29);
  total = 30;
  assert.equal(await load(), 29);
  clearDataCaches();
  assert.equal(await load(), 30);
});
