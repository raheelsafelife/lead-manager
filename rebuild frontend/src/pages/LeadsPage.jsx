import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import {
  CalendarRange,
  Download,
  Hash,
  PhoneCall,
  Search,
  Tag,
  UserRound,
  Users,
  XCircle
} from "lucide-react";
import { Button, Select } from "../components/Controls";
import LeadCard from "../components/LeadCard";
import { api, downloadFile } from "../services/api";
import { activeStatuses, caregiverTypes, referralStatuses, tagColors } from "../utils/constants";
import { useAuth } from "../context/AuthContext";

const dateRangeOptions = ["All Time", "Today", "Last 7 Days", "Last 30 Days"];

function startForDateFilter(filter) {
  const d = new Date();
  if (filter === "Today") d.setHours(0, 0, 0, 0);
  else if (filter === "Last 7 Days") d.setDate(d.getDate() - 7);
  else if (filter === "Last 30 Days") d.setDate(d.getDate() - 30);
  else return "";
  return d.toISOString().slice(0, 10);
}

function getDefaultFilters(user, initialId, initialOptions = {}) {
  return {
    active: initialOptions.transferView || initialOptions.globalSearch ? "All" : "Active",
    status: "All",
    callStatus: "All",
    tagColor: "All",
    referralType: "All",
    caregiverType: "All",
    ccu: "All",
    payor: "All",
    search: "",
    staff: "",
    source: "",
    idSearch: initialId,
    sort: "Newest Added",
    includeDeleted: Boolean(initialOptions.includeDeleted),
    onlyMine: user.role !== "admin",
    dateRange: "All Time",
    transferView: Boolean(initialOptions.transferView)
  };
}

function readUrlFilters(search) {
  const searchParams = new URLSearchParams(search);
  return {
    idSearch: searchParams.get("idSearch") || "",
    options: {
      transferView: searchParams.get("transferView") === "true",
      includeDeleted: searchParams.get("includeDeleted") === "true",
      globalSearch: searchParams.get("globalSearch") === "true"
    }
  };
}

function pageSubtitle(type, discovery) {
  if (discovery) return "Search and explore matching leads quickly.";
  if (type === "referral") return "Track, filter and manage all your referrals in one place.";
  if (type === "authorization") return "Review, filter and manage all authorizations in one place.";
  return "View, filter and manage all your leads in one place.";
}

export default function LeadsPage({ title, type, discovery = false }) {
  const { user } = useAuth();
  const location = useLocation();
  const { idSearch: initialId, options: initialOptions } = readUrlFilters(location.search);
  const [filters, setFilters] = useState(() => getDefaultFilters(user, initialId, initialOptions));
  const [lookups, setLookups] = useState({ ccus: [], agencies: [] });
  const [data, setData] = useState({ rows: [], total: 0 });
  const [page, setPage] = useState(0);
  const [exportOpen, setExportOpen] = useState(false);
  const [exporting, setExporting] = useState(false);

  const params = useMemo(() => ({
    ...filters,
    type: discovery || initialOptions.globalSearch ? undefined : type,
    pageSearch: discovery ? undefined : true,
    startDate: startForDateFilter(filters.dateRange),
    offset: page * 10,
    limit: 10
  }), [filters, type, discovery, page, initialOptions.globalSearch]);

  useEffect(() => {
    const { idSearch, options } = readUrlFilters(location.search);
    setFilters(getDefaultFilters(user, idSearch, options));
    setPage(0);
  }, [location.search, user.role]);

  function patch(key, value) {
    setFilters((current) => ({ ...current, [key]: value }));
    setPage(0);
  }

  function resetFilters() {
    setFilters(getDefaultFilters(user, initialId, initialOptions));
    setPage(0);
  }

  function setAuthorizationMode(transferView) {
    setFilters((current) => ({
      ...current,
      transferView,
      active: transferView ? "All" : current.active,
      status: "All"
    }));
    setPage(0);
  }

  async function handleExport(format = "excel") {
    setExporting(true);
    try {
      await downloadFile(
        "/reports/export",
        { ...params, format: format === "word" ? "word" : undefined },
        format === "word" ? `${type || "leads"}_export.docx` : `${type || "leads"}_export.xlsx`
      );
      setExportOpen(false);
    } finally {
      setExporting(false);
    }
  }

  function load() {
    api.get("/leads", { params }).then((res) => setData(res.data));
  }

  useEffect(() => {
    api.get("/lookups").then((res) => setLookups(res.data));
  }, []);

  useEffect(load, [JSON.stringify(params)]);

  const statusOptions = type === "referral"
    ? referralStatuses
    : type === "authorization"
      ? ["All", "Care Start", "Not Start", "Hold", "Terminated", "Deceased", "Transfer Received"]
      : ["All", "Initial Call", "No Response", "Not Interested"];

  const summaryLabel = type === "referral" ? "referrals" : type === "authorization" ? "authorizations" : "leads";

  return (
    <div className="leads-page">
      <div className="leads-page-head">
        <h2>{title}</h2>
        <p>{pageSubtitle(type, discovery)}</p>
      </div>

      <section className="leads-filter-card">
        <div className="leads-filter-grid">
          <label className="leads-filter">
            <span><Search size={18} />Search by Name</span>
            <div className="leads-input-shell">
              <input value={filters.search} onChange={(e) => patch("search", e.target.value)} placeholder="Search by name..." />
              <Search size={18} />
            </div>
          </label>

          <label className="leads-filter">
            <span><UserRound size={18} />Staff</span>
            <Select value={filters.staff || "All Staff"} onChange={(value) => patch("staff", value === "All Staff" ? "" : value)} options={["All Staff", ...lookups.approvedUsers?.map((entry) => entry.username) || []]} />
          </label>

          <label className="leads-filter">
            <span><Users size={18} />Source</span>
            <div className="leads-input-shell">
              <input value={filters.source} onChange={(e) => patch("source", e.target.value)} placeholder="All Sources" />
            </div>
          </label>

          <label className="leads-filter">
            <span><Hash size={18} />Search by ID</span>
            <div className="leads-input-shell">
              <input value={filters.idSearch} onChange={(e) => patch("idSearch", e.target.value)} placeholder="Enter ID..." />
              <Hash size={18} />
            </div>
          </label>

          <label className="leads-filter">
            <span><CalendarRange size={18} />Date Range</span>
            <Select value={filters.dateRange} onChange={(value) => patch("dateRange", value)} options={dateRangeOptions} />
          </label>

          <label className="leads-filter">
            <span><Users size={18} />Active Status</span>
            <Select value={filters.active} onChange={(value) => patch("active", value)} options={activeStatuses} />
          </label>

          <label className="leads-filter">
            <span><PhoneCall size={18} />Call Status</span>
            <Select value={filters.callStatus} onChange={(value) => patch("callStatus", value)} options={["All", "Not Called", "Pending", "Called"]} />
          </label>

          <label className="leads-filter">
            <span><Tag size={18} />Color Tag</span>
            <Select value={filters.tagColor === "All" ? "All Tags" : filters.tagColor} onChange={(value) => patch("tagColor", value === "All Tags" ? "All" : value)} options={tagColors.map((item) => item === "All" ? "All Tags" : item)} />
          </label>

          <label className="leads-filter">
            <span>Contact Status</span>
            <Select value={filters.status} onChange={(value) => patch("status", value)} options={statusOptions} />
          </label>

          <label className="leads-filter">
            <span>Sort By</span>
            <Select value={filters.sort} onChange={(value) => patch("sort", value)} options={["Newest Added", "Recently Updated"]} />
          </label>

          {type === "referral" && (
            <>
              <label className="leads-filter">
                <span>Referral Type</span>
                <Select value={filters.referralType} onChange={(value) => patch("referralType", value)} options={["All", "Regular", "Interim"]} />
              </label>
              <label className="leads-filter">
                <span>Caregiver Type</span>
                <Select value={filters.caregiverType} onChange={(value) => patch("caregiverType", value)} options={["All", ...caregiverTypes]} />
              </label>
            </>
          )}

          {(type === "referral" || type === "authorization") && (
            <>
              <label className="leads-filter">
                <span>CCU</span>
                <Select value={filters.ccu} onChange={(value) => patch("ccu", value)} options={["All", ...lookups.ccus.map((entry) => entry.name)]} />
              </label>
              <label className="leads-filter">
                <span>Payor</span>
                <Select value={filters.payor} onChange={(value) => patch("payor", value)} options={["All", ...lookups.agencies.map((entry) => entry.name)]} />
              </label>
            </>
          )}
        </div>

        <div className="leads-quick-filters">
          <div className="leads-quick-group">
            <span>Quick Filters</span>
            <div className="leads-pill-row">
              {activeStatuses.map((value) => (
                <button
                  className={`leads-filter-pill ${filters.active === value ? "active tone-primary" : ""}`}
                  key={value}
                  onClick={() => patch("active", value)}
                >
                  {value}
                </button>
              ))}
            </div>
          </div>

          <div className="leads-pill-divider" />

          <div className="leads-quick-group">
            <div className="leads-pill-row">
              {["Not Called", "Pending", "Called", "All"].map((value) => (
                <button
                  className={`leads-filter-pill ${filters.callStatus === value ? `active ${value === "Not Called" ? "tone-danger" : value === "Pending" ? "tone-warning" : value === "Called" ? "tone-success" : "tone-primary"}` : value === "Not Called" ? "outline-danger" : value === "Pending" ? "outline-warning" : value === "Called" ? "outline-success" : ""}`}
                  key={value}
                  onClick={() => patch("callStatus", value)}
                >
                  {value}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="leads-toolbar-modern">
        <div className="leads-toolbar-actions">
          {type === "authorization" && (
            <>
              <Button active={!filters.transferView} onClick={() => setAuthorizationMode(false)}>
                Authorizations
              </Button>
              <Button active={filters.transferView} onClick={() => setAuthorizationMode(true)}>
                Transfer Cases
              </Button>
            </>
          )}
          <Button variant="primary" onClick={load}>
            <Search size={16} />
            Search
          </Button>
          <Button onClick={resetFilters}>
            <XCircle size={16} />
            Clear Filters
          </Button>
        </div>

        <div className="leads-export-group">
          <button className="leads-export-button" onClick={() => setExportOpen((current) => !current)}>
            <span><Download size={18} />Export</span>
            <span className={`leads-export-caret ${exportOpen ? "open" : ""}`}>⌄</span>
          </button>
          {exportOpen && (
            <div className="leads-export-menu">
              <button onClick={() => handleExport("excel")} disabled={exporting}>Export Excel</button>
              <button onClick={() => handleExport("word")} disabled={exporting}>Export Word</button>
            </div>
          )}
        </div>
      </div>

      <p className="leads-summary-line">
        <b>Showing {data.rows.length} {filters.transferView ? "transfer cases" : summaryLabel} of {data.total} total</b>
        <span>Active Status: {filters.active} | Status: {filters.status} | Call Status: {filters.callStatus} | Tag: {filters.tagColor === "All Tags" ? "All" : filters.tagColor}</span>
      </p>

      {!discovery && (
        <div className="leads-inline-options">
          <label className="check"><input type="checkbox" checked={filters.includeDeleted} onChange={(e) => patch("includeDeleted", e.target.checked)} />Show Deleted Leads</label>
          {user.role !== "admin" && (
            <div className="segmented leads-view-toggle">
              <Button active={filters.onlyMine} onClick={() => patch("onlyMine", true)}>My {type === "referral" ? "Referrals" : "Leads"}</Button>
              <Button active={!filters.onlyMine} onClick={() => patch("onlyMine", false)}>All {type === "referral" ? "Referrals" : "Leads"}</Button>
            </div>
          )}
        </div>
      )}

      {data.rows.length
        ? data.rows.map((lead) => <LeadCard key={lead.id} lead={lead} type={type} onChanged={load} />)
        : <div className="info">No exact match found. Try a shorter search term, different spelling, phone, or ID.</div>}

      <div className="pagination">
        <Button disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</Button>
        <span>Page {page + 1} of {Math.max(1, Math.ceil(data.total / 10))}</span>
        <Button disabled={(page + 1) * 10 >= data.total} onClick={() => setPage(page + 1)}>Next</Button>
      </div>
    </div>
  );
}
