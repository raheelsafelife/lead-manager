import express from "express";
import cors from "cors";
import path from "path";
import fs from "fs";
import crypto from "crypto";
import jwt from "jsonwebtoken";
import multer from "multer";
import ExcelJS from "exceljs";
import { AlignmentType, Document, PageOrientation, Packer, Paragraph, Table, TableCell, TableLayoutType, TableRow, TextRun, WidthType } from "docx";
import { fileURLToPath } from "url";
import { createDatabase } from "./db.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "..", "..");
const dbPath = process.env.LEAD_DB || path.join(rootDir, "backend", "leads.db");
const uploadsDir = path.join(rootDir, "backend", "uploads");
const distDir = path.resolve(__dirname, "..", "dist");
const schemaPath = path.resolve(__dirname, "..", "migrations", "aws", "postgres-schema.sql");
const jwtSecret = process.env.JWT_SECRET_KEY || "f2f9c7c55bdbe69ea5ac0da9b29fb2c26555a720266bfb4ba936568b27ab7cef";
fs.mkdirSync(uploadsDir, { recursive: true });

const db = await createDatabase({ dbPath, schemaPath });
if (db.mode === "sqlite") {
  db.exec(`create table if not exists notification_reads (
    user_id integer not null,
    notification_id text not null,
    read_at text not null,
    primary key (user_id, notification_id)
  )`);
  const leadColumns = db.columns("leads");
  if (leadColumns.length && !leadColumns.includes("gender")) {
    db.exec("alter table leads add column gender varchar(30)");
  }
}

const app = express();
const upload = multer({ dest: uploadsDir });
app.use(cors({ origin: true, credentials: true }));
app.use(express.json({ limit: "10mb" }));
app.use((req, res, next) => {
  if (req.path.startsWith("/api/")) {
    res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate, proxy-revalidate");
    res.setHeader("Pragma", "no-cache");
    res.setHeader("Expires", "0");
  }
  next();
});

const now = () => new Date().toISOString().replace("T", " ").replace("Z", "");
const bool = (v) => (v ? 1 : 0);
const publicUser = (u, options = {}) => u && ({
  id: u.id,
  user_id: u.user_id,
  username: u.username,
  email: u.email,
  role: u.role,
  is_approved: !!u.is_approved,
  ...(options.profile ? { profile_pic: u.profile_pic } : {})
});
const normalizePhone = (value = "") => String(value || "").replace(/\D/g, "");

const cache = new Map();
function cacheKey(name, parts = []) {
  return [name, ...parts.map((part) => String(part ?? ""))].join(":");
}

async function cached(key, ttlMs, loader) {
  const hit = cache.get(key);
  if (hit && hit.expires > Date.now()) return hit.value;
  const value = await loader();
  cache.set(key, { value, expires: Date.now() + ttlMs });
  return value;
}

function clearDataCaches() {
  cache.clear();
}

const originalDbRun = db.run.bind(db);
db.run = async (...args) => {
  const result = await originalDbRun(...args);
  clearDataCaches();
  return result;
};

function duplicateKind(lead) {
  if (!lead) return "";
  if (Number(lead.authorization_received) === 1) return lead.source === "Transfer" && lead.care_status !== "Care Start" ? "transfer case" : "authorization";
  if (Number(lead.active_client) === 1) return "referral";
  return "lead";
}

function searchTargetForLead(lead) {
  if (Number(lead.authorization_received) === 1) {
    if (lead.source === "Transfer" && lead.care_status !== "Care Start") return { targetPage: "Transfer Cases", targetUrl: `/authorizations?idSearch=${lead.id}&transferView=true` };
    return { targetPage: "Authorizations", targetUrl: `/authorizations?idSearch=${lead.id}` };
  }
  if (Number(lead.active_client) === 1) return { targetPage: "Referrals Sent", targetUrl: `/referrals?idSearch=${lead.id}` };
  return { targetPage: "View Leads", targetUrl: `/view-leads?idSearch=${lead.id}` };
}

async function findDuplicateLead(body) {
  const firstName = String(body.first_name || "").trim().toLowerCase();
  const lastName = String(body.last_name || "").trim().toLowerCase();
  const phone = normalizePhone(body.phone);
  if (!firstName || !lastName || !phone) return null;
  const candidates = await db.all("select * from leads where lower(first_name)=@firstName and lower(last_name)=@lastName", { firstName, lastName });
  return candidates.find((lead) => normalizePhone(lead.phone) === phone) || null;
}

function b64DecodePasslib(value) {
  let text = value.replace(/\./g, "+");
  while (text.length % 4) text += "=";
  return Buffer.from(text, "base64");
}

function verifyPassword(password, stored) {
  if (!stored) return false;
  if (stored.startsWith("$pbkdf2-sha256$")) {
    const [, , rounds, salt, digest] = stored.split("$");
    const key = crypto.pbkdf2Sync(Buffer.from(password, "utf8").subarray(0, 72), b64DecodePasslib(salt), Number(rounds), 32, "sha256");
    return crypto.timingSafeEqual(key, b64DecodePasslib(digest));
  }
  if (!stored.startsWith("$")) return stored === password;
  return false;
}

function passlibB64(buffer) {
  return Buffer.from(buffer).toString("base64").replace(/\+/g, ".").replace(/=+$/g, "");
}

function hashPassword(password) {
  const rounds = 29000;
  const salt = crypto.randomBytes(16);
  const key = crypto.pbkdf2Sync(Buffer.from(password, "utf8").subarray(0, 72), salt, rounds, 32, "sha256");
  return `$pbkdf2-sha256$${rounds}$${passlibB64(salt)}$${passlibB64(key)}`;
}

function auth(req, res, next) {
  const header = req.headers.authorization || "";
  const tokenFromHeader = header.startsWith("Bearer ") ? header.slice(7) : null;
  const tokenFromQuery = typeof req.query.token === "string" ? req.query.token : null;
  const token = tokenFromHeader || tokenFromQuery;
  if (!token) return res.status(401).json({ error: "Missing token" });
  try {
    req.user = jwt.verify(token, jwtSecret);
    next();
  } catch {
    res.status(401).json({ error: "Invalid token" });
  }
}

function admin(req, res, next) {
  if (req.user.role !== "admin") return res.status(403).json({ error: "Admin only" });
  next();
}

async function logActivity(user, actionType, entityType, entityId, entityName, description, oldValue = null, newValue = null, keywords = "") {
  await db.run(`insert into activity_logs (timestamp,user_id,username,action_type,entity_type,entity_id,entity_name,description,old_value,new_value,keywords)
    values (@timestamp,@user_id,@username,@action_type,@entity_type,@entity_id,@entity_name,@description,@old_value,@new_value,@keywords)`, {
    timestamp: now(),
    user_id: user?.user_id || user?.id || null,
    username: user?.username || "system",
    action_type: actionType,
    entity_type: entityType,
    entity_id: entityId,
    entity_name: entityName,
    description,
    old_value: oldValue ? JSON.stringify(oldValue) : null,
    new_value: newValue ? JSON.stringify(newValue) : null,
    keywords
  });
}

const leadSelect = `select leads.*, agencies.name as agency_name, agencies.address as agency_address, agencies.phone as agency_phone,
  agencies.fax as agency_fax, agencies.email as agency_email, ccus.name as ccu_name, ccus.street as ccu_street,
  ccus.city as ccu_city, ccus.state as ccu_state, ccus.zip_code as ccu_zip_code, ccus.phone as ccu_phone,
  ccus.fax as ccu_fax, ccus.email as ccu_email, ccus.care_coordinator_name as ccu_care_coordinator_name
  from leads left join agencies on agencies.id = leads.agency_id left join ccus on ccus.id = leads.ccu_id`;

function buildLeadQuery(q = {}, user) {
  const where = [];
  const params = {};
  const includeDeleted = q.includeDeleted === "true" || q.includeDeleted === true;
  if (includeDeleted) where.push("leads.deleted_at is not null");
  else where.push("leads.deleted_at is null");

  if (q.onlyMine === "true" || q.onlyMine === true) {
    where.push("(leads.owner_id = @ownerId or leads.staff_name = @staffName)");
    params.ownerId = user.user_id;
    params.staffName = user.username;
  }
  if (q.type === "lead") {
    where.push("coalesce(leads.active_client,0) = 0");
  }
  if (q.type === "referral") {
    where.push("leads.active_client = 1");
    where.push("coalesce(leads.authorization_received,0) = 0");
  }
  if (q.type === "authorization") {
    where.push("leads.active_client = 1");
    where.push("leads.authorization_received = 1");
    if (q.transferView === "true" || q.transferView === true) {
      where.push("leads.source = 'Transfer'");
      where.push("coalesce(leads.care_status,'') != 'Care Start'");
    } else {
      where.push("(leads.source != 'Transfer' or leads.care_status = 'Care Start')");
    }
  }
  if (q.active && q.active !== "All") {
    const statusSets = {
      lead: {
        column: "last_contact_status",
        active: ["Initial Call", "No Response"],
        inactive: ["Not Interested"]
      },
      referral: {
        column: "last_contact_status",
        active: ["Initial Referral Sent", "Assessment Scheduled", "Assessment Done"],
        inactive: ["Not Approved", "Services Refused"]
      },
      authorization: {
        column: "care_status",
        active: ["Care Start", "Not Start", "Transfer Received"],
        inactive: ["Hold", "Terminated", "Deceased"]
      }
    };
    const config = statusSets[q.type] || statusSets.lead;
    const list = q.active === "Active" ? config.active : config.inactive;
    if (config.column === "care_status") {
      where.push(`leads.care_status in (${list.map((_, i) => `@active${i}`).join(",")})`);
    } else {
      where.push(`leads.last_contact_status in (${list.map((_, i) => `@active${i}`).join(",")})`);
    }
    list.forEach((v, i) => { params[`active${i}`] = v; });
  }
  if (q.status && q.status !== "All") {
    where.push("(leads.last_contact_status = @status or leads.care_status = @status)");
    params.status = q.status;
  }
  if (q.callStatus && q.callStatus !== "All") {
    where.push("coalesce(leads.priority,'Not Called') = @callStatus");
    params.callStatus = q.callStatus;
  }
  if (q.referralType && q.referralType !== "All") {
    where.push("coalesce(leads.referral_type,'Regular') = @referralType");
    params.referralType = q.referralType;
  }
  if (q.tagColor && q.tagColor !== "All") {
    where.push("leads.tag_color = @tagColor");
    params.tagColor = q.tagColor;
  }
  if (q.caregiverType && q.caregiverType !== "All") {
    where.push("leads.caregiver_type = @caregiverType");
    params.caregiverType = q.caregiverType;
  }
  if (q.ccu && q.ccu !== "All") {
    where.push("ccus.name = @ccu");
    params.ccu = q.ccu;
  }
  if (q.payor && q.payor !== "All") {
    where.push("agencies.name = @payor");
    params.payor = q.payor;
  }
  if (q.staff) {
    where.push("lower(leads.staff_name) like @staff");
    params.staff = `%${String(q.staff).toLowerCase()}%`;
  }
  if (q.source) {
    where.push("lower(leads.source) like @source");
    params.source = `%${String(q.source).toLowerCase()}%`;
  }
  if (q.search) {
    const tokens = String(q.search).trim().toLowerCase().split(/\s+/).filter(Boolean);
    tokens.forEach((token, i) => {
      params[`search${i}`] = `%${token}%`;
      if (q.pageSearch === "true" || q.pageSearch === true) {
        where.push(`(lower(leads.first_name) like @search${i} or lower(leads.last_name) like @search${i} or lower(leads.first_name || ' ' || leads.last_name) like @search${i} or lower(leads.last_name || ' ' || leads.first_name) like @search${i})`);
      } else {
        where.push(`(lower(leads.first_name) like @search${i} or lower(leads.last_name) like @search${i} or lower(leads.first_name || ' ' || leads.last_name) like @search${i} or lower(leads.last_name || ' ' || leads.first_name) like @search${i} or lower(coalesce(leads.phone,'')) like @search${i} or lower(coalesce(leads.medicaid_no,'')) like @search${i} or lower(coalesce(leads.custom_user_id,'')) like @search${i} or cast(leads.id as text) like @search${i})`);
      }
    });
  }
  if (q.idSearch) {
    if (q.pageSearch === "true" || q.pageSearch === true) {
      where.push("cast(leads.id as text) = @idSearch");
      params.idSearch = String(q.idSearch).trim();
    } else {
      where.push("cast(leads.id as text) like @idSearch");
      params.idSearch = `%${q.idSearch}%`;
    }
  }
  if (q.startDate) {
    where.push("date(leads.created_at) >= date(@startDate)");
    params.startDate = q.startDate;
  }
  if (q.endDate) {
    where.push("date(leads.created_at) <= date(@endDate)");
    params.endDate = q.endDate;
  }
  return { where: where.length ? `where ${where.join(" and ")}` : "", params };
}

async function getLead(id, includeDeleted = false) {
  const deleted = includeDeleted ? "" : "and leads.deleted_at is null";
  return await db.get(`${leadSelect} where leads.id = ? ${deleted}`, id);
}

async function listLeads(q, user) {
  const { where, params } = buildLeadQuery(q, user);
  const sort = q.sort === "Recently Updated" ? "leads.updated_at desc" : "leads.created_at desc";
  const limit = Math.min(Number(q.limit || 10), 2000);
  const offset = Math.max(Number(q.offset || 0), 0);
  const rows = await db.all(`${leadSelect} ${where} order by ${sort} limit @limit offset @offset`, { ...params, limit, offset });
  const total = (await db.get(`select count(*) as count from leads left join agencies on agencies.id = leads.agency_id left join ccus on ccus.id = leads.ccu_id ${where}`, params)).count;
  return { rows, total };
}

app.post("/api/auth/login", async (req, res) => {
  const { username, password } = req.body;
  const user = await db.get("select * from users where username = ?", username);
  if (!user || !verifyPassword(password || "", user.hashed_password)) return res.status(401).json({ error: "Invalid credentials" });
  if (!user.is_approved) return res.status(403).json({ error: "Account pending approval" });
  const payload = { sub: user.username, username: user.username, role: user.role, user_id: user.id, employee_id: user.user_id };
  const token = jwt.sign(payload, jwtSecret, { expiresIn: "7d" });
  await logActivity(payload, "USER_LOGIN", "User", user.id, user.username, `User '${user.username}' logged in`, null, null, "auth,login");
  res.json({ token, user: publicUser(user, { profile: true }) });
});

async function getCurrentUser(userId) {
  return cached(cacheKey("user", [userId]), 60_000, () => db.get("select * from users where id = ?", userId));
}

async function lookupPayload() {
  return cached("lookups", 300_000, async () => {
    const [users, approvedUsers, agencies, agencySuboptions, ccus, events] = await Promise.all([
      db.all("select id,user_id,username,email,role,is_approved,password_reset_requested,created_at from users order by username", ),
      db.all("select id,user_id,username,email,role from users where is_approved = 1 order by username", ),
      db.all("select * from agencies order by name", ),
      db.all("select * from agency_suboptions order by name", ),
      db.all("select * from ccus order by name", ),
      db.all("select * from events order by event_name", )
    ]);
    return { users, approvedUsers, agencies, agencySuboptions, ccus, events };
  });
}

async function activityPayload(user, query = {}) {
  const limit = Math.min(Number(query.limit || 100), 500);
  const offset = Math.max(Number(query.offset || 0), 0);
  const where = [];
  const params = { limit, offset };
  if (user.role !== "admin") {
    where.push("username = @username");
    params.username = user.username;
  } else if (query.username) {
    where.push("username = @username");
    params.username = query.username;
  }
  if (query.actionType) {
    where.push("action_type = @actionType");
    params.actionType = query.actionType;
  }
  if (query.entityType) {
    where.push("entity_type = @entityType");
    params.entityType = query.entityType;
  }
  if (query.startDate) {
    where.push("timestamp >= @startDate");
    params.startDate = query.startDate;
  }
  if (query.endDate) {
    where.push("timestamp <= @endDate");
    params.endDate = `${query.endDate} 23:59:59`;
  }
  if (query.search) {
    where.push("(lower(description) like @search or lower(keywords) like @search or lower(entity_name) like @search)");
    params.search = `%${String(query.search).toLowerCase()}%`;
  }
  const clause = where.length ? `where ${where.join(" and ")}` : "";
  const [totalRow, rows] = await Promise.all([
    db.get(`select count(*) as count from activity_logs ${clause}`, params),
    db.all(`select * from activity_logs ${clause} order by timestamp desc limit @limit offset @offset`, params)
  ]);
  return { rows, total: totalRow?.count || 0 };
}

app.get("/api/auth/me", auth, async (req, res) => {
  const user = await getCurrentUser(req.user.user_id);
  res.json({ user: publicUser(user) });
});

app.post("/api/auth/logout", auth, async (req, res) => {
  await logActivity(req.user, "USER_LOGOUT", "User", req.user.user_id, req.user.username, `User '${req.user.username}' logged out`, null, null, "auth,logout");
  res.json({ success: true });
});

app.post("/api/auth/signup", async (req, res) => {
  const { user_id, username, email, password } = req.body;
  if (!user_id || !username || !email || !password) return res.status(400).json({ error: "Please fill in all fields" });
  if (String(password).length < 6) return res.status(400).json({ error: "Password must be at least 6 characters" });
  if (!String(email).includes("@")) return res.status(400).json({ error: "Please enter a valid email" });
  if (await db.get("select id from users where user_id=? or username=? or email=?", user_id, username, email)) return res.status(409).json({ error: "User ID, username, or email already exists" });
  await db.run("insert into users (user_id,username,email,hashed_password,role,is_approved,password_reset_requested,created_at) values (?,?,?,?,?,?,?,?)", user_id, username, email, hashPassword(password), "user", 0, 0, now());
  res.status(201).json({ success: true });
});

app.post("/api/auth/forgot", async (req, res) => {
  const { username } = req.body;
  const user = await db.get("select * from users where username=?", username);
  if (!user) return res.status(404).json({ error: "Username not found" });
  await db.run("update users set password_reset_requested=1 where id=?", user.id);
  res.json({ success: true });
});

app.get("/api/lookups", auth, async (_req, res) => {
  res.json(await lookupPayload());
});

async function notificationRows(user) {
  const notifications = [];
  if (user.role === "admin") {
    const pendingUsers = await db.all("select id,username,created_at from users where is_approved = 0 order by created_at desc limit 5", );
    pendingUsers.forEach((pendingUser) => notifications.push({
      id: `pending-user-${pendingUser.id}`,
      type: "User approval",
      title: `ID: ${pendingUser.id} | ${pendingUser.username}`,
      message: `${pendingUser.username} is waiting for approval`,
      detail: pendingUser.created_at || "",
      due: pendingUser.created_at || "",
      icon: "user",
      link: "/users",
      done: false
    }));
    const resetUsers = await db.all("select id,username from users where password_reset_requested = 1 order by username limit 5", );
    resetUsers.forEach((resetUser) => notifications.push({
      id: `password-reset-${resetUser.id}`,
      type: "Password reset",
      title: `ID: ${resetUser.id} | ${resetUser.username}`,
      message: `${resetUser.username} requested a password reset`,
      detail: "User Management",
      due: "",
      icon: "user",
      link: "/users",
      done: false
    }));
  }

  const reminderWhere = user.role === "admin"
    ? "deleted_at is null and coalesce(send_reminders,0) = 1"
    : "deleted_at is null and coalesce(send_reminders,0) = 1 and (owner_id = @ownerId or staff_name = @username)";
  const reminders = await db.all(`select id,first_name,last_name,phone,updated_at,referral_sent_date,referral_type,active_client from leads where ${reminderWhere} order by updated_at desc limit 8`, { ownerId: user.user_id, username: user.username });
  reminders.forEach((lead) => notifications.push({
    id: `lead-reminder-${lead.id}`,
    type: "Lead reminder",
    title: `ID: ${lead.id} | ${`${lead.first_name || ""} ${lead.last_name || ""}`.trim() || "Lead"}`,
    message: lead.active_client ? `Referral Sent: Please follow-up with this referral. (${lead.referral_type || "Regular"})${lead.phone ? ` Phone: ${lead.phone}` : ""}` : `Please follow-up with this lead.${lead.phone ? ` Phone: ${lead.phone}` : ""}`,
    detail: lead.updated_at || lead.referral_sent_date || "",
    due: lead.referral_sent_date || lead.updated_at || "",
    icon: "lead",
    link: `/view-leads?idSearch=${lead.id}`,
    done: false
  }));

  const recentActivity = await db.all("select id,description,timestamp from activity_logs order by timestamp desc limit 5", );
  recentActivity.forEach((activity) => notifications.push({
    id: `activity-${activity.id}`,
    type: "Activity",
    title: "Recent activity",
    message: activity.description || "Recent activity",
    detail: activity.timestamp || "",
    due: activity.timestamp || "",
    icon: "activity",
    link: "/activity",
    done: true
  }));

  return notifications.slice(0, 12);
}

app.get("/api/notifications", auth, async (req, res) => {
  res.json(await notificationsPayload(req.user));
});

async function notificationsPayload(user) {
  const [all, readRows] = await Promise.all([
    cached(cacheKey("notifications-base", [user.role, user.user_id, user.username]), 30_000, () => notificationRows(user)),
    db.all("select notification_id from notification_reads where user_id=?", user.user_id)
  ]);
  const readIds = new Set(readRows.map((row) => row.notification_id));
  const notifications = all.map((item) => ({ ...item, read: readIds.has(item.id) }));
  const unreadCount = notifications.filter((item) => !item.read).length;
  return { count: unreadCount, notifications, total: all.length };
}

app.get("/api/bootstrap", auth, async (req, res) => {
  const [user, lookups, notifications, activity] = await Promise.all([
    getCurrentUser(req.user.user_id),
    lookupPayload(),
    notificationsPayload(req.user),
    activityPayload(req.user, { limit: 4, offset: 0 })
  ]);
  res.json({ user: publicUser(user), lookups, notifications, activity });
});

app.post("/api/notifications/read-all", auth, async (req, res) => {
  const rows = await notificationRows(req.user);
  for (const item of rows) {
    await db.run("insert or replace into notification_reads (user_id,notification_id,read_at) values (?,?,?)", req.user.user_id, item.id, now());
  }
  res.json({ success: true, count: 0, notifications: [] });
});

app.post("/api/notifications/read", auth, async (req, res) => {
  if (!req.body.id) return res.status(400).json({ error: "Missing notification id" });
  await db.run("insert or replace into notification_reads (user_id,notification_id,read_at) values (?,?,?)", req.user.user_id, req.body.id, now());
  res.json({ success: true });
});

app.get("/api/leads", auth, async (req, res) => res.json(await listLeads(req.query, req.user)));
app.get("/api/leads/:id", auth, async (req, res) => {
  const lead = await getLead(req.params.id, true);
  if (!lead) return res.status(404).json({ error: "Lead not found" });
  const comments = await db.all("select * from lead_comments where lead_id = ? order by created_at desc", req.params.id);
  const attachments = await db.all("select * from attachments where lead_id = ? order by uploaded_at desc", req.params.id);
  res.json({ lead, comments, attachments });
});

app.get("/api/search/suggestions", auth, async (req, res) => {
  const { rows } = await listLeads({ search: req.query.q, includeDeleted: false, limit: 10 }, req.user);
  res.json({ clients: rows.map((l) => {
    const target = searchTargetForLead(l);
    const separator = target.targetUrl.includes("?") ? "&" : "?";
    return { id: l.id, name: `${l.first_name} ${l.last_name}`, phone: l.phone, ...target, targetUrl: `${target.targetUrl}${separator}globalSearch=true` };
  }) });
});

app.post("/api/leads", auth, async (req, res) => {
  const body = req.body;
  const duplicate = await findDuplicateLead(body);
  if (duplicate) {
    const kind = duplicateKind(duplicate);
    const payloadKey = duplicate.deleted_at ? "deletedDuplicate" : "duplicate";
    return res.status(409).json({ error: `Duplicate ${kind.charAt(0).toUpperCase()}${kind.slice(1)} Detected`, [payloadKey]: duplicate, duplicateKind: kind });
  }
  const fields = ["created_at","updated_at","created_by","updated_by","owner_id","staff_name","first_name","last_name","source","event_name","word_of_mouth_type","other_source_type","active_client","referral_type","agency_id","agency_suboption_id","ccu_id","authorization_received","care_status","priority","tag_color","soc_date","phone","street","city","zip_code","dob","age","gender","medicaid_no","e_contact_name","e_contact_relation","e_contact_phone","last_contact_status","comments","ssn","email","custom_user_id","state","send_reminders","caregiver_type","referral_sent_date"];
  const data = { ...body, created_at: now(), updated_at: now(), created_by: req.user.username, updated_by: req.user.username, priority: body.priority || "Not Called", tag_color: body.tag_color || null, active_client: bool(body.active_client), authorization_received: bool(body.authorization_received), send_reminders: 1, referral_sent_date: body.active_client ? (body.referral_sent_date || now().slice(0, 10)) : null };
  const sql = `insert into leads (${fields.join(",")}) values (${fields.map((f) => `@${f}`).join(",")})`;
  const result = await db.run(sql, data);
  const lead = await getLead(result.lastInsertRowid, true);
  await logActivity(req.user, "CREATE_LEAD", "Lead", lead.id, `${lead.first_name} ${lead.last_name}`, `Created lead '${lead.first_name} ${lead.last_name}'`, null, lead, "lead,create");
  res.status(201).json({ lead });
});

app.patch("/api/leads/:id", auth, async (req, res) => {
  const oldLead = await getLead(req.params.id, true);
  if (!oldLead) return res.status(404).json({ error: "Lead not found" });
  const allowed = Object.keys(req.body).filter((k) => !["id", "created_at"].includes(k));
  if (!allowed.length) return res.json({ lead: oldLead });
  const data = { ...req.body, id: req.params.id, updated_at: now(), updated_by: req.user.username };
  const sets = [...allowed, "updated_at", "updated_by"].map((k) => `${k} = @${k}`).join(",");
  await db.run(`update leads set ${sets} where id = @id`, data);
  const lead = await getLead(req.params.id, true);
  const actionType = req.body.care_status === "Care Start"
    ? "CARE_START_MARKED"
    : Number(req.body.authorization_received) === 1
      ? "AUTHORIZATION_MARKED"
      : Number(req.body.active_client) === 1 && Number(req.body.authorization_received) === 0
        ? "REFERRAL_MARKED"
        : "UPDATE_LEAD";
  const description = actionType === "CARE_START_MARKED"
    ? `Marked Care Start for '${lead.first_name} ${lead.last_name}'`
    : actionType === "AUTHORIZATION_MARKED"
      ? `Marked authorization for '${lead.first_name} ${lead.last_name}'`
      : actionType === "REFERRAL_MARKED"
        ? `Marked referral for '${lead.first_name} ${lead.last_name}'`
        : `Updated lead '${lead.first_name} ${lead.last_name}'`;
  await logActivity(req.user, actionType, "Lead", lead.id, `${lead.first_name} ${lead.last_name}`, description, oldLead, lead, "lead,update");
  res.json({ lead });
});

app.post("/api/leads/:id/soft-delete", auth, async (req, res) => {
  const lead = await getLead(req.params.id, true);
  await db.run("update leads set deleted_at=@deleted_at, deleted_by=@deleted_by, updated_at=@updated_at, updated_by=@updated_by where id=@id", { id: req.params.id, deleted_at: now(), deleted_by: req.user.username, updated_at: now(), updated_by: req.user.username });
  await logActivity(req.user, "DELETE_LEAD", "Lead", Number(req.params.id), lead ? `${lead.first_name} ${lead.last_name}` : "", "Soft deleted lead", lead, null, "lead,delete");
  res.json({ success: true });
});

app.post("/api/leads/:id/restore", auth, async (req, res) => {
  await db.run("update leads set deleted_at=null, deleted_by=null, updated_at=@updated_at, updated_by=@updated_by where id=@id", { id: req.params.id, updated_at: now(), updated_by: req.user.username });
  const lead = await getLead(req.params.id, true);
  await logActivity(req.user, "RESTORE_LEAD", "Lead", lead.id, `${lead.first_name} ${lead.last_name}`, "Restored lead", null, lead, "lead,restore");
  res.json({ lead });
});

app.delete("/api/leads/:id", auth, admin, async (req, res) => {
  await db.run("delete from leads where id = ?", req.params.id);
  await logActivity(req.user, "PERMANENT_DELETE", "Lead", Number(req.params.id), "", "Permanently deleted lead", null, null, "lead,delete");
  res.json({ success: true });
});

app.post("/api/leads/:id/comment", auth, async (req, res) => {
  const result = await db.run("insert into lead_comments (lead_id,username,content,created_at) values (?,?,?,?)", req.params.id, req.user.username, req.body.content, now());
  await logActivity(req.user, "ADD_COMMENT", "Lead", Number(req.params.id), "", "Added comment", null, { content: req.body.content }, "lead,comment");
  res.status(201).json({ comment: await db.get("select * from lead_comments where id=?", result.lastInsertRowid) });
});

app.post("/api/leads/:id/attachment", auth, upload.single("file"), async (req, res) => {
  const safeName = `${req.params.id}_${req.file.originalname}`;
  const finalPath = path.join(uploadsDir, safeName);
  fs.renameSync(req.file.path, finalPath);
  const result = await db.run("insert into attachments (lead_id,filename,file_path,file_size,uploaded_by,uploaded_at) values (?,?,?,?,?,?)", req.params.id, req.file.originalname, finalPath, req.file.size, req.user.username, now());
  const attachment = await db.get("select * from attachments where id=?", result.lastInsertRowid);
  await logActivity(req.user, "UPLOAD_ATTACHMENT", "Lead", Number(req.params.id), req.file.originalname, `Uploaded attachment '${req.file.originalname}'`, null, attachment, "lead,attachment,upload");
  res.status(201).json({ attachment });
});

app.get("/api/attachments/:id/preview", auth, async (req, res) => {
  const att = await db.get("select * from attachments where id=?", req.params.id);
  if (!att || !fs.existsSync(att.file_path)) return res.status(404).json({ error: "File not found" });
  res.type(att.filename);
  res.setHeader("Content-Disposition", `inline; filename="${encodeURIComponent(att.filename)}"`);
  res.sendFile(path.resolve(att.file_path));
});

app.get("/api/attachments/:id/download", auth, async (req, res) => {
  const att = await db.get("select * from attachments where id=?", req.params.id);
  if (!att || !fs.existsSync(att.file_path)) return res.status(404).json({ error: "File not found" });
  res.download(att.file_path, att.filename);
});

app.delete("/api/attachments/:id", auth, admin, async (req, res) => {
  const att = await db.get("select * from attachments where id=?", req.params.id);
  if (att && fs.existsSync(att.file_path)) fs.unlinkSync(att.file_path);
  await db.run("delete from attachments where id=?", req.params.id);
  await logActivity(req.user, "DELETE_ATTACHMENT", "Lead", att?.lead_id || null, att?.filename || "", `Deleted attachment '${att?.filename || req.params.id}'`, att, null, "lead,attachment,delete");
  res.json({ success: true });
});

app.get("/api/activity", auth, async (req, res) => {
  res.json(await activityPayload(req.user, req.query));
});

app.get("/api/leads/:id/history", auth, async (req, res) => {
  res.json({ rows: await db.all("select * from activity_logs where entity_type='Lead' and entity_id=? order by timestamp desc limit 20", req.params.id) });
});

async function dashboardPayload(user, query = {}) {
  const includeUsers = query.includeUsers === "true" || query.includeUsers === true;
  const isCumulative = user.role === "admin" || query.mode === "cumulative";
  const cacheScope = isCumulative ? "all" : `user-${user.user_id}-${user.username}`;
  return cached(cacheKey("dashboard", [cacheScope, includeUsers ? "users" : "base"]), includeUsers ? 60_000 : 120_000, async () => {
  const leadRows = await db.all(`${leadSelect} where leads.deleted_at is null`, );
  const visible = isCumulative ? leadRows : leadRows.filter((l) => l.staff_name === user.username || l.owner_id === user.user_id);
  const hydrate = (row) => ({
    ...row,
    full_name: `${row.first_name || ""} ${row.last_name || ""}`.trim(),
    month: String(row.created_at || "").slice(0, 7) || "N/A",
    ccu_name: row.ccu_name || "N/A",
    agency_name: row.agency_name || "N/A",
    auth_label: row.authorization_received ? "Authorized" : "Pending",
    referral_label: row.active_client ? "Referrals" : "Pending"
  });
  const rows = visible.map(hydrate);
  const group = (key, sourceRows = rows) => Object.values(sourceRows.reduce((acc, row) => {
    const name = row[key] || "N/A";
    acc[name] = acc[name] || { name, count: 0, rowIds: [] };
    acc[name].count += 1;
    acc[name].rowIds.push(row.id);
    return acc;
  }, {})).sort((a, b) => b.count - a.count || String(a.name).localeCompare(String(b.name)));
  const only = (predicate) => rows.filter(predicate);
  const referrals = only((l) => Number(l.active_client) === 1);
  const pendingLeads = only((l) => Number(l.active_client) !== 1);
  const careStart = referrals.filter((l) => l.care_status === "Care Start");
  const notStart = referrals.filter((l) => l.care_status === "Not Start");
  const pendingCare = referrals.filter((l) => !["Care Start", "Not Start"].includes(l.care_status));
  const [totalUsersRow, approvedUsers] = await Promise.all([
    db.get("select count(*) as count from users", ),
    includeUsers ? db.all("select id,user_id,username,email,role from users where is_approved = 1 order by username", ) : Promise.resolve([])
  ]);
  const userDashboards = includeUsers ? approvedUsers.map((u) => {
    const userRows = rows.filter((l) => l.staff_name === u.username || l.owner_id === u.id);
    return {
      user: u,
      stats: { total_leads: userRows.length, referrals: userRows.filter((l) => Number(l.active_client) === 1).length },
      source: group("source", userRows),
      status: group("last_contact_status", userRows),
      rowIds: userRows.map((row) => row.id)
    };
  }) : [];
  return {
    stats: {
      total_leads: rows.length,
      total_users: totalUsersRow?.count || 0,
      active_clients: referrals.length
    },
    charts: {
      staff: group("staff_name"),
      source: group("source"),
      status: group("last_contact_status"),
      month: group("month"),
      event: group("event_name", rows.filter((l) => l.source === "Event")),
      wordOfMouth: group("word_of_mouth_type", rows.filter((l) => l.source === "Word of Mouth")),
      priority: group("priority"),
      auth: group("auth_label"),
      ccuSent: group("ccu_name", referrals),
      ccuConfirmed: group("ccu_name", referrals.filter((l) => l.care_status === "Care Start" || Number(l.authorization_received) === 1)),
      referralConfirmation: [
        { name: "Referrals", count: referrals.length, rowIds: referrals.map((row) => row.id) },
        { name: "Pending", count: pendingLeads.length, rowIds: pendingLeads.map((row) => row.id) }
      ],
      leadConversion: [
        { name: "Care Start", count: careStart.length, rowIds: careStart.map((row) => row.id) },
        { name: "Not Start", count: notStart.length, rowIds: notStart.map((row) => row.id) },
        { name: "Pending", count: pendingCare.length, rowIds: pendingCare.map((row) => row.id) }
      ]
    },
    rates: {
      confirmation: rows.length ? (referrals.length / rows.length) * 100 : 0,
      conversion: referrals.length ? (careStart.length / referrals.length) * 100 : 0
    },
    rows,
    userDashboards
  };
  });
}

app.get("/api/dashboard", auth, async (req, res) => {
  res.json(await dashboardPayload(req.user, req.query));
});

app.get("/api/reports/export", auth, async (req, res) => {
  const { rows } = await listLeads({ ...req.query, limit: 2000 }, req.user);
  if (req.query.format === "word") {
    const tableColumns = [
      { header: "ID", key: "id", width: 900 },
      { header: "Name", key: "name", width: 2800 },
      { header: "Staff", key: "staff_name", width: 2200 },
      { header: "Source", key: "source", width: 2400 },
      { header: "Status", key: "last_contact_status", width: 2500 },
      { header: "Phone", key: "phone", width: 1900 }
    ];
    const wordRows = rows.map((lead) => ({
      id: lead.id,
      name: `${lead.first_name || ""} ${lead.last_name || ""}`.trim(),
      staff_name: lead.staff_name,
      source: lead.source,
      last_contact_status: lead.last_contact_status,
      phone: lead.phone
    }));
    const headerRow = new TableRow({
      children: tableColumns.map((column) => new TableCell({
        width: { size: column.width, type: WidthType.DXA },
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: column.header, bold: true, size: 22 })]
        })]
      }))
    });
    const dataRows = wordRows.map((row) => new TableRow({
      children: tableColumns.map((column) => new TableCell({
        width: { size: column.width, type: WidthType.DXA },
        children: [new Paragraph({
          children: [new TextRun({ text: String(row[column.key] || "N/A"), size: 20 })]
        })]
      }))
    }));
    const doc = new Document({
      sections: [{
        properties: {
          page: {
            margin: { top: 720, right: 720, bottom: 720, left: 720 },
            size: { orientation: PageOrientation.LANDSCAPE }
          }
        },
        children: [
          new Paragraph({
            spacing: { after: 180 },
            children: [new TextRun({ text: "Lead Manager Report", bold: true, size: 34 })]
          }),
          new Paragraph({
            spacing: { after: 240 },
            children: [new TextRun({
              text: `Generated ${new Date().toLocaleString()} | Total records: ${wordRows.length}`,
              size: 20
            })]
          }),
          new Table({
            width: { size: 100, type: WidthType.PERCENTAGE },
            layout: TableLayoutType.FIXED,
            rows: [headerRow, ...dataRows]
          })
        ]
      }]
    });
    const buffer = await Packer.toBuffer(doc);
    res.setHeader("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
    res.setHeader("Content-Disposition", `attachment; filename=lead_report_${Date.now()}.docx`);
    return res.send(buffer);
  }
  const workbook = new ExcelJS.Workbook();
  const sheet = workbook.addWorksheet("Leads");
  sheet.columns = ["ID", "First Name", "Last Name", "Staff", "Source", "Status", "Call Status", "Phone", "Email", "CCU", "Payor", "Created", "Updated"].map((h) => ({ header: h, key: h, width: 20 }));
  rows.forEach((l) => sheet.addRow({ "ID": l.id, "First Name": l.first_name, "Last Name": l.last_name, "Staff": l.staff_name, "Source": l.source, "Status": l.last_contact_status, "Call Status": l.priority, "Phone": l.phone, "Email": l.email, "CCU": l.ccu_name, "Payor": l.agency_name, "Created": l.created_at, "Updated": l.updated_at }));
  const buffer = await workbook.xlsx.writeBuffer();
  res.setHeader("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
  res.setHeader("Content-Disposition", `attachment; filename=leads_export_${Date.now()}.xlsx`);
  res.send(buffer);
});

app.post("/api/reports/word", auth, async (req, res) => {
  const title = String(req.body?.title || "Lead Manager Report");
  const rows = Array.isArray(req.body?.rows) ? req.body.rows : [];
  const columns = Object.keys(rows[0] || { Empty: "" });
  const width = Math.floor(14000 / Math.max(columns.length, 1));
  const headerRow = new TableRow({
    children: columns.map((column) => new TableCell({
      width: { size: width, type: WidthType.DXA },
      children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: column, bold: true, size: 22 })]
      })]
    }))
  });
  const dataRows = rows.map((row) => new TableRow({
    children: columns.map((column) => new TableCell({
      width: { size: width, type: WidthType.DXA },
      children: [new Paragraph({
        children: [new TextRun({ text: String(row[column] ?? "N/A"), size: 20 })]
      })]
    }))
  }));
  const doc = new Document({
    sections: [{
      properties: {
        page: {
          margin: { top: 720, right: 720, bottom: 720, left: 720 },
          size: { orientation: PageOrientation.LANDSCAPE }
        }
      },
      children: [
        new Paragraph({
          spacing: { after: 180 },
          children: [new TextRun({ text: title, bold: true, size: 34 })]
        }),
        new Paragraph({
          spacing: { after: 240 },
          children: [new TextRun({
            text: `Generated ${new Date().toLocaleString()} | Total records: ${rows.length}`,
            size: 20
          })]
        }),
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          layout: TableLayoutType.FIXED,
          rows: [headerRow, ...dataRows]
        })
      ]
    }]
  });
  const buffer = await Packer.toBuffer(doc);
  res.setHeader("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
  res.setHeader("Content-Disposition", `attachment; filename=${title.toLowerCase().replace(/[^a-z0-9]+/gi, "_")}.docx`);
  res.send(buffer);
});

app.patch("/api/users/:id", auth, async (req, res, next) => {
  if (req.params.id === "me") return next();
  if (req.user.role !== "admin") return res.status(403).json({ error: "Admin only" });
  const oldUser = await db.get("select * from users where id=?", req.params.id);
  const allowed = ["username", "role", "is_approved", "password_reset_requested", "email", "user_id", "profile_pic"];
  const keys = Object.keys(req.body).filter((k) => allowed.includes(k));
  if (!keys.length) return res.json({ success: true });
  await db.run(`update users set ${keys.map((k) => `${k}=@${k}`).join(",")} where id=@id`, { ...req.body, id: req.params.id });
  const updatedUser = await db.get("select * from users where id=?", req.params.id);
  await logActivity(req.user, req.body.is_approved === 1 && oldUser?.is_approved !== 1 ? "USER_APPROVED" : "UPDATE_USER", "User", Number(req.params.id), updatedUser?.username || "", `Updated user '${updatedUser?.username || req.params.id}'`, publicUser(oldUser), publicUser(updatedUser), "user,update");
  res.json({ user: publicUser(updatedUser, { profile: true }) });
});

app.patch("/api/users/me", auth, async (req, res) => {
  const allowed = ["username", "email", "user_id", "profile_pic"];
  const keys = Object.keys(req.body).filter((k) => allowed.includes(k));
  if (!keys.length) return res.json({ user: publicUser(await db.get("select * from users where id=?", req.user.user_id), { profile: true }) });
  const oldUser = await db.get("select * from users where id=?", req.user.user_id);
  await db.run(`update users set ${keys.map((k) => `${k}=@${k}`).join(",")} where id=@id`, { ...req.body, id: req.user.user_id });
  const user = await db.get("select * from users where id=?", req.user.user_id);
  await logActivity(req.user, "UPDATE_PROFILE", "User", req.user.user_id, user?.username || req.user.username, `Updated profile for '${user?.username || req.user.username}'`, publicUser(oldUser), publicUser(user), "user,profile,update");
  res.json({ user: publicUser(user, { profile: true }) });
});

app.post("/api/users/me/password", auth, async (req, res) => {
  const { currentPassword, newPassword } = req.body;
  const user = await db.get("select * from users where id=?", req.user.user_id);
  if (!user || !verifyPassword(currentPassword || "", user.hashed_password)) return res.status(400).json({ error: "Current password is incorrect" });
  if (!newPassword || String(newPassword).length < 6) return res.status(400).json({ error: "Password must be at least 6 characters" });
  await db.run("update users set hashed_password=?, password_reset_requested=0 where id=?", hashPassword(newPassword), req.user.user_id);
  await logActivity(req.user, "PASSWORD_CHANGED", "User", req.user.user_id, user.username, `Password changed for '${user.username}'`, null, null, "user,password");
  res.json({ success: true });
});

app.post("/api/users/me/request-reset", auth, async (req, res) => {
  await db.run("update users set password_reset_requested=1 where id=?", req.user.user_id);
  await logActivity(req.user, "PASSWORD_RESET_REQUESTED", "User", req.user.user_id, req.user.username, `Password reset requested by '${req.user.username}'`, null, null, "user,password,reset");
  res.json({ success: true });
});

app.post("/api/users", auth, admin, async (req, res) => {
  const { user_id, username, email, password, role } = req.body;
  if (!user_id || !username || !email || !password) return res.status(400).json({ error: "Please fill in all required fields" });
  if (await db.get("select id from users where user_id=? or username=? or email=?", user_id, username, email)) return res.status(409).json({ error: "User ID, username, or email already exists" });
  const result = await db.run("insert into users (user_id,username,email,hashed_password,role,is_approved,password_reset_requested,created_at) values (?,?,?,?,?,?,?,?)", user_id, username, email, hashPassword(password), role || "user", 1, 0, now());
  const createdUser = await db.get("select * from users where id=?", result.lastInsertRowid);
  await logActivity(req.user, "CREATE_USER", "User", createdUser.id, createdUser.username, `Created user '${createdUser.username}'`, null, publicUser(createdUser), "user,create");
  res.status(201).json({ user: publicUser(createdUser) });
});

app.post("/api/users/:id/reset-password", auth, admin, async (req, res) => {
  if (!req.body.password || String(req.body.password).length < 6) return res.status(400).json({ error: "Password must be at least 6 characters" });
  const targetUser = await db.get("select * from users where id=?", req.params.id);
  await db.run("update users set hashed_password=?, password_reset_requested=0 where id=?", hashPassword(req.body.password), req.params.id);
  await logActivity(req.user, "PASSWORD_RESET", "User", Number(req.params.id), targetUser?.username || "", `Reset password for '${targetUser?.username || req.params.id}'`, null, null, "user,password,reset");
  res.json({ success: true });
});

app.delete("/api/users/:id", auth, admin, async (req, res) => {
  const deletedUser = await db.get("select * from users where id=?", req.params.id);
  await db.run("delete from users where id=?", req.params.id);
  await logActivity(req.user, "DELETE_USER", "User", Number(req.params.id), deletedUser?.username || "", `Deleted user '${deletedUser?.username || req.params.id}'`, publicUser(deletedUser), null, "user,delete");
  res.json({ success: true });
});

app.post("/api/admin/:type", auth, admin, async (req, res) => {
  const table = { event: "events", agency: "agencies", ccu: "ccus" }[req.params.type];
  if (!table) return res.status(400).json({ error: "Bad type" });
  if (table === "events") await db.run("insert into events (event_name,created_at,created_by) values (?,?,?)", req.body.name, now(), req.user.username);
  if (table === "agencies") await db.run("insert into agencies (name,address,phone,fax,email,created_at,created_by) values (@name,@address,@phone,@fax,@email,@created_at,@created_by)", { ...req.body, created_at: now(), created_by: req.user.username });
  if (table === "ccus") await db.run("insert into ccus (name,street,city,state,zip_code,phone,fax,email,care_coordinator_name,created_at,created_by) values (@name,@street,@city,@state,@zip_code,@phone,@fax,@email,@care_coordinator_name,@created_at,@created_by)", { ...req.body, created_at: now(), created_by: req.user.username });
  await logActivity(req.user, `CREATE_${req.params.type.toUpperCase()}`, req.params.type === "agency" ? "Payor" : req.params.type.toUpperCase(), null, req.body.name || "", `Created ${req.params.type} '${req.body.name || ""}'`, null, req.body, `${req.params.type},create`);
  res.status(201).json({ success: true });
});

app.post("/api/ccus", auth, async (req, res) => {
  if (!req.body.name) return res.status(400).json({ error: "CCU name is required" });
  if (await db.get("select id from ccus where lower(name)=lower(?)", req.body.name)) return res.status(409).json({ error: "CCU already exists" });
  await db.run("insert into ccus (name,street,city,state,zip_code,phone,fax,email,care_coordinator_name,created_at,created_by) values (@name,@street,@city,@state,@zip_code,@phone,@fax,@email,@care_coordinator_name,@created_at,@created_by)", {
    ...req.body,
    created_at: now(),
    created_by: req.user.username
  });
  await logActivity(req.user, "CREATE_CCU", "CCU", null, req.body.name, `Created CCU '${req.body.name}'`, null, req.body, "ccu,create");
  res.status(201).json({ success: true });
});

app.patch("/api/agencies/:id", auth, async (req, res) => {
  const allowed = ["name", "address", "phone", "fax", "email"];
  const keys = Object.keys(req.body).filter((key) => allowed.includes(key));
  if (!keys.length) return res.json({ success: true });
  const oldAgency = await db.get("select * from agencies where id=?", req.params.id);
  await db.run(`update agencies set ${keys.map((key) => `${key}=@${key}`).join(",")} where id=@id`, { ...req.body, id: req.params.id });
  const agency = await db.get("select * from agencies where id=?", req.params.id);
  await logActivity(req.user, "UPDATE_PAYOR", "Payor", Number(req.params.id), agency?.name || "", `Updated payor '${agency?.name || req.params.id}'`, oldAgency, agency, "payor,update");
  res.json({ success: true });
});

app.patch("/api/ccus/:id", auth, async (req, res) => {
  const allowed = ["name", "street", "city", "state", "zip_code", "phone", "fax", "email", "care_coordinator_name"];
  const keys = Object.keys(req.body).filter((key) => allowed.includes(key));
  if (!keys.length) return res.json({ success: true });
  const oldCcu = await db.get("select * from ccus where id=?", req.params.id);
  await db.run(`update ccus set ${keys.map((key) => `${key}=@${key}`).join(",")} where id=@id`, { ...req.body, id: req.params.id });
  const ccu = await db.get("select * from ccus where id=?", req.params.id);
  await logActivity(req.user, "UPDATE_CCU", "CCU", Number(req.params.id), ccu?.name || "", `Updated CCU '${ccu?.name || req.params.id}'`, oldCcu, ccu, "ccu,update");
  res.json({ success: true });
});

app.get("/api/ccus/duplicates", auth, admin, async (req, res) => {
  const ccus = await db.all("select * from ccus order by lower(trim(name)), id", );
  const leadCounts = await db.all("select ccu_id, count(*) as count from leads where ccu_id is not null group by ccu_id", );
  const countById = Object.fromEntries(leadCounts.map((row) => [String(row.ccu_id), row.count]));
  const groups = Object.values(ccus.reduce((acc, ccu) => {
    const key = String(ccu.name || "").trim().toLowerCase().replace(/\s+/g, " ");
    if (!key) return acc;
    if (!acc[key]) acc[key] = { key, name: ccu.name, items: [] };
    acc[key].items.push({ ...ccu, lead_count: countById[String(ccu.id)] || 0 });
    return acc;
  }, {})).filter((group) => group.items.length > 1);
  res.json({ groups });
});

app.post("/api/ccus/merge", auth, admin, async (req, res) => {
  const masterId = Number(req.body.masterId);
  const duplicateIds = [...new Set((req.body.duplicateIds || []).map(Number).filter((id) => Number.isInteger(id) && id > 0 && id !== masterId))];
  if (!masterId || !duplicateIds.length) return res.status(400).json({ error: "Choose a master CCU and at least one duplicate CCU" });
  const master = await db.get("select * from ccus where id=?", masterId);
  if (!master) return res.status(404).json({ error: "Master CCU not found" });
  const duplicates = (await Promise.all(duplicateIds.map((id) => db.get("select * from ccus where id=?", id)))).filter(Boolean);
  if (duplicates.length !== duplicateIds.length) return res.status(404).json({ error: "One or more duplicate CCUs were not found" });
  const updated = await db.run(`update leads set ccu_id=@masterId, updated_at=@updated_at, updated_by=@updated_by where ccu_id in (${duplicateIds.map((_, i) => `@id${i}`).join(",")})`, {
    masterId,
    updated_at: now(),
    updated_by: req.user.username,
    ...Object.fromEntries(duplicateIds.map((id, i) => [`id${i}`, id]))
  });
  for (const id of duplicateIds) await db.run("delete from ccus where id=?", id);
  await logActivity(req.user, "MERGE_CCU", "CCU", masterId, master.name, `Merged ${duplicates.length} duplicate CCU record(s) into '${master.name}'`, duplicates, { master, duplicateIds, leadsUpdated: updated.changes || 0 }, "ccu,merge,cleanup");
  res.json({ success: true, master, merged: duplicates, leadsUpdated: updated.changes || 0 });
});

app.delete("/api/admin/:type/:id", auth, admin, async (req, res) => {
  const table = { event: "events", agency: "agencies", ccu: "ccus" }[req.params.type];
  if (!table) return res.status(400).json({ error: "Bad type" });
  const nameColumn = table === "events" ? "event_name" : "name";
  const oldItem = await db.get(`select * from ${table} where id=?`, req.params.id);
  await db.run(`delete from ${table} where id=?`, req.params.id);
  await logActivity(req.user, `DELETE_${req.params.type.toUpperCase()}`, req.params.type === "agency" ? "Payor" : req.params.type.toUpperCase(), Number(req.params.id), oldItem?.[nameColumn] || "", `Deleted ${req.params.type} '${oldItem?.[nameColumn] || req.params.id}'`, oldItem, null, `${req.params.type},delete`);
  res.json({ success: true });
});

function spaHtml() {
  const indexPath = path.join(distDir, "index.html");
  let html = fs.readFileSync(indexPath, "utf8");
  const scripts = [];
  html = html.replace(/\s*<script\b[^>]*\bsrc="[^"]+"[^>]*><\/script>/g, (tag) => {
    scripts.push(tag.trim());
    return "";
  });
  if (scripts.length) html = html.replace("</body>", `${scripts.join("\n")}\n</body>`);
  return html;
}

app.use("/uploads", auth, express.static(uploadsDir));
app.use(express.static(distDir, {
  index: false,
  setHeaders(res, filePath) {
    if (/\.(js|css|png|jpg|jpeg|svg|webp|woff2?)$/i.test(filePath)) {
      res.setHeader("Cache-Control", "public, max-age=2592000, immutable");
    }
  }
}));
app.use((req, res, next) => {
  if (req.path.startsWith("/api/")) return next();
  res.type("html").send(spaHtml());
});
const server = app.listen(process.env.PORT || 3001, "0.0.0.0", () => console.log(`Lead Manager API running on http://localhost:${process.env.PORT || 3001}`));
server.on("error", (error) => console.error("API server error:", error));
setInterval(() => {}, 1 << 30);
