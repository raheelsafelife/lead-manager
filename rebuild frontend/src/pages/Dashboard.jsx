import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { PageHeader, Button } from "../components/Controls";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import SmartSearch from "../components/SmartSearch";
import { DashboardSkeleton, SkeletonTable } from "../components/Skeleton";

const chartColors = ["#00506b", "#3CA5AA", "#7C91B0", "#54B56B", "#E39D17", "#D95F59", "#8B5CF6"];
const tableCols = ["id", "full_name", "phone", "source", "last_contact_status", "staff_name", "created_at", "ccu_name"];

function csvValue(value) {
  const text = value == null ? "" : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

function downloadCsv(rows, filename) {
  const csv = [tableCols.join(","), ...rows.map((row) => tableCols.map((col) => csvValue(row[col])).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function buildRowResolver(data) {
  const byId = new Map((data?.rows || []).map((row) => [String(row.id), row]));
  return (item) => {
    if (item?.rows) return item.rows;
    return (item?.rowIds || []).map((id) => byId.get(String(id))).filter(Boolean);
  };
}

function DrillDown({ drill }) {
  if (!drill) return null;
  return <div className="drilldown"><h3>Drill Down: {drill.title} ({drill.rows.length})</h3><div className="table-wrap"><table><thead><tr>{tableCols.map((col) => <th key={col}>{col.replaceAll("_", " ")}</th>)}</tr></thead><tbody>{drill.rows.slice(0, 100).map((row) => <tr key={row.id}>{tableCols.map((col) => <td key={col}>{row[col] || "N/A"}</td>)}</tr>)}</tbody></table></div></div>;
}

function shortName(value = "", max = 28) {
  const text = String(value || "N/A");
  return text.length > max ? `${text.slice(0, max - 1)}...` : text;
}

function compactTop(data = [], limit = 10) {
  const clean = data.filter((item) => item.count > 0);
  if (clean.length <= limit) return clean;
  const top = clean.slice(0, limit);
  const rest = clean.slice(limit);
  return [...top, {
    name: "Other",
    count: rest.reduce((sum, item) => sum + item.count, 0),
    rowIds: rest.flatMap((item) => item.rowIds || []),
    rows: rest.flatMap((item) => item.rows || [])
  }];
}

function ChartShell({ chartKey, title, data, filename, resolveRows, drill, children }) {
  const clean = data.filter((item) => item.count > 0);
  return <div className="chart-box dashboard-chart-card"><div className="chart-card-head"><h3>{title}</h3><span>{clean.length} groups</span></div>{clean.length ? children(clean) : <div className="info">No data</div>}<button className="download-link" onClick={() => downloadCsv(clean.flatMap((item) => resolveRows(item)), filename)}>Download CSV</button><DrillDown drill={drill?.chartKey === chartKey ? drill : null} /></div>;
}

function HorizontalRankChart({ chartKey, title, data = [], filename, onDrill, drill, resolveRows, limit = 10, accent = "#00506b", tall = false }) {
  const ranked = compactTop(data, limit).map((item) => ({ ...item, label: shortName(item.name, 30) }));
  const height = Math.max(tall ? 360 : 280, ranked.length * 34 + 48);
  return <ChartShell chartKey={chartKey} title={title} data={ranked} filename={filename} resolveRows={resolveRows} drill={drill}>{(clean) => (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart layout="vertical" data={clean} margin={{ top: 8, right: 34, bottom: 8, left: 138 }} onClick={(e) => e?.activePayload?.[0]?.payload && onDrill(chartKey, title, e.activePayload[0].payload)}>
        <CartesianGrid horizontal={false} stroke="#e4edf3" />
        <XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} />
        <YAxis type="category" dataKey="label" width={132} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#475467" }} />
        <Tooltip formatter={(value) => [value, "Count"]} labelFormatter={(_label, payload) => payload?.[0]?.payload?.name || ""} />
        <Bar dataKey="count" fill={accent} radius={[0, 8, 8, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )}</ChartShell>;
}

function DonutChartBox({ chartKey, title, data = [], filename, onDrill, drill, resolveRows, limit = 6 }) {
  const cleanData = compactTop(data, limit);
  return <ChartShell chartKey={chartKey} title={title} data={cleanData} filename={filename} resolveRows={resolveRows} drill={drill}>{(clean) => (
    <div className="donut-layout">
      <ResponsiveContainer width="48%" height={260}>
        <PieChart>
          <Tooltip formatter={(value) => [value, "Count"]} />
          <Pie data={clean} dataKey="count" nameKey="name" innerRadius={62} outerRadius={98} paddingAngle={2} onClick={(entry) => onDrill(chartKey, title, entry)}>
            {clean.map((entry, index) => <Cell key={entry.name} fill={chartColors[index % chartColors.length]} />)}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="donut-legend">
        {clean.map((entry, index) => <button key={entry.name} onClick={() => onDrill(chartKey, title, entry)}><span style={{ "--legend-color": chartColors[index % chartColors.length] }} /> <b>{shortName(entry.name, 24)}</b><em>{entry.count}</em></button>)}
      </div>
    </div>
  )}</ChartShell>;
}

function LineChartBox({ chartKey, title, data = [], filename, onDrill, drill, resolveRows }) {
  const clean = data.filter((item) => item.count > 0);
  return <ChartShell chartKey={chartKey} title={title} data={clean} filename={filename} resolveRows={resolveRows} drill={drill}>{(chartData) => (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={chartData} margin={{ top: 16, right: 24, bottom: 8, left: 0 }} onClick={(e) => e?.activePayload?.[0]?.payload && onDrill(chartKey, title, e.activePayload[0].payload)}>
        <CartesianGrid stroke="#e4edf3" vertical={false} />
        <XAxis dataKey="name" tickLine={false} axisLine={false} />
        <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
        <Tooltip formatter={(value) => [value, "Leads"]} />
        <Line type="monotone" dataKey="count" stroke="#3CA5AA" strokeWidth={4} dot={{ r: 4, fill: "#00506b" }} activeDot={{ r: 7 }} />
      </LineChart>
    </ResponsiveContainer>
  )}</ChartShell>;
}

function StatCard({ value, label }) {
  return <div className="dashboard-stat-card"><b>{value}</b><span>{label}</span></div>;
}

export default function Dashboard() {
  const { user } = useAuth();
  const [mode, setMode] = useState(user.role === "admin" ? "cumulative" : "individual");
  const [data, setData] = useState(null);
  const [drill, setDrill] = useState(null);
  const [showUsers, setShowUsers] = useState(false);
  const [loadError, setLoadError] = useState("");
  const resolveRows = buildRowResolver(data);

  useEffect(() => {
    let mounted = true;
    setLoadError("");
    api.get("/dashboard", { params: { mode } })
      .then((res) => {
        if (!mounted) return;
        if (!res.data?.stats || !res.data?.charts) {
          setLoadError("Dashboard data came back in an unexpected format.");
          return;
        }
        setData(res.data);
      })
      .catch((error) => {
        if (!mounted) return;
        setLoadError(error?.response?.data?.error || error.message || "Failed to load dashboard.");
      });
    return () => {
      mounted = false;
    };
  }, [mode]);
  function onDrill(chartKey, title, payload) {
    const nextTitle = `${title}: ${payload.name}`;
    if (drill?.chartKey === chartKey && drill?.title === nextTitle) {
      setDrill(null);
      return;
    }
    setDrill({ chartKey, title: nextTitle, rows: resolveRows(payload) });
  }
  async function showAllUserDashboards() {
    setShowUsers(true);
    if (data.userDashboards?.length) return;
    const res = await api.get("/dashboard", { params: { mode: "cumulative", includeUsers: "true" } });
    setData(res.data);
  }
  if (loadError) return <div className="error">Lead Manager failed to load: {loadError}</div>;
  if (!data?.stats || !data?.charts) return <DashboardSkeleton />;
  if (showUsers) return <><PageHeader>User Performance</PageHeader><Button onClick={() => setShowUsers(false)}>Back to Dashboard</Button>{data.userDashboards?.length ? <div className="user-dashboard-list">{data.userDashboards.map((dash) => <details className="user-dashboard" key={dash.user.id}><summary>{dash.user.username}</summary><div className="stats compact"><div><b>{dash.stats.total_leads}</b><span>Total Leads</span></div><div><b>{dash.stats.referrals}</b><span>Referrals</span></div></div><div className="chart-grid"><HorizontalRankChart chartKey={`${dash.user.id}-source`} title="Sources" data={dash.source} filename={`${dash.user.username}_source.csv`} onDrill={onDrill} drill={drill} resolveRows={resolveRows} /><DonutChartBox chartKey={`${dash.user.id}-status`} title="Statuses" data={dash.status} filename={`${dash.user.username}_status.csv`} onDrill={onDrill} drill={drill} resolveRows={resolveRows} /></div></details>)}</div> : <SkeletonTable rows={4} columns={3} />}</>;
  return <div className="dashboard-page">
    <PageHeader>Performance Dashboard</PageHeader>
    <section className="dashboard-hero">
      <div className="dashboard-copy">
        <h2>Welcome back, {user.username}</h2>
        <p>Monitor lead flow, referral progress, and authorization outcomes from one workspace.</p>
      </div>
      <SmartSearch />
      <div className="dashboard-actions">
        {user.role !== "admin" && <div className="segmented dashboard-mode-toggle"><Button active={mode === "individual"} onClick={() => setMode("individual")}>Individual</Button><Button active={mode === "cumulative"} onClick={() => setMode("cumulative")}>Cumulative</Button></div>}
        {user.role === "admin" && <Button variant="primary" onClick={showAllUserDashboards}>View All User Dashboards</Button>}
      </div>
    </section>
    <div className="stats dashboard-stats">
      <StatCard value={data.stats.total_leads} label={mode === "cumulative" ? "Total Leads" : "Your Leads"} />
      <StatCard value={data.stats.total_users} label="Total Users" />
      <StatCard value={data.stats.active_clients} label="Referrals" />
    </div>
    <div className="chart-grid dashboard-primary-grid">
      {mode === "cumulative"
        ? <HorizontalRankChart chartKey="primary-staff-or-month" title="Top Staff by Leads" data={data.charts.staff} filename="staff_leads_all.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} limit={12} accent="#00506b" />
        : <LineChartBox chartKey="primary-staff-or-month" title="Your Monthly Lead Flow" data={data.charts.month} filename="your_monthly_leads.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />}
      <DonutChartBox chartKey="primary-source" title={mode === "cumulative" ? "Leads by Source" : "Your Lead Sources"} data={data.charts.source} filename={mode === "cumulative" ? "source_leads_all.csv" : "your_source_breakdown.csv"} onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
    </div>
    <h2 className="section-title">Referral and Authorization Breakdown</h2>
    <div className="chart-grid">
      <HorizontalRankChart chartKey="ccu-sent" title="Top CCUs by Referrals Sent" data={data.charts.ccuSent} filename="referrals_sent_detailed.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} limit={10} accent="#3CA5AA" tall />
      <HorizontalRankChart chartKey="ccu-confirmed" title="Top CCUs by Authorizations" data={data.charts.ccuConfirmed} filename="authorizations_received.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} limit={10} accent="#54B56B" tall />
      <DonutChartBox chartKey="status" title={mode === "cumulative" ? "Leads by Status" : "Your Leads by Status"} data={data.charts.status} filename="status_breakdown.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
      <LineChartBox chartKey="month" title={mode === "cumulative" ? "Monthly Leads" : "Your Monthly Flow"} data={data.charts.month} filename={mode === "cumulative" ? "monthly_leads_all.csv" : "your_monthly_flow.csv"} onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
      <HorizontalRankChart chartKey="event" title={mode === "cumulative" ? "Event Leads" : "Your Event Leads"} data={data.charts.event} filename="event_leads_detailed.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} limit={8} accent="#7C91B0" />
      <DonutChartBox chartKey="word-of-mouth" title={mode === "cumulative" ? "Word of Mouth Breakdown" : "Your WOM Breakdown"} data={data.charts.wordOfMouth} filename="wom_leads_detailed.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
      <DonutChartBox chartKey="priority" title={mode === "cumulative" ? "Priority Distribution" : "Your Priority Mix"} data={data.charts.priority} filename="priority_distribution.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
      <DonutChartBox chartKey="auth" title={mode === "cumulative" ? "Authorization Status" : "Your Auth Status"} data={data.charts.auth} filename="auth_status_detailed.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
    </div>
    <div className="pipeline-header"><h2>Pipeline Analytics</h2></div>
    <div className="chart-grid">
      <DonutChartBox chartKey="lead-confirmation" title="Lead Confirmation" data={data.charts.referralConfirmation} filename="lead_confirmation_data.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
      <DonutChartBox chartKey="lead-conversion" title="Lead Conversion" data={data.charts.leadConversion} filename="lead_conversion_data.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
    </div>
    <div className="rate-cards"><div><b>{data.rates.confirmation.toFixed(1)}%</b><span>{mode === "cumulative" ? "Confirmation Rate" : "Your Confirmation Rate"}</span></div><div><b>{data.rates.conversion.toFixed(1)}%</b><span>{mode === "cumulative" ? "Conversion Rate" : "Your Conversion Rate"}</span></div></div>
  </div>;
}
