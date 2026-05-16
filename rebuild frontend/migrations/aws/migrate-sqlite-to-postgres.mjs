import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import initSqlJs from "sql.js";
import pg from "pg";

const { Pool } = pg;
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appDir = path.resolve(__dirname, "../..");
const repoDir = path.resolve(appDir, "..");
const defaultSqlitePath = path.join(repoDir, "backend", "leads.db");
const schemaPath = path.join(__dirname, "postgres-schema.sql");

const args = new Set(process.argv.slice(2));
const reset = args.has("--reset");
const apply = args.has("--apply");
const sqlitePath = process.env.SQLITE_DB || defaultSqlitePath;
const databaseUrl = process.env.DATABASE_URL;

const orderedTables = [
  "users",
  "events",
  "agencies",
  "agency_suboptions",
  "ccus",
  "mcos",
  "leads",
  "activity_logs",
  "lead_comments",
  "attachments",
  "email_reminders",
  "email_templates",
  "session_tokens",
  "magic_link_tokens",
  "notifications",
  "notification_reads"
];

const booleanColumns = new Map([
  ["users", ["is_approved", "password_reset_requested"]],
  ["leads", ["active_client", "authorization_received", "send_reminders"]],
  ["magic_link_tokens", ["is_used"]],
  ["notifications", ["is_read"]]
]);

function usage() {
  console.log(`
SQLite to PostgreSQL migration

Required:
  DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DB

Optional:
  SQLITE_DB=/absolute/path/to/leads.db

Commands:
  npm run migrate:aws:check
  DATABASE_URL=... npm run migrate:aws -- --apply
  DATABASE_URL=... npm run migrate:aws -- --apply --reset

Safety:
  Without --apply, the script only checks source data.
  Without --reset, the script refuses to import into non-empty AWS tables.
`);
}

function assertReady() {
  if (!fs.existsSync(sqlitePath)) throw new Error(`SQLite DB not found: ${sqlitePath}`);
  if (!fs.existsSync(schemaPath)) throw new Error(`Schema file not found: ${schemaPath}`);
  if (apply && !databaseUrl) throw new Error("DATABASE_URL is required when using --apply");
  if (apply && !databaseUrl.startsWith("postgres")) throw new Error("DATABASE_URL must be a PostgreSQL URL");
}

function backupSqlite() {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const backupPath = `${sqlitePath}.backup-${stamp}`;
  fs.copyFileSync(sqlitePath, backupPath);
  return backupPath;
}

function sqliteAll(db, sql, params = []) {
  const stmt = db.prepare(sql);
  try {
    stmt.bind(params);
    const rows = [];
    while (stmt.step()) rows.push(stmt.getAsObject());
    return rows;
  } finally {
    stmt.free();
  }
}

function quoteIdent(name) {
  return `"${String(name).replaceAll('"', '""')}"`;
}

function normalizeValue(table, column, value) {
  if (value === undefined) return null;
  if (booleanColumns.get(table)?.includes(column)) return value === true || value === 1 || value === "1" ? 1 : 0;
  return value;
}

function tableColumns(db, table) {
  return sqliteAll(db, `pragma table_info(${quoteIdent(table)})`).map((row) => row.name);
}

function tableExists(db, table) {
  return tableColumns(db, table).length > 0;
}

function tableCount(db, table) {
  if (!tableExists(db, table)) return 0;
  return sqliteAll(db, `select count(*) as count from ${quoteIdent(table)}`)[0]?.count || 0;
}

async function pgCount(client, table) {
  const result = await client.query(`select count(*)::int as count from ${quoteIdent(table)}`);
  return result.rows[0]?.count || 0;
}

async function resetIdentity(client, table) {
  const result = await client.query(`select max(id)::int as max_id from ${quoteIdent(table)}`);
  const maxId = result.rows[0]?.max_id || 0;
  await client.query(`select setval(pg_get_serial_sequence($1, 'id'), $2, true)`, [table, Math.max(maxId, 1)]);
}

async function ensureDestinationEmpty(client) {
  const counts = {};
  for (const table of orderedTables) counts[table] = await pgCount(client, table);
  const nonEmpty = Object.entries(counts).filter(([, count]) => count > 0);
  if (nonEmpty.length && !reset) {
    throw new Error(`AWS database is not empty. Non-empty tables: ${nonEmpty.map(([table, count]) => `${table}=${count}`).join(", ")}. Re-run with --reset only after confirming backups.`);
  }
}

async function clearDestination(client) {
  await client.query(`truncate table ${[...orderedTables].reverse().map(quoteIdent).join(", ")} restart identity cascade`);
}

async function insertTable(client, db, table) {
  const columns = tableColumns(db, table);
  if (!columns.length) return 0;
  const rows = sqliteAll(db, `select ${columns.map(quoteIdent).join(", ")} from ${quoteIdent(table)}`);
  if (!rows.length) return 0;

  const columnSql = columns.map(quoteIdent).join(", ");
  const placeholders = columns.map((_, i) => `$${i + 1}`).join(", ");
  const insertSql = `insert into ${quoteIdent(table)} (${columnSql}) values (${placeholders})`;

  for (const row of rows) {
    const values = columns.map((column) => normalizeValue(table, column, row[column]));
    await client.query(insertSql, values);
  }
  return rows.length;
}

async function main() {
  usage();
  assertReady();

  const SQL = await initSqlJs();
  const sqliteBytes = fs.readFileSync(sqlitePath);
  const sqliteDb = new SQL.Database(sqliteBytes);

  const sourceCounts = Object.fromEntries(orderedTables.map((table) => [table, tableCount(sqliteDb, table)]));
  console.log("Source SQLite:", sqlitePath);
  console.table(sourceCounts);

  if (!apply) {
    console.log("Check complete. No AWS changes were made. Add --apply to migrate.");
    return;
  }

  const backupPath = backupSqlite();
  console.log(`Local source backup created: ${backupPath}`);

  const pool = new Pool({ connectionString: databaseUrl, ssl: process.env.PGSSL === "false" ? false : { rejectUnauthorized: false } });
  const client = await pool.connect();
  try {
    await client.query("begin");
    await client.query(fs.readFileSync(schemaPath, "utf8"));
    await ensureDestinationEmpty(client);
    if (reset) await clearDestination(client);

    const inserted = {};
    for (const table of orderedTables) {
      inserted[table] = await insertTable(client, sqliteDb, table);
      if (table !== "notification_reads" && table !== "agency_suboptions") {
        const columns = tableColumns(sqliteDb, table);
        if (columns.includes("id")) await resetIdentity(client, table);
      }
    }

    const destinationCounts = {};
    for (const table of orderedTables) destinationCounts[table] = await pgCount(client, table);

    const mismatches = orderedTables.filter((table) => sourceCounts[table] !== destinationCounts[table]);
    console.log("Inserted rows:");
    console.table(inserted);
    console.log("Destination PostgreSQL:");
    console.table(destinationCounts);

    if (mismatches.length) {
      throw new Error(`Migration count mismatch: ${mismatches.map((table) => `${table} source=${sourceCounts[table]} destination=${destinationCounts[table]}`).join(", ")}`);
    }

    await client.query("commit");
    console.log("Migration complete. AWS PostgreSQL row counts match the local SQLite source.");
  } catch (error) {
    await client.query("rollback");
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
