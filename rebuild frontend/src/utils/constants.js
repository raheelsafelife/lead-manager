export const leadSources = ["Home Health Notify", "Web", "Direct Through CCU", "Event", "Word of Mouth", "Transfer", "Other"];
export const callStatuses = ["Not Called", "Pending", "Called"];
export const activeStatuses = ["Active", "Inactive", "All"];
export const tagColors = ["All", "Blue", "Purple"];
export const caregiverTypes = ["None", "FHCA", "PHCA", "HCA"];
export const referralStatuses = ["All", "Initial Referral Sent", "Assessment Scheduled", "Assessment Done", "Not Approved", "Services Refused"];
export const leadStatuses = ["Initial Call", "Not Interested", "No Response"];
export const authCareStatuses = ["Active", "Hold", "Terminated", "Deceased", "Transfer"];

export function normalizeCcuName(value = "") {
  return String(value || "")
    .toLowerCase()
    .replace(/\([^)]*\)/g, " ")
    .replace(/&/g, " and ")
    .replace(/\b(dept|department)\b/g, "department")
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\b(area|county|case|coordination|coordinating|program|programs|office|diocese|of|the|and)\b/g, " ")
    .replace(/\b(north|south|east|west|northern|southern|central|regular|nwss|nenw|oas|ssss|swss|nw|ne|se|sw)\b/g, " ")
    .replace(/\b(aurora|elgin|kendall|kankakee|joliet|lake|schaumburg|will)\b/g, " ")
    .replace(/\b(ass|assoc|association)\b/g, " ")
    .replace(/\b\d+\b/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function ccuCompletenessScore(ccu = {}) {
  return ["name", "street", "city", "state", "zip_code", "phone", "fax", "email", "care_coordinator_name"]
    .filter((key) => String(ccu[key] || "").trim()).length;
}

export function uniqueCcuSuggestions(ccus = [], selectedId = null) {
  const selectedKey = selectedId ? String(selectedId) : "";
  const grouped = ccus.reduce((acc, ccu) => {
    const key = normalizeCcuName(ccu.name) || `ccu-${ccu.id}`;
    if (!acc.has(key)) acc.set(key, []);
    acc.get(key).push(ccu);
    return acc;
  }, new Map());

  return [...grouped.values()]
    .map((group) => {
      const selected = group.find((ccu) => String(ccu.id) === selectedKey);
      if (selected) return selected;
      const preferred = group.find((ccu) => Number(ccu.is_preferred_suggestion) === 1);
      if (preferred) return preferred;
      return [...group].sort((a, b) => ccuCompletenessScore(b) - ccuCompletenessScore(a) || Number(a.id) - Number(b.id))[0];
    })
    .sort((a, b) => String(a.name || "").localeCompare(String(b.name || "")));
}
