import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { PageHeader, Button } from "../components/Controls";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import SmartSearch from "../components/SmartSearch";

const chartColors = ["#00506b", "#3CA5AA", "#B5E8F7", "#64748b", "#94a3b8"];
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

function ChartBox({ chartKey, title, data = [], type = "bar", filename, onDrill, drill, resolveRows }) {
  const clean = data.filter((item) => item.count > 0);
  return <div className="chart-box"><h3>{title}</h3>{clean.length ? <ResponsiveContainer width="100%" height={260}>{type === "line" ? <LineChart data={clean} onClick={(e) => e?.activePayload?.[0]?.payload && onDrill(chartKey, title, e.activePayload[0].payload)}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis /><Tooltip /><Line dataKey="count" stroke="#00506b" strokeWidth={3} /></LineChart> : <BarChart data={clean} onClick={(e) => e?.activePayload?.[0]?.payload && onDrill(chartKey, title, e.activePayload[0].payload)}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" interval={0} angle={-12} textAnchor="end" height={58} /><YAxis /><Tooltip /><Bar dataKey="count" fill="#00506b" /></BarChart>}</ResponsiveContainer> : <div className="info">No data</div>}<button className="download-link" onClick={() => downloadCsv(clean.flatMap((item) => resolveRows(item)), filename)}>Download CSV</button><DrillDown drill={drill?.chartKey === chartKey ? drill : null} /></div>;
}

function PieBox({ chartKey, title, data = [], filename, onDrill, drill, resolveRows }) {
  const clean = data.filter((item) => item.count > 0);
  return <div className="chart-box"><h3>{title}</h3>{clean.length ? <ResponsiveContainer width="100%" height={300}><PieChart><Tooltip /><Pie data={clean} dataKey="count" nameKey="name" innerRadius={62} outerRadius={105} paddingAngle={2} onClick={(entry) => onDrill(chartKey, title, entry)}>{clean.map((entry, index) => <Cell key={entry.name} fill={chartColors[index % chartColors.length]} />)}</Pie></PieChart></ResponsiveContainer> : <div className="info">No data</div>}<div className="pie-text-labels">{clean.map((entry, index) => <span key={entry.name} style={{ "--label-color": chartColors[index % chartColors.length] }}>{entry.name}</span>)}</div><button className="download-link" onClick={() => downloadCsv(clean.flatMap((item) => resolveRows(item)), filename)}>Download CSV</button><DrillDown drill={drill?.chartKey === chartKey ? drill : null} /></div>;
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
  if (!data?.stats || !data?.charts) return <div className="page-loader">Loading dashboard...</div>;
  if (showUsers) return <><PageHeader>ALL USER DASHBOARDS</PageHeader><Button onClick={() => setShowUsers(false)}>Back to Dashboard</Button>{data.userDashboards?.length ? <div className="user-dashboard-list">{data.userDashboards.map((dash) => <details className="user-dashboard" key={dash.user.id}><summary>{dash.user.username} Dashboard</summary><div className="stats compact"><div><b>{dash.stats.total_leads}</b><span>Total Leads</span></div><div><b>{dash.stats.referrals}</b><span>Referrals</span></div></div><div className="chart-grid"><ChartBox chartKey={`${dash.user.id}-source`} title="Source" data={dash.source} filename={`${dash.user.username}_source.csv`} onDrill={onDrill} drill={drill} resolveRows={resolveRows} /><ChartBox chartKey={`${dash.user.id}-status`} title="Status" data={dash.status} filename={`${dash.user.username}_status.csv`} onDrill={onDrill} drill={drill} resolveRows={resolveRows} /></div></details>)}</div> : <div className="page-loader">Loading user dashboards...</div>}</>;
  return <div className="dashboard-page">
    <PageHeader>PERFORMANCE METRICS DASHBOARD</PageHeader>
    <section className="dashboard-hero">
      <div className="dashboard-copy">
        <h2>Welcome back, {user.username}</h2>
        <p>Search, manage and track your leads all in one place.</p>
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
      <ChartBox chartKey="primary-staff-or-month" title={mode === "cumulative" ? "Leads by Staff" : "Your Monthly Lead Flow"} data={mode === "cumulative" ? data.charts.staff : data.charts.month} type={mode === "cumulative" ? "bar" : "line"} filename={mode === "cumulative" ? "staff_leads_all.csv" : "your_monthly_leads.csv"} onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
      <ChartBox chartKey="primary-source" title={mode === "cumulative" ? "Leads by Source" : "Your Content Sources"} data={data.charts.source} filename={mode === "cumulative" ? "source_leads_all.csv" : "your_source_breakdown.csv"} onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
    </div>
    <h2 className="section-title">Detailed Referral Distribution</h2>
    <div className="chart-grid">
      <ChartBox chartKey="ccu-sent" title="Referrals sent by CCU" data={data.charts.ccuSent} filename="referrals_sent_detailed.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
      <ChartBox chartKey="ccu-confirmed" title="Authorizations received from CCUs" data={data.charts.ccuConfirmed} filename="authorizations_received.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
      <ChartBox chartKey="status" title={mode === "cumulative" ? "Leads by Status" : "Your Leads by Status"} data={data.charts.status} filename="status_breakdown.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
      <ChartBox chartKey="month" title={mode === "cumulative" ? "Monthly Leads (All)" : "Your Monthly Flow"} data={data.charts.month} type="line" filename={mode === "cumulative" ? "monthly_leads_all.csv" : "your_monthly_flow.csv"} onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
      <ChartBox chartKey="event" title={mode === "cumulative" ? "Event Leads" : "Your Event Leads"} data={data.charts.event} filename="event_leads_detailed.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
      <ChartBox chartKey="word-of-mouth" title={mode === "cumulative" ? "Word of Mouth Breakdown" : "Your WOM Breakdown"} data={data.charts.wordOfMouth} filename="wom_leads_detailed.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
      <ChartBox chartKey="priority" title={mode === "cumulative" ? "Priority Distribution" : "Your Priority Mix"} data={data.charts.priority} filename="priority_distribution.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
      <ChartBox chartKey="auth" title={mode === "cumulative" ? "Authorization Status" : "Your Auth Status"} data={data.charts.auth} filename="auth_status_detailed.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
    </div>
    <div className="pipeline-header"><h2>LEAD PIPELINE ANALYTICS</h2></div>
    <div className="chart-grid">
      <PieBox chartKey="lead-confirmation" title="Lead Confirmation" data={data.charts.referralConfirmation} filename="lead_confirmation_data.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
      <PieBox chartKey="lead-conversion" title="Lead Conversion" data={data.charts.leadConversion} filename="lead_conversion_data.csv" onDrill={onDrill} drill={drill} resolveRows={resolveRows} />
    </div>
    <div className="rate-cards"><div><b>{data.rates.confirmation.toFixed(1)}%</b><span>{mode === "cumulative" ? "Confirmation Rate" : "Your Confirmation Rate"}</span></div><div><b>{data.rates.conversion.toFixed(1)}%</b><span>{mode === "cumulative" ? "Conversion Rate" : "Your Conversion Rate"}</span></div></div>
  </div>;
}
