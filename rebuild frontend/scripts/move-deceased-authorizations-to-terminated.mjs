import path from "path";
import dotenv from "dotenv";
import { fileURLToPath } from "url";
import { createDatabase } from "../server/db.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, "..");
const rootDir = path.resolve(frontendDir, "..");

dotenv.config({ path: path.join(rootDir, ".env") });
dotenv.config({ path: path.join(frontendDir, ".env") });

const dbPath = process.env.LEAD_DB || path.join(rootDir, "backend", "leads.db");
const schemaPath = path.join(frontendDir, "migrations", "aws", "postgres-schema.sql");
const db = await createDatabase({ dbPath, schemaPath });
const timestamp = new Date().toISOString().replace("T", " ").replace("Z", "");

try {
  const rows = await db.all(`
    select id, first_name, last_name, care_status, authorization_received
    from leads
    where coalesce(authorization_received,0) = 1
      and care_status = 'Deceased'
  `);

  if (!rows.length) {
    console.log("No deceased authorizations found. Nothing to move.");
    process.exit(0);
  }

  for (const lead of rows) {
    const oldValue = { id: lead.id, care_status: "Deceased" };
    const newValue = { id: lead.id, care_status: "Terminated" };
    const entityName = `${lead.first_name || ""} ${lead.last_name || ""}`.trim() || `Lead ${lead.id}`;

    await db.run(`
      update leads
      set care_status = 'Terminated',
          updated_at = @updatedAt,
          updated_by = @updatedBy
      where id = @id
    `, {
      id: lead.id,
      updatedAt: timestamp,
      updatedBy: "system_status_migration"
    });

    await db.run(`
      insert into activity_logs (timestamp,user_id,username,action_type,entity_type,entity_id,entity_name,description,old_value,new_value,keywords)
      values (@timestamp,@userId,@username,@actionType,@entityType,@entityId,@entityName,@description,@oldValue,@newValue,@keywords)
    `, {
      timestamp,
      userId: null,
      username: "system_status_migration",
      actionType: "UPDATE_LEAD",
      entityType: "Lead",
      entityId: lead.id,
      entityName,
      description: `Moved authorization status from Deceased to Terminated for '${entityName}'`,
      oldValue: JSON.stringify(oldValue),
      newValue: JSON.stringify(newValue),
      keywords: "lead,authorization,status,migration"
    });
  }

  console.log(`Moved ${rows.length} deceased authorization${rows.length === 1 ? "" : "s"} to Terminated.`);
} finally {
  await db.close?.();
}
