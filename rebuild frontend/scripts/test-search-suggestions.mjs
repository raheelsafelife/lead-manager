import { searchSuggestionRelevance } from "../server/suggestionRank.js";

const leads = [
  { id: 704, first_name: "Christine", last_name: "Burg", phone: "(224) 447-8490", created_at: "2026-05-03" },
  { id: 447, first_name: "Archie", last_name: "Cole Sr.", phone: "(847) 744-1908", created_at: "2025-01-01" },
  { id: 148, first_name: "Waleed", last_name: "A hakky", phone: "7082447872", created_at: "2026-06-01" },
];

leads.sort((left, right) => searchSuggestionRelevance(left, "447") - searchSuggestionRelevance(right, "447")
  || String(right.created_at).localeCompare(String(left.created_at)));

if (leads[0].id !== 447) {
  throw new Error(`Expected exact ID 447 first, got ${leads[0].id}`);
}

console.log("SmartSearch ranking passed: exact lead ID appears first");
