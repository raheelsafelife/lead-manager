import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Button, PageHeader, Select } from "../components/Controls";
import { api } from "../services/api";
import { DiscoverySkeleton } from "../components/Skeleton";

const featureMap = {
  "Lead Source": "source",
  "Staff Name": "staff_name",
  "Contact Status": "last_contact_status",
  "Priority": "priority",
  "CCU": "ccu_name",
  "Care Status": "care_status",
  "Active Client": "active_client",
  "Referral Type": "referral_type",
  "City": "city",
  "Authorization": "authorization_received",
  "Medicaid Status": "medicaid_status"
};
const displayValue = (value, key) => {
  if (key === "active_client") return Number(value) === 1 ? "True" : "False";
  if (key === "authorization_received") return Number(value) === 1 ? "Authorized" : "Pending";
  return value || "N/A";
};
const tableCols = ["id", "full_name", "phone", "source", "last_contact_status", "staff_name", "created_at", "ccu_name"];

function downloadCsv(rows) {
  const csv = [tableCols.join(","), ...rows.map((row) => tableCols.map((col) => `"${String(row[col] || "").replaceAll('"', '""')}"`).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "discovery_leads_detailed.csv";
  link.click();
  URL.revokeObjectURL(url);
}

export default function LeadDiscovery() {
  const [data, setData] = useState(null);
  const [xFeature, setXFeature] = useState("Lead Source");
  const [colorFeature, setColorFeature] = useState("None");
  const [drill, setDrill] = useState(null);
  useEffect(() => { api.get("/dashboard", { params: { mode: "individual" } }).then((res) => setData(res.data)); }, []);

  const chart = useMemo(() => {
    if (!data) return { rows: [], colorKeys: [] };
    const xKey = featureMap[xFeature];
    const cKey = featureMap[colorFeature];
    if (!cKey || cKey === xKey) {
      const grouped = {};
      data.rows.forEach((row) => {
        const name = displayValue(row[xKey], xKey);
        grouped[name] = grouped[name] || { name, Count: 0, rows: [] };
        grouped[name].Count += 1;
        grouped[name].rows.push(row);
      });
      return { rows: Object.values(grouped), colorKeys: ["Count"] };
    }
    const grouped = {};
    const colors = new Set();
    data.rows.forEach((row) => {
      const name = displayValue(row[xKey], xKey);
      const color = displayValue(row[cKey], cKey);
      colors.add(color);
      grouped[name] = grouped[name] || { name, rows: [], colorRows: {} };
      grouped[name][color] = (grouped[name][color] || 0) + 1;
      grouped[name].rows.push(row);
      grouped[name].colorRows[color] = grouped[name].colorRows[color] || [];
      grouped[name].colorRows[color].push(row);
    });
    return { rows: Object.values(grouped), colorKeys: [...colors] };
  }, [data, xFeature, colorFeature]);

  if (!data) return <DiscoverySkeleton />;
  const xKey = featureMap[xFeature];
  return <><PageHeader>Lead Discovery</PageHeader>
    <div className="filter-grid">
      <label className="field"><span>Split By (X-Axis):</span><Select value={xFeature} onChange={setXFeature} options={Object.keys(featureMap)} /></label>
      <label className="field"><span>Compare Against (Color):</span><Select value={colorFeature} onChange={setColorFeature} options={["None", ...Object.keys(featureMap)]} /></label>
    </div>
    <div className="chart-box">
      <ResponsiveContainer width="100%" height={390}>
        <BarChart data={chart.rows} onClick={(e) => {
          const payload = e?.activePayload?.[0];
          if (!payload) return;
          const base = payload.payload;
          const rows = base.colorRows?.[payload.dataKey] || base.rows || [];
          setDrill({ title: `Discovery: ${xFeature}=${base.name}${payload.dataKey !== "Count" ? `, ${colorFeature}=${payload.dataKey}` : ""}`, rows });
        }}>
          <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" interval={0} angle={-15} textAnchor="end" height={70} /><YAxis /><Tooltip /><Legend />
          {chart.colorKeys.map((key, index) => <Bar key={key} dataKey={key} fill={["#00506b", "#3CA5AA", "#B5E8F7", "#64748b", "#94a3b8"][index % 5]} />)}
        </BarChart>
      </ResponsiveContainer>
      <Button onClick={() => downloadCsv(data.rows)}>Download CSV</Button>
    </div>
    {drill && <div className="drilldown"><h3>{drill.title} ({drill.rows.length})</h3><div className="table-wrap"><table><thead><tr>{tableCols.map((col) => <th key={col}>{col.replaceAll("_", " ")}</th>)}</tr></thead><tbody>{drill.rows.map((row) => <tr key={row.id}>{tableCols.map((col) => <td key={col}>{row[col] || "N/A"}</td>)}</tr>)}</tbody></table></div></div>}
  </>;
}
