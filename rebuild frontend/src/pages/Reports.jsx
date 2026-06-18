import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import ExcelJS from "exceljs";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { Download, FileSpreadsheet, FileText, ShieldCheck, HeartHandshake, Layers3, Sparkles } from "lucide-react";
import { Button, Select } from "../components/Controls";
import { api } from "../services/api";
import { ReportsSkeleton } from "../components/Skeleton";

const topOptions = ["5", "10", "20"];
const dateRangeOptions = ["All Time", "Today", "Last 7 Days", "Last 30 Days"];
const formatOptions = ["Excel (.xlsx)", "Word (.docx)", "PDF (.pdf)"];
const formatValueByLabel = {
  "Excel (.xlsx)": "excel",
  "Word (.docx)": "word",
  "PDF (.pdf)": "pdf"
};
const chartColors = ["#0b6f87", "#15a3b4", "#5fb9c4", "#7c91b0", "#94a3b8", "#dce8ef"];
const reportCategories = [
  "Community Care Unit (CCU)",
  "Top Staff Leaderboard",
  "Top Sources",
  "Referral Report",
  "Authorization Report",
  "Leads Report",
  "Activity Logs",
  "Payor Report",
  "Care Start Report"
];

function saveBlob(blob, fileName) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function createdDate(value) {
  const date = new Date(String(value || "").replace(" ", "T"));
  return Number.isNaN(date.getTime()) ? null : date;
}

function startForDateFilter(filter) {
  const d = new Date();
  if (filter === "Today") d.setHours(0, 0, 0, 0);
  else if (filter === "Last 7 Days") d.setDate(d.getDate() - 7);
  else if (filter === "Last 30 Days") d.setDate(d.getDate() - 30);
  else return null;
  return d;
}

function inSelectedRange(value, filter) {
  if (filter === "All Time") return true;
  const date = createdDate(value);
  const start = startForDateFilter(filter);
  if (!date || !start) return false;
  return date >= start;
}

function leadName(row) {
  return `${row.first_name || ""} ${row.last_name || ""}`.trim() || "N/A";
}

function isReferral(row) {
  return Number(row.active_client) === 1;
}

function isAuthorization(row) {
  return isReferral(row) && Number(row.authorization_received) === 1;
}

function isCareStart(row) {
  return isAuthorization(row) && row.care_status === "Care Start";
}

function isLeadStage(row) {
  return !isReferral(row);
}

function isReferralStage(row) {
  return isReferral(row) && !isAuthorization(row);
}

function isAuthorizationStage(row) {
  return isAuthorization(row) && !isCareStart(row);
}

function sourceLabel(row) {
  const source = String(row.source || "").trim();
  return source.toLowerCase() === "hhn" ? "Home Health Notify" : source || "N/A";
}

function groupCounts(rows, accessor) {
  const grouped = {};
  rows.forEach((row) => {
    const name = accessor(row) || "N/A";
    grouped[name] = grouped[name] || { name, count: 0, rows: [] };
    grouped[name].count += 1;
    grouped[name].rows.push(row);
  });
  return Object.values(grouped).sort((a, b) => b.count - a.count);
}

function formatDateTime(value) {
  const date = createdDate(value);
  return date ? date.toLocaleString() : "N/A";
}

function categoryConfig(category) {
  switch (category) {
    case "Community Care Unit (CCU)":
      return {
        scope: "lead",
        filter: isReferralStage,
        groupLabel: "CCU Name",
        groupBy: (row) => row.ccu_name || "N/A"
      };
    case "Top Staff Leaderboard":
      return {
        scope: "lead",
        filter: isLeadStage,
        groupLabel: "Staff",
        groupBy: (row) => row.staff_name || "Unassigned"
      };
    case "Top Sources":
      return {
        scope: "lead",
        filter: isLeadStage,
        groupLabel: "Source",
        groupBy: sourceLabel
      };
    case "Referral Report":
      return {
        scope: "lead",
        filter: isReferralStage,
        groupLabel: "Source",
        groupBy: sourceLabel
      };
    case "Authorization Report":
      return {
        scope: "lead",
        filter: isAuthorizationStage,
        groupLabel: "CCU Name",
        groupBy: (row) => row.ccu_name || "N/A"
      };
    case "Leads Report":
      return {
        scope: "lead",
        filter: isLeadStage,
        groupLabel: "Source",
        groupBy: sourceLabel
      };
    case "Activity Logs":
      return {
        scope: "activity",
        filter: () => true,
        groupLabel: "Action Type",
        groupBy: (row) => row.action_type || "N/A"
      };
    case "Payor Report":
      return {
        scope: "lead",
        filter: isReferralStage,
        groupLabel: "Payor",
        groupBy: (row) => row.agency_name || "N/A"
      };
    case "Care Start Report":
      return {
        scope: "lead",
        filter: isCareStart,
        groupLabel: "Staff",
        groupBy: (row) => row.staff_name || "Unassigned"
      };
    default:
      return {
        scope: "lead",
        filter: isLeadStage,
        groupLabel: "Source",
        groupBy: sourceLabel
      };
  }
}

function buildLeadExportRows(rows) {
  return rows.map((row) => ({
    ID: row.id,
    Name: leadName(row),
    Staff: row.staff_name || "N/A",
    Source: row.source || "N/A",
    Status: row.last_contact_status || "N/A",
    "Call Status": row.priority || "N/A",
    Phone: row.phone || "N/A",
    Payor: row.agency_name || "N/A",
    CCU: row.ccu_name || "N/A",
    Created: formatDateTime(row.created_at),
    Updated: formatDateTime(row.updated_at)
  }));
}

function buildActivityExportRows(rows) {
  return rows.map((row) => ({
    Timestamp: formatDateTime(row.timestamp),
    User: row.username || "N/A",
    "Action Type": row.action_type || "N/A",
    "Entity Type": row.entity_type || "N/A",
    Entity: row.entity_name || "N/A",
    Description: row.description || "N/A"
  }));
}

async function exportExcel(title, rows) {
  const workbook = new ExcelJS.Workbook();
  const sheet = workbook.addWorksheet("Report");
  const columns = Object.keys(rows[0] || { Empty: "" });
  sheet.columns = columns.map((header) => ({ header, key: header, width: Math.max(16, header.length + 4) }));
  rows.forEach((row) => sheet.addRow(row));
  const headerRow = sheet.getRow(1);
  headerRow.font = { bold: true };
  headerRow.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FFDBF3F6" } };
  sheet.insertRow(1, [title]);
  sheet.mergeCells(1, 1, 1, columns.length);
  sheet.getCell("A1").font = { bold: true, size: 16 };
  const buffer = await workbook.xlsx.writeBuffer();
  saveBlob(new Blob([buffer], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), `${title.toLowerCase().replaceAll(/[^a-z0-9]+/gi, "_")}.xlsx`);
}

async function exportWord(title, rows) {
  const response = await api.post("/reports/word", { title, rows }, { responseType: "blob" });
  saveBlob(new Blob([response.data], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" }), `${title.toLowerCase().replaceAll(/[^a-z0-9]+/gi, "_")}.docx`);
}

async function exportPdf(title, rows) {
  const doc = new jsPDF({ orientation: "landscape" });
  doc.setFontSize(18);
  doc.text(title, 14, 18);
  const columns = Object.keys(rows[0] || { Empty: "" });
  autoTable(doc, {
    startY: 28,
    head: [columns],
    body: rows.map((row) => columns.map((column) => String(row[column] ?? "N/A"))),
    styles: { fontSize: 8, cellPadding: 2.5 },
    headStyles: { fillColor: [11, 111, 135] }
  });
  doc.save(`${title.toLowerCase().replaceAll(/[^a-z0-9]+/gi, "_")}.pdf`);
}

function MetricCard({ icon: Icon, tintClass, label, value, note }) {
  return (
    <article className="reports-metric-card">
      <span className={`reports-metric-icon ${tintClass}`}><Icon size={22} /></span>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
        <small>{note}</small>
      </div>
    </article>
  );
}

export default function Reports() {
  const [dashboard, setDashboard] = useState(null);
  const [activityRows, setActivityRows] = useState([]);
  const [category, setCategory] = useState("Community Care Unit (CCU)");
  const [topN, setTopN] = useState(5);
  const [dateRange, setDateRange] = useState("All Time");
  const [formatLabel, setFormatLabel] = useState("Excel (.xlsx)");
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    let mounted = true;
    Promise.all([
      api.get("/dashboard", { params: { mode: "cumulative" } }),
      api.get("/activity", { params: { limit: 1000, offset: 0 } })
    ]).then(([dashboardRes, activityRes]) => {
      if (!mounted) return;
      setDashboard(dashboardRes.data);
      setActivityRows(activityRes.data.rows || []);
    });
    return () => {
      mounted = false;
    };
  }, []);

  const scopedData = useMemo(() => {
    const config = categoryConfig(category);
    if (!dashboard?.rows) return { config, filteredRows: [], grouped: [], leaderboard: [], chartOne: [], chartTwo: [], exportRows: [], detailColumns: [], kpis: [] };

    const allLeadRows = dashboard.rows.filter((row) => inSelectedRange(row.created_at || row.updated_at, dateRange));
    const leadStageRows = allLeadRows.filter(isLeadStage);
    const referralStageRows = allLeadRows.filter(isReferralStage);
    const authorizationStageRows = allLeadRows.filter(isAuthorizationStage);
    const careStartRows = allLeadRows.filter(isCareStart);
    const leadKpis = {
      totalLeads: leadStageRows.length,
      referrals: referralStageRows.length,
      authorizations: authorizationStageRows.length,
      careStarts: careStartRows.length
    };

    if (config.scope === "activity") {
      const filteredRows = activityRows.filter((row) => inSelectedRange(row.timestamp, dateRange)).filter(config.filter);
      const grouped = groupCounts(filteredRows, config.groupBy);
      const leaderboard = grouped.slice(0, topN).map((entry, index) => ({
        ...entry,
        rank: index + 1,
        share: filteredRows.length ? ((entry.count / filteredRows.length) * 100).toFixed(1) : "0.0"
      }));
      const selectedNames = new Set(leaderboard.map((entry) => entry.name));
      const detailRows = filteredRows.filter((row) => selectedNames.has(config.groupBy(row) || "N/A"));
      return {
        config,
        filteredRows,
        grouped,
        leaderboard,
        chartOne: leaderboard.map((entry) => ({ name: entry.name, count: entry.count })),
        chartTwo: groupCounts(filteredRows, (row) => row.entity_type || "N/A").slice(0, 6),
        exportRows: buildActivityExportRows(detailRows),
        detailColumns: ["Timestamp", "User", "Action Type", "Entity Type", "Entity", "Description"],
        kpis: [
          { icon: Layers3, tintClass: "tone-aqua", label: "Activity Entries", value: filteredRows.length.toLocaleString(), note: "matching selected range" },
          { icon: FileText, tintClass: "tone-blue", label: "Active Users", value: new Set(filteredRows.map((row) => row.username || "Unknown")).size.toLocaleString(), note: "users in this log scope" },
          { icon: ShieldCheck, tintClass: "tone-green", label: "Unique Actions", value: grouped.length.toLocaleString(), note: "action types captured" },
          { icon: Sparkles, tintClass: "tone-violet", label: "Showing Top", value: String(topN), note: "leaderboard groups" }
        ]
      };
    }

    const filteredRows = allLeadRows.filter(config.filter);
    const grouped = groupCounts(filteredRows, config.groupBy);
    const leaderboard = grouped.slice(0, topN).map((entry, index) => ({
      ...entry,
      rank: index + 1,
      share: filteredRows.length ? ((entry.count / filteredRows.length) * 100).toFixed(1) : "0.0"
    }));
    const selectedNames = new Set(leaderboard.map((entry) => entry.name));
    const detailRows = filteredRows.filter((row) => selectedNames.has(config.groupBy(row) || "N/A"));
    return {
      config,
      filteredRows,
      grouped,
      leaderboard,
      chartOne: leaderboard.map((entry) => ({ name: entry.name, count: entry.count })),
      chartTwo: groupCounts(filteredRows, sourceLabel).slice(0, 6),
      exportRows: buildLeadExportRows(detailRows),
      detailColumns: ["ID", "Name", "Staff", "Source", "Status", "Call Status", "Phone", "Payor", "CCU", "Created", "Updated"],
      kpis: [
        { icon: Layers3, tintClass: "tone-aqua", label: "Total Leads", value: leadKpis.totalLeads.toLocaleString(), note: "selected date range" },
        { icon: HeartHandshake, tintClass: "tone-blue", label: "Referrals Sent", value: leadKpis.referrals.toLocaleString(), note: "active referral pipeline" },
        { icon: ShieldCheck, tintClass: "tone-green", label: "Authorizations", value: leadKpis.authorizations.toLocaleString(), note: "approved client cases" },
        { icon: Sparkles, tintClass: "tone-violet", label: "Care Starts", value: leadKpis.careStarts.toLocaleString(), note: "care start conversions" }
      ]
    };
  }, [activityRows, category, dashboard, dateRange, topN]);

  async function generateReport() {
    if (!scopedData.exportRows.length) return;
    setGenerating(true);
    try {
      const title = `${category} Report`;
      const format = formatValueByLabel[formatLabel];
      if (format === "excel") await exportExcel(title, scopedData.exportRows);
      else if (format === "word") await exportWord(title, scopedData.exportRows);
      else await exportPdf(title, scopedData.exportRows);
    } finally {
      setGenerating(false);
    }
  }

  if (!dashboard) return <ReportsSkeleton />;

  return (
    <div className="reports-page">
      <div className="reports-page-head">
        <span>Home / Reports</span>
        <h2>Reports</h2>
        <p>Generate, analyze and export operational reports from one clean reporting workspace.</p>
      </div>

      <section className="reports-generator-card">
        <div className="reports-generator-head">
          <div className="reports-generator-badge"><FileSpreadsheet size={20} /></div>
          <div>
            <h3>Report Generator</h3>
            <p>Pick the report type, top range, date range, and final format from one unified flow.</p>
          </div>
        </div>

        <div className="reports-generator-grid">
          <label className="reports-control">
            <span>Report Category</span>
            <Select value={category} onChange={setCategory} options={reportCategories} />
          </label>
          <label className="reports-control">
            <span>Show Top</span>
            <Select value={String(topN)} onChange={(value) => setTopN(Number(value))} options={topOptions} />
          </label>
          <label className="reports-control">
            <span>Date Range</span>
            <Select value={dateRange} onChange={setDateRange} options={dateRangeOptions} />
          </label>
          <label className="reports-control">
            <span>Download Format</span>
            <Select value={formatLabel} onChange={setFormatLabel} options={formatOptions} />
          </label>
          <div className="reports-generate-action">
            <Button variant="primary" onClick={generateReport} disabled={generating || !scopedData.exportRows.length}>
              <Download size={18} />
              {generating ? "Generating..." : "Generate Report"}
            </Button>
          </div>
        </div>
      </section>

      <section className="reports-metrics-grid">
        {scopedData.kpis.map((item) => <MetricCard key={item.label} {...item} />)}
      </section>

      <section className="reports-analysis-grid">
        <article className="reports-section-card">
          <div className="reports-section-head">
            <div>
              <h3>Top {topN} {category}</h3>
              <p>Leaderboard ranked by {scopedData.config.groupLabel.toLowerCase()} volume.</p>
            </div>
          </div>
          <div className="reports-leaderboard-wrap">
            <table className="reports-leaderboard-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>{scopedData.config.groupLabel}</th>
                  <th>Volume</th>
                  <th>Share</th>
                </tr>
              </thead>
              <tbody>
                {scopedData.leaderboard.map((entry) => (
                  <tr key={entry.name}>
                    <td>#{entry.rank}</td>
                    <td>{entry.name}</td>
                    <td>{entry.count}</td>
                    <td>{entry.share}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!scopedData.leaderboard.length && <div className="info">No data available for this report selection.</div>}
          </div>
        </article>

        <article className="reports-section-card">
          <div className="reports-section-head">
            <div>
              <h3>Analytics Snapshot</h3>
              <p>Visual mix for the selected report scope and date range.</p>
            </div>
          </div>
          <div className="reports-chart-grid">
            <div className="reports-chart-card">
              <h4>Top Group Distribution</h4>
              {scopedData.chartOne.length ? (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={scopedData.chartOne}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" interval={0} angle={-12} textAnchor="end" height={58} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                      {scopedData.chartOne.map((entry, index) => <Cell key={entry.name} fill={chartColors[index % chartColors.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : <div className="info">No chart data available.</div>}
            </div>

            <div className="reports-chart-card">
              <h4>Source Mix</h4>
              {scopedData.chartTwo.length ? (
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Tooltip />
                    <Pie data={scopedData.chartTwo} dataKey="count" nameKey="name" innerRadius={56} outerRadius={92} paddingAngle={2}>
                      {scopedData.chartTwo.map((entry, index) => <Cell key={entry.name} fill={chartColors[index % chartColors.length]} />)}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              ) : <div className="info">No chart data available.</div>}
            </div>
          </div>
        </article>
      </section>

      <section className="reports-section-card reports-detail-card">
        <div className="reports-section-head">
          <div>
            <h3>Detailed Report Table</h3>
            <p>Operational detail rows included in the generated export.</p>
          </div>
        </div>
        <div className="table-wrap reports-table-wrap">
          <table className="reports-detail-table">
            <thead>
              <tr>
                {scopedData.detailColumns.map((column) => <th key={column}>{column}</th>)}
              </tr>
            </thead>
            <tbody>
              {scopedData.exportRows.slice(0, 25).map((row, index) => (
                <tr key={`${row.ID || row.Timestamp || "row"}-${index}`}>
                  {scopedData.detailColumns.map((column) => <td key={column}>{row[column] ?? "N/A"}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
