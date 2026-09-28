import assert from "node:assert/strict";
import { once } from "node:events";
import test from "node:test";
import { request } from "node:http";
import express from "express";
import cors from "cors";
import { searchPrivacy } from "./searchPrivacy.js";

function fetch(url, options = {}) {
  return new Promise((resolve, reject) => {
    const req = request(url, options, (res) => {
      res.resume();
      res.on("end", () => resolve({
        status: res.statusCode,
        headers: { get: (name) => res.headers[name] ?? null },
        arrayBuffer: async () => {}
      }));
    });
    req.on("error", reject);
    req.end();
  });
}

test("private-domain headers cover success, errors and CORS without blocking requests", async (t) => {
  const app = express();
  app.use(searchPrivacy);
  app.use(cors({ origin: true, credentials: true }));
  app.get("/api/private", (req, res) => {
    if (req.headers.authorization !== "Bearer test-only") return res.sendStatus(401);
    res.json({ ok: true });
  });
  app.get("/", (_req, res) => res.send("login shell"));
  app.get("/error", (_req, res) => res.sendStatus(500));
  const server = app.listen(0, "127.0.0.1");
  t.after(() => new Promise((resolve) => server.close(resolve)));
  await once(server, "listening");
  const base = `http://127.0.0.1:${server.address().port}`;
  for (const [route, method, extra, status] of [
    ["/", "GET", {}, 200],
    ["/", "HEAD", {}, 200],
    ["/api/private", "GET", {}, 401],
    ["/api/private", "GET", { authorization: "Bearer test-only" }, 200],
    ["/missing", "GET", {}, 404],
    ["/error", "GET", {}, 500],
    ["/api/private", "OPTIONS", { origin: "https://ccpleads.safelifehomehealth.com", "access-control-request-method": "GET" }, 204]
  ]) {
    const response = await fetch(base + route, { method, headers: { host: "ccpleads.safelifehomehealth.com", ...extra } });
    assert.equal(response.status, status);
    assert.equal(response.headers.get("x-robots-tag"), "noindex, nofollow, noarchive");
    if (method === "OPTIONS") assert.equal(response.headers.get("access-control-allow-credentials"), "true");
    await response.arrayBuffer();
  }
  const other = await fetch(base, { headers: { host: "safelifehomehealth.com", "x-forwarded-host": "ccpleads.safelifehomehealth.com" } });
  assert.equal(other.headers.get("x-robots-tag"), null);
  await other.arrayBuffer();
});
