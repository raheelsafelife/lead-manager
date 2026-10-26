const blank = (value) => value == null || String(value).trim() === "";
export function validateAuthorizationHours(data) {
  for (const [key, label] of [["hours", "Weekly hours"], ["monthly_hours", "Monthly hours"]]) {
    const value = data[key];
    if (!blank(value) && (!["number", "string"].includes(typeof value) || !Number.isFinite(Number(value)) || Number(value) < 0)) return `${label} must be a non-negative number.`;
  }
  return "";
}
export const normalizeHours = (value) => blank(value) ? null : Number(value);
