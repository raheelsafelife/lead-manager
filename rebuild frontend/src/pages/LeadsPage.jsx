import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
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
import { Button, Field, Modal, Select } from "../components/Controls";
import LeadCard from "../components/LeadCard";
import { LeadListSkeleton } from "../components/Skeleton";
import { api, downloadFile } from "../services/api";
import { caregiverTypes, leadCallStatuses, referralCallStatuses, referralStatuses, tagColors } from "../utils/constants";
import { useAuth } from "../context/AuthContext";
import { isAdminRole } from "../utils/roles";

const dateRangeOptions = ["All Time", "Today", "Last 7 Days", "Last 30 Days", "Custom"];
const attachmentDateRangeOptions = ["All Time", "Today", "Last 7 Days", "Last 30 Days", "Custom"];

function startForDateFilter(filter) {
  const d = new Date();
  if (filter === "Today") d.setHours(0, 0, 0, 0);
  else if (filter === "Last 7 Days") d.setDate(d.getDate() - 7);
  else if (filter === "Last 30 Days") d.setDate(d.getDate() - 30);
  else return "";
  return d.toISOString().slice(0, 10);
}

function getDefaultFilters(user, initialId, initialOptions = {}, type = "lead") {
  return {
    active: initialOptions.active || (initialOptions.globalSearch ? "All" : "Active"),
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
    onlyMine: !isAdminRole(user.role),
    dateRange: "All Time",
    customStartDate: "",
    customEndDate: "",
    attachmentDateRange: "All Time",
    attachmentStartDate: "",
    attachmentEndDate: "",
    transferView: Boolean(initialOptions.transferView),
    chicagoOnly: Boolean(initialOptions.chicagoOnly),
    reportable: Boolean(initialOptions.reportable),
    includeChicago: type === "authorization" || Boolean(initialOptions.includeChicago)
  };
}

function readUrlFilters(search) {
  const searchParams = new URLSearchParams(search);
  return {
    idSearch: searchParams.get("idSearch") || "",
    options: {
      transferView: searchParams.get("transferView") === "true",
      includeDeleted: searchParams.get("includeDeleted") === "true",
      globalSearch: searchParams.get("globalSearch") === "true",
      active: searchParams.get("active") || "",
      chicagoOnly: searchParams.get("chicagoOnly") === "true",
      reportable: searchParams.get("reportable") === "true",
      includeChicago: searchParams.get("includeChicago") === "true"
    }
  };
}

function pageSubtitle(type, discovery) {
  if (discovery) return "Search and explore matching leads quickly.";
  if (type === "referral") return "Active referrals stay here. Closed referrals live in Archive. Chicago referrals live in their own folder.";
  if (type === "authorization") return "Active authorizations are shown by default. Use filters to narrow by hold, terminated, transfer cases, staff, CCU, payor, or authorization received date.";
  return "Active leads stay here. Closed leads live in Archive. Chicago referrals live in their own folder.";
}

function folderCopy(active) {
  if (active === "Chicago") return { title: "Chicago Referral Folder", summary: "Chicago Referral", empty: "No Chicago referrals found for these filters." };
  if (active === "Inactive") return { title: "Archive Folder", summary: "Archive", empty: "No archived records found for these filters." };
  if (active === "All") return { title: "All Records", summary: "All", empty: "No matching records found for these filters." };
  return { title: "Active Folder", summary: "Active", empty: "No active records found for these filters." };
}

export default function LeadsPage({ title, type, discovery = false }) {
  const { user } = useAuth();
  const canAdmin = isAdminRole(user.role);
  const location = useLocation();
  const navigate = useNavigate();
  const { idSearch: initialId, options: initialOptions } = readUrlFilters(location.search);
  const [filters, setFilters] = useState(() => getDefaultFilters(user, initialId, initialOptions, type));
  const [lookups, setLookups] = useState({ ccus: [], agencies: [] });
  const [data, setData] = useState({ rows: [], total: 0 });
  const [loadingRows, setLoadingRows] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [page, setPage] = useState(0);
  const [exportOpen, setExportOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [customDateOpen, setCustomDateOpen] = useState(false);
  const [customDateDraft, setCustomDateDraft] = useState({ start: "", end: "" });
  const [attachmentDateOpen, setAttachmentDateOpen] = useState(false);
  const [attachmentDateDraft, setAttachmentDateDraft] = useState({ range: "All Time", start: "", end: "" });
  const ccuFilterOptions = ["All", ...lookups.ccus.map((entry) => entry.name)];

  const params = useMemo(() => ({
    ...filters,
    type: discovery || initialOptions.globalSearch ? undefined : type,
    pageSearch: discovery ? undefined : true,
    startDate: filters.dateRange === "Custom" ? filters.customStartDate : startForDateFilter(filters.dateRange),
    endDate: filters.dateRange === "Custom" ? filters.customEndDate : undefined,
    attachmentStartDate: filters.attachmentDateRange === "Custom" ? filters.attachmentStartDate : startForDateFilter(filters.attachmentDateRange),
    attachmentEndDate: filters.attachmentDateRange === "Custom" ? filters.attachmentEndDate : undefined,
    offset: page * 10,
    limit: 10
  }), [filters, type, discovery, page, initialOptions.globalSearch]);

  useEffect(() => {
    const { idSearch, options } = readUrlFilters(location.search);
    setFilters(getDefaultFilters(user, idSearch, options, type));
    setPage(0);
  }, [location.search, user.role, type]);

  function patch(key, value) {
    setFilters((current) => ({ ...current, [key]: value }));
    setPage(0);
  }

  function handleDateRangeChange(value) {
    if (value === "Custom") {
      setCustomDateDraft({ start: filters.customStartDate, end: filters.customEndDate });
      setFilters((current) => ({ ...current, dateRange: value }));
      setCustomDateOpen(true);
      setPage(0);
      return;
    }
    setFilters((current) => ({ ...current, dateRange: value }));
    setPage(0);
  }

  function openCustomDateDialog() {
    setCustomDateDraft({ start: filters.customStartDate, end: filters.customEndDate });
    setCustomDateOpen(true);
  }

  function applyCustomDateRange() {
    setFilters((current) => ({
      ...current,
      dateRange: "Custom",
      customStartDate: customDateDraft.start,
      customEndDate: customDateDraft.end
    }));
    setCustomDateOpen(false);
    setPage(0);
  }

  function clearCustomDateRange() {
    setFilters((current) => ({
      ...current,
      dateRange: "All Time",
      customStartDate: "",
      customEndDate: ""
    }));
    setCustomDateDraft({ start: "", end: "" });
    setCustomDateOpen(false);
    setPage(0);
  }

  function openAttachmentDateDialog() {
    setAttachmentDateDraft({
      range: filters.attachmentDateRange,
      start: filters.attachmentStartDate,
      end: filters.attachmentEndDate
    });
    setAttachmentDateOpen(true);
  }

  function handleAttachmentDateRangeChange(range) {
    if (range === "Custom") {
      setAttachmentDateDraft({
        range,
        start: filters.attachmentStartDate,
        end: filters.attachmentEndDate
      });
      setAttachmentDateOpen(true);
      return;
    }
    setFilters((current) => ({
      ...current,
      attachmentDateRange: range,
      attachmentStartDate: "",
      attachmentEndDate: ""
    }));
    setPage(0);
  }

  function applyAttachmentDateRange() {
    setFilters((current) => ({
      ...current,
      attachmentDateRange: attachmentDateDraft.range,
      attachmentStartDate: attachmentDateDraft.range === "Custom" ? attachmentDateDraft.start : "",
      attachmentEndDate: attachmentDateDraft.range === "Custom" ? attachmentDateDraft.end : ""
    }));
    setAttachmentDateOpen(false);
    setPage(0);
  }

  function clearAttachmentDateRange() {
    setFilters((current) => ({
      ...current,
      attachmentDateRange: "All Time",
      attachmentStartDate: "",
      attachmentEndDate: ""
    }));
    setAttachmentDateDraft({ range: "All Time", start: "", end: "" });
    setAttachmentDateOpen(false);
    setPage(0);
  }

  function setFolder(active) {
    setFilters((current) => ({
      ...current,
      active,
      status: "All"
    }));
    setPage(0);
  }

  function setChicagoFolder() {
    setFilters((current) => ({ ...current, chicagoOnly: true, status: "All" }));
    setPage(0);
  }

  function resetFilters() {
    if (location.search) navigate(location.pathname, { replace: true });
    setFilters(getDefaultFilters(user, "", {}, type));
    setCustomDateDraft({ start: "", end: "" });
    setCustomDateOpen(false);
    setAttachmentDateDraft({ range: "All Time", start: "", end: "" });
    setAttachmentDateOpen(false);
    setPage(0);
  }

  function setAuthorizationMode(transferView) {
    setFilters((current) => ({
      ...current,
      transferView,
      active: current.active || "Active",
      status: "All"
    }));
    setPage(0);
  }

  function setAuthorizationStatus(status) {
    setFilters((current) => ({
      ...current,
      transferView: false,
      active: status === "Active" ? "Active" : "All",
      status: status === "Active" ? "All" : status
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
    let cancelled = false;
    setLoadingRows(true);
    setLoadError("");
    api.get("/leads", { params })
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(err.response?.data?.error || "Could not load leads");
          setData({ rows: [], total: 0 });
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingRows(false);
      });
    return () => {
      cancelled = true;
    };
  }

  useEffect(() => {
    api.get("/lookups").then((res) => setLookups(res.data));
  }, []);

  useEffect(load, [JSON.stringify(params)]);

  const statusOptions = type === "referral"
    ? referralStatuses
    : type === "authorization"
      ? ["Active", "Hold", "Terminated"]
      : ["All", "Initial Call", "No Response", "Not Interested"];
  const callStatusOptions = type === "lead" ? leadCallStatuses : type === "referral" ? referralCallStatuses : [...new Set([...leadCallStatuses, ...referralCallStatuses])];
  const callFilterOptions = ["All", ...callStatusOptions];

  const summaryLabel = type === "referral" ? "referrals" : type === "authorization" ? "authorizations" : "leads";
  const currentFolder = folderCopy(filters.active);

  return (
    <div className="leads-page">
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
            <Select value={filters.dateRange} onChange={handleDateRangeChange} options={dateRangeOptions} />
            {filters.dateRange === "Custom" && (
              <button type="button" className="date-range-summary-button" onClick={openCustomDateDialog}>
                {filters.customStartDate || "Start"} to {filters.customEndDate || "End"}
              </button>
            )}
          </label>

          <label className="leads-filter">
            <span><PhoneCall size={18} />Call Status</span>
            <Select value={filters.callStatus} onChange={(value) => patch("callStatus", value)} options={callFilterOptions} />
          </label>

          <label className="leads-filter">
            <span><Tag size={18} />Color Tag</span>
            <Select value={filters.tagColor === "All" ? "All Tags" : filters.tagColor} onChange={(value) => patch("tagColor", value === "All Tags" ? "All" : value)} options={tagColors.map((item) => item === "All" ? "All Tags" : item)} />
          </label>

          {type !== "authorization" && (
            <label className="leads-filter">
              <span>Contact Status</span>
              <Select value={filters.status} onChange={(value) => patch("status", value)} options={statusOptions} />
            </label>
          )}

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
                <Select value={filters.ccu} onChange={(value) => patch("ccu", value)} options={ccuFilterOptions} />
              </label>
              <label className="leads-filter">
                <span>Payor</span>
                <Select value={filters.payor} onChange={(value) => patch("payor", value)} options={["All", ...lookups.agencies.map((entry) => entry.name)]} />
              </label>
              {type === "authorization" && (
                <label className="leads-filter">
                  <span>Attachment Updated</span>
                  <Select value={filters.attachmentDateRange} onChange={handleAttachmentDateRangeChange} options={attachmentDateRangeOptions} />
                  {filters.attachmentDateRange === "Custom" && (
                    <button type="button" className="date-range-summary-button" onClick={openAttachmentDateDialog}>
                      {filters.attachmentStartDate || "Start"} to {filters.attachmentEndDate || "End"}
                    </button>
                  )}
                </label>
              )}
            </>
          )}
        </div>

        {!discovery && type !== "authorization" && (
          <div className="archive-folder-switch" aria-label={`${summaryLabel} folder`}>
            <button className={filters.active === "Active" ? "active" : ""} onClick={() => setFolder("Active")} type="button">
              <b>Active Folder</b>
              <span>Open work only</span>
            </button>
            <button className={filters.active === "Inactive" ? "active archive" : "archive"} onClick={() => setFolder("Inactive")} type="button">
              <b>Archive Folder</b>
              <span>Closed and inactive</span>
            </button>
            <button className={filters.chicagoOnly ? "active chicago" : "chicago"} onClick={setChicagoFolder} type="button">
              <b>Chicago Referral</b>
              <span>{filters.active} Chicago records</span>
            </button>
            {(initialOptions.globalSearch || filters.chicagoOnly) && (
              <button className={filters.active === "All" ? "active all" : "all"} onClick={() => setFolder("All")} type="button">
                <b>All Records</b>
                <span>{filters.chicagoOnly ? "All Chicago records" : "Global search result"}</span>
              </button>
            )}
          </div>
        )}

      </section>

      <div className="leads-toolbar-modern">
        <div className="leads-toolbar-actions">
          {type === "authorization" && (
            <>
              {statusOptions.map((status) => (
                <Button
                  key={status}
                  active={!filters.transferView && (status === "Active" ? filters.active === "Active" && filters.status === "All" : filters.status === status)}
                  onClick={() => setAuthorizationStatus(status)}
                >
                  {status === "Active" ? "Active Authorizations" : status}
                </Button>
              ))}
              <Button active={filters.transferView} onClick={() => {
                setAuthorizationMode(true);
                patch("status", "All");
              }}>
                {filters.active} Transfers
              </Button>
              {filters.transferView && ["Active", "Inactive", "All"].map((scope) => (
                <Button key={`transfer-${scope}`} active={filters.active === scope} onClick={() => setFolder(scope)}>
                  {scope}
                </Button>
              ))}
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
        <b>Showing {data.rows.length} {filters.transferView ? "transfer cases" : summaryLabel} in {currentFolder.summary} of {data.total} total</b>
        <span>{type === "authorization" ? "Authorization Records" : `Folder: ${currentFolder.title}`} | Status: {filters.status} | Call Status: {filters.callStatus} | Tag: {filters.tagColor === "All Tags" ? "All" : filters.tagColor}{type === "authorization" ? ` | Attachment Updated: ${filters.attachmentDateRange}` : ""}</span>
      </p>

      {loadError && <div className="error">Could not load this lead list: {loadError}</div>}

      {!discovery && (
        <div className="leads-inline-options">
          <label className="check"><input type="checkbox" checked={filters.includeDeleted} onChange={(e) => patch("includeDeleted", e.target.checked)} />Show Deleted Leads</label>
          {!canAdmin && (
            <div className="segmented leads-view-toggle">
              <Button active={filters.onlyMine} onClick={() => patch("onlyMine", true)}>My {type === "referral" ? "Referrals" : "Leads"}</Button>
              <Button active={!filters.onlyMine} onClick={() => patch("onlyMine", false)}>All {type === "referral" ? "Referrals" : "Leads"}</Button>
            </div>
          )}
        </div>
      )}

      {loadingRows
        ? <LeadListSkeleton />
        : loadError
        ? null
        : data.rows.length
        ? data.rows.map((lead) => <LeadCard key={lead.id} lead={lead} type={type} onChanged={load} />)
        : <div className="info">{currentFolder.empty} Try a shorter search term, different spelling, phone, or ID.</div>}

      <div className="pagination">
        <Button disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</Button>
        <span>Page {page + 1} of {Math.max(1, Math.ceil(data.total / 10))}</span>
        <Button disabled={(page + 1) * 10 >= data.total} onClick={() => setPage(page + 1)}>Next</Button>
      </div>

      {customDateOpen && (
        <Modal title="Custom Date Range" onClose={() => setCustomDateOpen(false)}>
          <div className="custom-date-modal">
            <Field label="Start Date">
              <input type="date" value={customDateDraft.start} onChange={(e) => setCustomDateDraft((current) => ({ ...current, start: e.target.value }))} />
            </Field>
            <Field label="End Date">
              <input type="date" value={customDateDraft.end} onChange={(e) => setCustomDateDraft((current) => ({ ...current, end: e.target.value }))} />
            </Field>
            <div className="edit-lead-actions">
              <Button onClick={clearCustomDateRange}>Clear</Button>
              <Button onClick={() => setCustomDateOpen(false)}>Cancel</Button>
              <Button variant="primary" onClick={applyCustomDateRange}>Apply</Button>
            </div>
          </div>
        </Modal>
      )}

      {attachmentDateOpen && (
        <Modal title="Filter by Attachment Update" onClose={() => setAttachmentDateOpen(false)}>
          <div className="custom-date-modal">
            <Field label="Attachment Updated">
              <Select
                value={attachmentDateDraft.range}
                onChange={(range) => setAttachmentDateDraft((current) => ({ ...current, range }))}
                options={attachmentDateRangeOptions}
              />
            </Field>
            {attachmentDateDraft.range === "Custom" && (
              <>
                <Field label="Start Date">
                  <input type="date" value={attachmentDateDraft.start} onChange={(e) => setAttachmentDateDraft((current) => ({ ...current, start: e.target.value }))} />
                </Field>
                <Field label="End Date">
                  <input type="date" value={attachmentDateDraft.end} onChange={(e) => setAttachmentDateDraft((current) => ({ ...current, end: e.target.value }))} />
                </Field>
              </>
            )}
            <div className="edit-lead-actions">
              <Button onClick={clearAttachmentDateRange}>Clear</Button>
              <Button onClick={() => setAttachmentDateOpen(false)}>Cancel</Button>
              <Button variant="primary" onClick={applyAttachmentDateRange}>Apply</Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
