const fieldLabels = {
  active_client: "Referral status",
  address: "Address",
  agency_id: "Payor",
  authorization_received: "Authorization",
  call_status_updated_by: "Call status updated by",
  care_status: "Care Status",
  caregiver_type: "Caregiver Type",
  ccu_id: "CCU",
  city: "City",
  comments: "Comments",
  content: "Comment",
  custom_user_id: "Employee ID",
  deleted_at: "Deleted date",
  dob: "Date of Birth",
  e_contact_name: "Emergency Contact",
  e_contact_phone: "Emergency Contact Phone",
  e_contact_relation: "Relationship",
  email: "Email",
  event_name: "Event",
  fax: "Fax",
  first_name: "First Name",
  gender: "Gender",
  is_chicago_referral: "Chicago Referral",
  is_deleted: "Deleted",
  is_approved: "Approval",
  last_contact_status: "Contact Status",
  last_name: "Last Name",
  medicaid_no: "Medicaid Number",
  name: "Name",
  phone: "Phone",
  priority: "Priority",
  referral_sent_date: "Referral Sent Date",
  referral_type: "Referral Type",
  role: "Role",
  send_reminders: "Email Reminders",
  soc_date: "SOC Date",
  source: "Source",
  ssn: "SSN",
  staff_name: "Staff",
  state: "State",
  street: "Street",
  tag_color: "Color Tag",
  username: "Username",
  word_of_mouth_type: "Word of Mouth Type",
  zip_code: "Zip Code"
};

const ignoredFields = new Set([
  "id",
  "created_at",
  "updated_at",
  "created_by",
  "updated_by",
  "deleted_by",
  "call_status_updated_at",
  "agency_address",
  "agency_fax",
  "agency_email",
  "agency_phone",
  "ccu_street",
  "ccu_city",
  "ccu_state",
  "ccu_zip_code",
  "ccu_phone",
  "ccu_fax",
  "ccu_email",
  "ccu_care_coordinator_name",
  "profile_picture",
  "password_hash"
]);

function parseJsonMaybe(value) {
  if (!value) return null;
  if (typeof value === "object") return value;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function clean(value) {
  if (value === undefined || value === null || value === "") return "Not added";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (value === 1 || value === "1") return "Yes";
  if (value === 0 || value === "0") return "No";
  return String(value);
}

function valueFor(field, data) {
  if (!data) return "Not added";
  if (field === "agency_id") return clean(data.agency_name || data.name || data.agency_id);
  if (field === "ccu_id") return clean(data.ccu_name || data.name || data.ccu_id);
  if (field === "active_client") return Number(data.active_client) === 1 ? "Referral Sent" : "Lead";
  if (field === "authorization_received") return Number(data.authorization_received) === 1 ? "Received" : "Pending";
  if (field === "is_chicago_referral") return Number(data.is_chicago_referral) === 1 ? "Yes" : "No";
  if (field === "is_deleted") return Number(data.is_deleted) === 1 ? "Deleted" : "Active";
  if (field === "is_approved") return Number(data.is_approved) === 1 ? "Approved" : "Pending";
  return clean(data[field]);
}

function titleCase(value) {
  return String(value || "")
    .toLowerCase()
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function changedFields(row) {
  const oldData = parseJsonMaybe(row.old_value);
  const newData = parseJsonMaybe(row.new_value);
  if (!oldData || !newData) return [];

  const keys = new Set([...Object.keys(oldData), ...Object.keys(newData)]);
  return [...keys]
    .filter((key) => !ignoredFields.has(key))
    .map((key) => ({
      key,
      label: fieldLabels[key] || titleCase(key),
      before: valueFor(key, oldData),
      after: valueFor(key, newData)
    }))
    .filter((change) => change.before !== change.after);
}

export function commentFromActivity(row) {
  const oldData = parseJsonMaybe(row.old_value);
  const newData = parseJsonMaybe(row.new_value);
  return clean(newData?.content || newData?.comments || newData?.comment || oldData?.comments || "").replace(/^Not added$/, "");
}

export function friendlyActionTitle(actionType) {
  const titles = {
    ADD_COMMENT: "Comment Added",
    CREATE_CCU: "CCU Created",
    CREATE_EVENT: "Event Created",
    CREATE_LEAD: "Lead Created",
    CREATE_SOURCE: "Source Created",
    CREATE_USER: "User Created",
    DELETE_ATTACHMENT: "Attachment Deleted",
    DELETE_CCU: "CCU Deleted",
    DELETE_EVENT: "Event Deleted",
    DELETE_LEAD: "Lead Deleted",
    DELETE_SOURCE: "Source Deleted",
    DELETE_USER: "User Deleted",
    PASSWORD_CHANGED: "Password Changed",
    PASSWORD_RESET: "Password Reset",
    PASSWORD_RESET_REQUESTED: "Password Reset Requested",
    RESTORE_LEAD: "Lead Restored",
    UPDATE_CCU: "CCU Updated",
    UPDATE_EVENT: "Event Updated",
    UPDATE_LEAD: "Lead Updated",
    UPDATE_PAYOR: "Payor Updated",
    UPDATE_SOURCE: "Source Updated",
    UPDATE_PROFILE: "Profile Updated",
    UPDATE_USER: "User Updated",
    UPLOAD_ATTACHMENT: "Attachment Uploaded",
    USER_APPROVED: "User Approved",
    USER_LOGIN: "User Login",
    USER_LOGOUT: "User Logout"
  };
  return titles[actionType] || titleCase(actionType);
}

export function friendlyActivitySummary(row) {
  const actor = row.username || "Someone";
  const name = row.entity_name || row.description || row.entity_type || "record";
  const changes = changedFields(row);
  const comment = commentFromActivity(row);
  if (row.action_type === "ADD_COMMENT" && comment) return `${actor} added a comment for ${name}: ${comment}`;
  if (changes.length === 1) {
    const change = changes[0];
    return `${actor} changed ${change.label} from "${change.before}" to "${change.after}" for ${name}.`;
  }
  if (changes.length > 1) return `${actor} updated ${name}. ${changes.length} fields changed.`;
  return row.description || `${actor} performed ${friendlyActionTitle(row.action_type).toLowerCase()} for ${name}.`;
}
