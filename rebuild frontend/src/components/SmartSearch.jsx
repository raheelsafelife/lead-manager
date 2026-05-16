import { Search } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

export default function SmartSearch({ className = "" }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const timer = useRef(null);

  useEffect(() => {
    clearTimeout(timer.current);
    if (!query.trim()) {
      setSuggestions([]);
      return;
    }
    timer.current = setTimeout(async () => {
      const res = await api.get("/search/suggestions", { params: { q: query } });
      setSuggestions(res.data.clients || []);
    }, 220);
  }, [query]);

  function goSuggestion(item) {
    const map = { "Authorizations": "/authorizations", "Referrals Sent": "/referrals", "View Leads": "/view-leads" };
    setQuery("");
    setSuggestions([]);
    navigate(item.targetUrl || `${map[item.targetPage] || "/view-leads"}?idSearch=${item.id}`);
  }

  return (
    <div className={`smart-search ${className}`}>
      <Search size={30} />
      <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="SmartSearch leads by name or ID..." />
      {suggestions.length > 0 && <div className="suggestions">{suggestions.map((item) => <button key={item.id} onClick={() => goSuggestion(item)}>#{item.id} {item.name}<span>{item.phone || "No phone"} · {item.targetPage}</span></button>)}</div>}
    </div>
  );
}
