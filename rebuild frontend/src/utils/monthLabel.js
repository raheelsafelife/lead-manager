const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatMonthLabel(value) {
  const match = String(value || "").match(/^(\d{4})-(\d{2})$/);
  if (!match) return value || "";
  const monthIndex = Number(match[2]) - 1;
  if (monthIndex < 0 || monthIndex > 11) return value;
  return `${monthNames[monthIndex]} ${match[1]}`;
}
