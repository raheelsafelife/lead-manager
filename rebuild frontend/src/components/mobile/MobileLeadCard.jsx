import { ChevronDown, ChevronUp, Phone, UserRound } from "lucide-react";
import { Select, StatusPill } from "../Controls";

export default function MobileLeadCard({ lead, fullName, status, priority, priorityClass, callStatusOptions, open, onToggle, onCallStatus }) {
  const date = lead.updated_at || lead.created_at;
  const displayDate = date ? new Date(date).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "Not available";
  return (
    <div className="m-lead-summary m-only">
      <button type="button" className="m-lead-main" onClick={onToggle} aria-expanded={open}>
        <span className="m-lead-heading"><strong>{fullName}</strong><small>Lead #{lead.id}</small></span>
        <span className="m-lead-chevron">{open ? <ChevronUp size={20} /> : <ChevronDown size={20} />}</span>
      </button>
      <div className="m-lead-badges"><span className="m-status-badge">{status}</span><span className={`m-call-badge ${priorityClass}`}><StatusPill value={priority} /></span></div>
      <div className="m-lead-meta">
        <span><UserRound size={15} />{lead.staff_name || "Unassigned"}</span><span>{lead.source || "No source"}</span><span>Updated {displayDate}</span>
      </div>
      <div className="m-lead-actions">
        {lead.phone ? <a href={`tel:${lead.phone}`} aria-label={`Call ${fullName}`}><Phone size={17} /></a> : <span />}
        <label><span>Call status</span><Select value={priority} options={callStatusOptions} onChange={onCallStatus} /></label>
        <button type="button" onClick={onToggle}>{open ? "Close" : "View details"}</button>
      </div>
    </div>
  );
}
