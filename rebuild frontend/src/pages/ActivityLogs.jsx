import { useEffect, useMemo, useState } from "react";
import {
  CalendarRange,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Clock3,
  Download,
  FileClock,
  Layers3,
  LogIn,
  LogOut,
  MessageCircleMore,
  Pencil,
  Search,
  SquareStack,
  UserRound
} from "lucide-react";
import { Button } from "../components/Controls";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { changedFields, commentFromActivity, friendlyActionTitle, friendlyActivitySummary } from "../utils/activityFormat";

const dateOptions = ["All Time", "Today", "Last 7 Days", "Last 30 Days", "Custom Range"];
const pageSizeOptions = [10, 20, 50, 100];

function startForDateFilter(filter) {
  const d = new Date();
  if (filter === "Today") d.setHours(0, 0, 0, 0);
  else if (filter === "Last 7 Days") d.setDate(d.getDate() - 7);
  else if (filter === "Last 30 Days") d.setDate(d.getDate() - 30);
  else return "";
  return d.toISOString().slice(0, 10);
}

function exportCsv(rows) {
  const cols = ["timestamp", "username", "action", "entity_type", "entity_name", "summary"];
  const csvRows = rows.map((row) => ({
    timestamp: row.timestamp,
    username: row.username,
    action: friendlyActionTitle(row.action_type),
    entity_type: row.entity_type,
    entity_name: row.entity_name,
    summary: friendlyActivitySummary(row)
  }));
  const csv = [cols.join(","), ...csvRows.map((row) => cols.map((col) => `"${String(row[col] || "").replaceAll('"', '""')}"`).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `activity_logs_${Date.now()}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

function iconForAction(actionType) {
  if (actionType === "USER_LOGIN") return LogIn;
  if (actionType === "USER_LOGOUT") return LogOut;
  if (actionType.includes("COMMENT")) return MessageCircleMore;
  if (actionType.includes("UPDATE")) return Pencil;
  return FileClock;
}

function accentForAction(actionType) {
  if (actionType === "USER_LOGIN") return "success";
  if (actionType === "USER_LOGOUT") return "danger";
  if (actionType.includes("COMMENT")) return "warning";
  if (actionType.includes("UPDATE")) return "info";
  return "neutral";
}

function entityTone(entityType) {
  if (entityType === "Lead") return "lead";
  if (entityType === "User") return "user";
  return "other";
}

function relativeTime(value) {
  const date = new Date(String(value).replace(" ", "T"));
  if (Number.isNaN(date.getTime())) return value;
  const diff = Date.now() - date.getTime();
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;
  if (diff < minute) return "just now";
  if (diff < hour) return `${Math.round(diff / minute)} minute${Math.round(diff / minute) === 1 ? "" : "s"} ago`;
  if (diff < day) return `${Math.round(diff / hour)} hour${Math.round(diff / hour) === 1 ? "" : "s"} ago`;
  return `${Math.round(diff / day)} day${Math.round(diff / day) === 1 ? "" : "s"} ago`;
}

function formatStamp(value) {
  const date = new Date(String(value).replace(" ", "T"));
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function buildPageNumbers(currentPage, totalPages) {
  if (totalPages <= 7) return Array.from({ length: totalPages }, (_, index) => index + 1);
  const pages = [1];
  const start = Math.max(2, currentPage - 1);
  const end = Math.min(totalPages - 1, currentPage + 1);
  if (start > 2) pages.push("...");
  for (let page = start; page <= end; page += 1) pages.push(page);
  if (end < totalPages - 1) pages.push("...");
  pages.push(totalPages);
  return pages;
}

export default function ActivityLogs() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [lookups, setLookups] = useState({ users: [] });
  const [expanded, setExpanded] = useState(() => new Set());
  const [filters, setFilters] = useState({
    dateRange: "All Time",
    username: "",
    actionType: "",
    entityType: "",
    search: "",
    startDate: "",
    endDate: ""
  });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const params = useMemo(() => ({
    username: user.role === "admin" ? filters.username : undefined,
    actionType: filters.actionType,
    entityType: filters.entityType,
    startDate: filters.dateRange === "Custom Range" ? filters.startDate : startForDateFilter(filters.dateRange),
    endDate: filters.dateRange === "Custom Range" ? filters.endDate : "",
    search: filters.search,
    limit: pageSize,
    offset: (page - 1) * pageSize
  }), [filters, page, pageSize, user.role]);

  useEffect(() => {
    api.get("/lookups").then((res) => setLookups(res.data));
  }, []);

  useEffect(() => {
    let mounted = true;
    api.get("/activity", { params }).then((res) => {
      if (!mounted) return;
      setRows(res.data.rows || []);
      setTotal(res.data.total || 0);
    });
    return () => {
      mounted = false;
    };
  }, [params]);

  const actionOptions = useMemo(() => {
    const base = ["All Actions"];
    const values = new Set(rows.map((row) => row.action_type).filter(Boolean));
    [
      "USER_LOGIN",
      "USER_LOGOUT",
      "CREATE_LEAD",
      "UPDATE_LEAD",
      "DELETE_LEAD",
      "ADD_COMMENT",
      "REFERRAL_MARKED",
      "STATUS_CHANGED"
    ].forEach((item) => values.add(item));
    return [...base, ...Array.from(values).sort()];
  }, [rows]);

  const entityOptions = useMemo(() => {
    const values = new Set(rows.map((row) => row.entity_type).filter(Boolean));
    ["Lead", "User", "Event"].forEach((item) => values.add(item));
    return ["All Types", ...Array.from(values).sort()];
  }, [rows]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const visiblePages = buildPageNumbers(page, totalPages);

  function patch(key, value) {
    setPage(1);
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function toggleExpanded(id) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="activity-page">
      <div className="activity-page-head">
        <h2>Activity Logs</h2>
        <p>Track all user activities and system events</p>
      </div>

      <section className="activity-filter-card">
        <div className="activity-filters">
          <label className="activity-filter">
            <span><CalendarRange size={18} />Date Range</span>
            <select value={filters.dateRange} onChange={(e) => patch("dateRange", e.target.value)}>
              {dateOptions.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>

          {user.role === "admin" && (
            <label className="activity-filter">
              <span><UserRound size={18} />User</span>
              <select value={filters.username} onChange={(e) => patch("username", e.target.value)}>
                <option value="">All Users</option>
                {lookups.users.map((entry) => <option key={entry.id} value={entry.username}>{entry.username}</option>)}
              </select>
            </label>
          )}

          <label className="activity-filter">
            <span><SquareStack size={18} />Action Type</span>
            <select value={filters.actionType || "All Actions"} onChange={(e) => patch("actionType", e.target.value === "All Actions" ? "" : e.target.value)}>
              {actionOptions.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>

          <label className="activity-filter">
            <span><Layers3 size={18} />Entity Type</span>
            <select value={filters.entityType || "All Types"} onChange={(e) => patch("entityType", e.target.value === "All Types" ? "" : e.target.value)}>
              {entityOptions.map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>

          <label className="activity-filter activity-filter-search">
            <span><Search size={18} />Search</span>
            <input value={filters.search} onChange={(e) => patch("search", e.target.value)} placeholder="Search by keyword..." />
          </label>

          {filters.dateRange === "Custom Range" && (
            <>
              <label className="activity-filter">
                <span><CalendarRange size={18} />From</span>
                <input type="date" value={filters.startDate} onChange={(e) => patch("startDate", e.target.value)} />
              </label>
              <label className="activity-filter">
                <span><CalendarRange size={18} />To</span>
                <input type="date" value={filters.endDate} onChange={(e) => patch("endDate", e.target.value)} />
              </label>
            </>
          )}
        </div>

        <div className="activity-filter-footer">
          <span>Showing {total} activit{total === 1 ? "y" : "ies"}</span>
          <Button onClick={() => exportCsv(rows)}>
            <Download size={17} />
            Export CSV
          </Button>
        </div>
      </section>

      <section className="activity-feed">
        {rows.length ? rows.map((row) => {
          const Icon = iconForAction(row.action_type || "");
          const expandedRow = expanded.has(row.id);
          const changes = changedFields(row);
          const commentText = commentFromActivity(row);
          const hasDetails = changes.length > 0 || Boolean(commentText);

          return (
            <article className={`activity-log-card activity-${accentForAction(row.action_type || "")}`} key={row.id}>
              <div className="activity-log-main">
                <div className="activity-log-icon">
                  <Icon size={24} />
                </div>

                <div className="activity-log-copy">
                  <div className="activity-log-top">
                    <div className="activity-log-title-row">
                      <h3>{friendlyActionTitle(row.action_type)}</h3>
                      <span className={`activity-entity-pill ${entityTone(row.entity_type)}`}>{row.entity_type}</span>
                    </div>
                    <div className="activity-log-time">
                      <Clock3 size={16} />
                      <span>{relativeTime(row.timestamp)}</span>
                    </div>
                  </div>

                  <div className="activity-log-meta">
                    <span><b>By:</b> {row.username}</span>
                    <span><b>Entity:</b> {row.entity_type}</span>
                    <span><b>Details:</b> {friendlyActivitySummary(row)}</span>
                  </div>

                  {expandedRow && commentText && (
                    <div className="activity-log-comment">
                      <b>Comment:</b>
                      <span>{commentText}</span>
                    </div>
                  )}

                  {expandedRow && changes.length > 0 && (
                    <div className="activity-change-list">
                      {changes.map((change) => (
                        <div className="activity-change-row" key={change.key}>
                          <b>{change.label}</b>
                          <span>{change.before}</span>
                          <strong>changed to</strong>
                          <span>{change.after}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="activity-log-actions">
                  <small>{formatStamp(row.timestamp)}</small>
                  {hasDetails && (
                    <button className="activity-expand-button" onClick={() => toggleExpanded(row.id)}>
                      {expandedRow ? (
                        <>
                          Hide Details
                          <ChevronUp size={16} />
                        </>
                      ) : (
                        <>
                          View Details
                          <ChevronDown size={16} />
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>
            </article>
          );
        }) : <div className="info">No activities found matching your filters</div>}
      </section>

      <section className="activity-pagination-card">
        <div className="activity-pagination-spacer" />
        <div className="activity-pagination">
          <button disabled={page === 1} onClick={() => setPage((current) => Math.max(1, current - 1))}><ChevronLeft size={18} /></button>
          {visiblePages.map((item, index) => item === "..." ? (
            <span className="activity-pagination-ellipsis" key={`ellipsis-${index}`}>...</span>
          ) : (
            <button
              className={item === page ? "active" : ""}
              key={item}
              onClick={() => setPage(item)}
            >
              {item}
            </button>
          ))}
          <button disabled={page === totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))}><ChevronRight size={18} /></button>
        </div>

        <label className="activity-page-size">
          <span>{pageSize} per page</span>
          <select value={pageSize} onChange={(e) => { setPage(1); setPageSize(Number(e.target.value)); }}>
            {pageSizeOptions.map((option) => <option key={option} value={option}>{option} per page</option>)}
          </select>
        </label>
      </section>
    </div>
  );
}
