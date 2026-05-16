import fs from "fs";
import path from "path";
import initSqlJs from "sql.js";
import pg from "pg";

const { Pool } = pg;
const mutateSql = /^\s*(insert|update|delete|replace|create|drop|alter)/i;

function sqliteParamKey(key) {
  return key.startsWith("$") ? key : `$${key}`;
}

function normalizeSqliteParams(params) {
  if (params === undefined || params === null) return [];
  if (Array.isArray(params)) return params;
  if (typeof params !== "object") return [params];
  return Object.fromEntries(Object.entries(params).map(([key, value]) => [sqliteParamKey(key), value]));
}

function normalizeSqliteSql(sql) {
  return sql.replace(/@([A-Za-z_][A-Za-z0-9_]*)/g, "$$$1");
}

function normalizePgParams(sql, params) {
  const values = [];
  const namedIndexes = new Map();
  let index = 0;
  const source = Array.isArray(params) ? params : params === undefined || params === null ? [] : typeof params === "object" ? params : [params];

  const text = sql
    .replace(/\?/g, () => {
      if (!Array.isArray(source)) throw new Error("Positional SQL placeholders require array parameters");
      values.push(source[index++]);
      return `$${values.length}`;
    })
    .replace(/@([A-Za-z_][A-Za-z0-9_]*)/g, (_match, key) => {
      if (Array.isArray(source)) {
        values.push(source[index++]);
        return `$${values.length}`;
      }
      if (!namedIndexes.has(key)) {
        values.push(source[key]);
        namedIndexes.set(key, values.length);
      }
      return `$${namedIndexes.get(key)}`;
    });

  return { text, values };
}

function normalizePgSql(sql) {
  return sql
    .replace(/insert\s+or\s+replace\s+into\s+notification_reads\s*\(([^)]+)\)\s*values\s*\(([^)]+)\)/i, "insert into notification_reads ($1) values ($2) on conflict (user_id, notification_id) do update set read_at = excluded.read_at");
}

function shouldReturnId(sql) {
  return /^\s*insert\s+into\s+/i.test(sql)
    && !/\breturning\b/i.test(sql)
    && !/notification_reads/i.test(sql);
}

export async function createDatabase({ dbPath, schemaPath } = {}) {
  const databaseUrl = process.env.DATABASE_URL;
  if (databaseUrl?.startsWith("postgres")) {
    const pool = new Pool({
      connectionString: databaseUrl,
      ssl: process.env.PGSSL === "false" ? false : { rejectUnauthorized: false }
    });
    if (schemaPath && fs.existsSync(schemaPath)) {
      await pool.query(fs.readFileSync(schemaPath, "utf8"));
    }
    return {
      mode: "postgres",
      async all(sql, ...args) {
        const params = args.length === 1 ? args[0] : args.length ? args : undefined;
        const normalized = normalizePgParams(normalizePgSql(sql), params);
        const result = await pool.query(normalized.text, normalized.values);
        return result.rows;
      },
      async get(sql, ...args) {
        const rows = await this.all(sql, ...args);
        return rows[0];
      },
      async run(sql, ...args) {
        const params = args.length === 1 ? args[0] : args;
        const sqlText = shouldReturnId(sql) ? `${sql} returning id` : sql;
        const normalized = normalizePgParams(normalizePgSql(sqlText), params);
        const result = await pool.query(normalized.text, normalized.values);
        return { lastInsertRowid: result.rows[0]?.id || 0, changes: result.rowCount || 0 };
      },
      async close() {
        await pool.end();
      }
    };
  }

  const SQL = await initSqlJs();
  const rawDb = new SQL.Database(fs.readFileSync(dbPath));
  const saveDb = () => fs.writeFileSync(dbPath, Buffer.from(rawDb.export()));

  return {
    mode: "sqlite",
    rawDb,
    all(sql, ...args) {
      const params = args.length === 1 ? args[0] : args.length ? args : undefined;
      const stmt = rawDb.prepare(normalizeSqliteSql(sql));
      try {
        if (params !== undefined) stmt.bind(normalizeSqliteParams(params));
        const rows = [];
        while (stmt.step()) rows.push(stmt.getAsObject());
        return rows;
      } finally {
        stmt.free();
      }
    },
    get(sql, ...args) {
      return this.all(sql, ...args)[0];
    },
    run(sql, ...args) {
      const params = args.length === 1 ? args[0] : args;
      rawDb.run(normalizeSqliteSql(sql), normalizeSqliteParams(params));
      const lastInsertRowid = rawDb.exec("select last_insert_rowid() as id")[0]?.values?.[0]?.[0] || 0;
      const changes = typeof rawDb.getRowsModified === "function" ? rawDb.getRowsModified() : 0;
      if (mutateSql.test(sql)) saveDb();
      return { lastInsertRowid, changes };
    },
    exec(sql) {
      rawDb.run(sql);
      if (mutateSql.test(sql)) saveDb();
    },
    columns(table) {
      return rawDb.exec(`pragma table_info(${table})`)[0]?.values?.map((row) => row[1]) || [];
    },
    close() {}
  };
}
