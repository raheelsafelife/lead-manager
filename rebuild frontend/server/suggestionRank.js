const normalizePhone = (value = "") => String(value || "").replace(/\D/g, "");

export function searchSuggestionRelevance(lead, rawQuery) {
  const query = String(rawQuery || "").trim().toLowerCase();
  const id = String(lead.id);
  const phone = normalizePhone(lead.phone);
  const queryPhone = normalizePhone(query);
  const name = `${lead.first_name || ""} ${lead.last_name || ""}`.trim().toLowerCase();
  if (id === query) return 0;
  if (id.startsWith(query)) return 1;
  if (queryPhone && phone === queryPhone) return 2;
  if (queryPhone && phone.startsWith(queryPhone)) return 3;
  if (name === query) return 4;
  if (name.startsWith(query)) return 5;
  return 6;
}

