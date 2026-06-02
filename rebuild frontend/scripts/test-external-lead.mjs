import { spawn } from "child_process";
import fs from "fs";
import net from "net";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import initSqlJs from "sql.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appDir = path.resolve(__dirname, "..");
const repoDir = path.resolve(appDir, "..");
const sourceDb = path.join(repoDir, "backend", "leads.db");
const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "lead-manager-external-test-"));
const tempDb = path.join(tempDir, "leads.db");
const apiKey = "local-external-lead-test-key";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function getFreePort() {
  return await new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      server.close(() => resolve(port));
    });
  });
}

async function waitForServer(url) {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    try {
      const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      if (response.status === 401) return;
    } catch {
      // The child process is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("Timed out waiting for the rebuilt Lead Manager API");
}

function firstApprovedUser(SQL) {
  const db = new SQL.Database(fs.readFileSync(tempDb));
  try {
    const result = db.exec("select id,user_id,username from users where is_approved=1 and user_id is not null order by id limit 1");
    const [row] = result[0]?.values || [];
    assert(row, "The copied database needs at least one approved user with a Staff ID");
    return { id: row[0], userId: row[1], username: row[2] };
  } finally {
    db.close();
  }
}

function verifySavedLead(SQL, phone, user) {
  const db = new SQL.Database(fs.readFileSync(tempDb));
  try {
    const statement = db.prepare(`select first_name,last_name,owner_id,staff_name,custom_user_id,source,phone,street,address,
      city,state,zip_code,medicaid_status,medicaid_no,gender,comments,last_contact_status
      from leads where phone=?`);
    statement.bind([phone]);
    assert(statement.step(), "Expected the external lead to be saved");
    const lead = statement.getAsObject();
    statement.free();

    assert(lead.first_name === "External" && lead.last_name === "Form Test", "Client name mapping failed");
    assert(Number(lead.owner_id) === Number(user.id), "Owner mapping failed");
    assert(lead.staff_name === user.username && lead.custom_user_id === user.userId, "Staff mapping failed");
    assert(lead.street === "101 Test Ave, Unit 2" && lead.address === "101 Test Ave, Unit 2", "Address mapping failed");
    assert(lead.medicaid_status === "yes" && lead.medicaid_no === "MED-TEST-1", "Medicaid mapping failed");
    assert(lead.gender === "Female" && lead.comments === "Temporary integration test", "Details mapping failed");
    assert(lead.last_contact_status === "Initial Call", "Default lead status mapping failed");
  } finally {
    db.close();
  }
}

fs.copyFileSync(sourceDb, tempDb);
const SQL = await initSqlJs();
const user = firstApprovedUser(SQL);
const port = await getFreePort();
const url = `http://127.0.0.1:${port}/api/external-lead`;
const phone = `630-555-${String(Date.now()).slice(-4)}`;
const payload = {
  staff_name: user.username,
  user_id: user.userId,
  source: "Web",
  first_name: "External",
  last_name: "Form Test",
  gender: "Female",
  birthdate: "01/15/1980",
  medicaid: "yes",
  medicaid_number: "MED-TEST-1",
  phone,
  email: "external-form-test@example.com",
  address_line1: "101 Test Ave",
  address_line2: "Unit 2",
  city: "Lombard",
  state: "IL",
  zip: "60148",
  info: "Temporary integration test"
};

const child = spawn(process.execPath, ["server/index.js"], {
  cwd: appDir,
  env: { ...process.env, PORT: String(port), LEAD_DB: tempDb, LEAD_MANAGER_API_KEY: apiKey },
  stdio: ["ignore", "pipe", "pipe"]
});

try {
  await waitForServer(url);

  const unauthorized = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  assert(unauthorized.status === 401, `Expected missing API key to return 401, got ${unauthorized.status}`);

  const staffResponse = await fetch(`${url}/staff`, { headers: { "X-API-Key": apiKey } });
  assert(staffResponse.status === 200, `Expected staff lookup to return 200, got ${staffResponse.status}`);
  const { staff } = await staffResponse.json();
  assert(staff.some((entry) => entry.username === user.username && entry.user_id === user.userId), "Expected staff lookup to include the approved test user");

  const created = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
    body: JSON.stringify(payload)
  });
  assert(created.status === 201, `Expected lead creation to return 201, got ${created.status}: ${await created.text()}`);

  const duplicate = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
    body: JSON.stringify(payload)
  });
  assert(duplicate.status === 409, `Expected duplicate submission to return 409, got ${duplicate.status}`);

  verifySavedLead(SQL, phone, user);
  console.log("External lead integration passed: auth, staff lookup, insert, field mapping, and duplicate blocking");
} finally {
  child.kill("SIGTERM");
  fs.rmSync(tempDir, { recursive: true, force: true });
}
