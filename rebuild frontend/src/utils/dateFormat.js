export function formatCalendarDate(value, locale) {
  if (!value) return "N/A";

  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return "N/A";

  const [, year, month, day] = match;
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  if (Number.isNaN(date.getTime())) return "N/A";

  return new Intl.DateTimeFormat(locale, { timeZone: "UTC" }).format(date);
}

export function calendarDateParts(value) {
  const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return null;

  return {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3])
  };
}
