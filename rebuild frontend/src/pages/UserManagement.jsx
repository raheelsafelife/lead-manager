import { useEffect, useState } from "react";
import { Button, Field, PageHeader, Select } from "../components/Controls";
import { useConfirm } from "../components/ConfirmProvider";
import { api } from "../services/api";

export default function UserManagement() {
  const confirmAction = useConfirm();
  const [lookups, setLookups] = useState({ users: [], agencies: [], ccus: [], events: [] });
  const [loadError, setLoadError] = useState("");
  const [tab, setTab] = useState("Pending Users");
  const [newItem, setNewItem] = useState({ type: "event", name: "", address: "", phone: "", fax: "", email: "", street: "", city: "", state: "IL", zip_code: "", care_coordinator_name: "" });
  const [newUser, setNewUser] = useState({ username: "", user_id: "", email: "", password: "", confirm: "", role: "user" });
  const [resetPasswords, setResetPasswords] = useState({});
  const [ccuDuplicateGroups, setCcuDuplicateGroups] = useState([]);
  const [managementSearch, setManagementSearch] = useState("");
  const [duplicateGroupSort, setDuplicateGroupSort] = useState("Most Linked");
  const [duplicateItemSort, setDuplicateItemSort] = useState("Future Default First");
  function load() {
    api.get("/lookups")
      .then((res) => {
        setLookups({
          users: res.data.users || [],
          agencies: res.data.agencies || [],
          ccus: res.data.ccus || [],
          events: res.data.events || []
        });
        setLoadError("");
        if (tab === "CCU") loadCcuDuplicates();
      })
      .catch((err) => {
        setLoadError(err.response?.data?.error || err.message || "Could not load user management data");
      });
  }
  useEffect(load, []);
  useEffect(() => { if (tab === "CCU") loadCcuDuplicates(); }, [tab]);
  async function updateUser(id, patch) { await api.patch(`/users/${id}`, patch); load(); }
  async function createItem() {
    if (!newItem.name) return;
    await api.post(`/admin/${newItem.type}`, newItem);
    setNewItem({ type: newItem.type, name: "", address: "", phone: "", fax: "", email: "", street: "", city: "", state: "IL", zip_code: "", care_coordinator_name: "" });
    load();
  }
  async function deleteItem(type, id) { await api.delete(`/admin/${type}/${id}`); load(); }
  async function loadCcuDuplicates() {
    const res = await api.get("/ccus/duplicates");
    setCcuDuplicateGroups(res.data.groups || []);
  }
  async function setPreferredCcu(id) {
    await api.post(`/ccus/${id}/preferred-suggestion`);
    await loadCcuDuplicates();
    load();
  }
  async function createUser() {
    if (newUser.password !== newUser.confirm) return;
    await api.post("/users", newUser);
    setNewUser({ username: "", user_id: "", email: "", password: "", confirm: "", role: "user" });
    load();
  }
  async function resetPassword(id) {
    if (!resetPasswords[id]) return;
    await api.post(`/users/${id}/reset-password`, { password: resetPasswords[id] });
    setResetPasswords({ ...resetPasswords, [id]: "" });
    load();
  }
  function askUpdateUser(id, patch, message = "Do you want to update this user?") {
    confirmAction({
      title: "Update User?",
      message,
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: () => updateUser(id, patch)
    });
  }
  function askCreateUser() {
    if (newUser.password !== newUser.confirm) return;
    confirmAction({
      title: "Create User?",
      message: `Do you want to create user ${newUser.username || newUser.email}?`,
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: createUser
    });
  }
  function askResetPassword(id, username) {
    if (!resetPasswords[id]) return;
    confirmAction({
      title: "Reset Password?",
      message: `Do you want to reset password for ${username}?`,
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: () => resetPassword(id)
    });
  }
  function askRejectUser(user) {
    confirmAction({
      title: "Reject User?",
      message: `Do you want to reject ${user.username}?`,
      confirmText: "Yes",
      cancelText: "No",
      variant: "danger",
      onConfirm: async () => {
        await api.delete(`/users/${user.id}`);
        load();
      }
    });
  }
  function askCreateItem() {
    if (!newItem.name) return;
    confirmAction({
      title: `Add ${tab}?`,
      message: `Do you want to create ${tab} ${newItem.name}?`,
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: createItem
    });
  }
  function askDeleteItem(type, item) {
    confirmAction({
      title: `Delete ${tab}?`,
      message: `Do you want to delete ${item.name || item.event_name}?`,
      confirmText: "Yes",
      cancelText: "No",
      variant: "danger",
      onConfirm: () => deleteItem(type, item.id)
    });
  }
  function askSetPreferredCcu(item) {
    confirmAction({
      title: "Use This CCU For Future Leads?",
      message: `Do you want future dropdowns to use ${item.name}?`,
      detail: "This does not change existing leads, referrals, or authorizations.",
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: () => setPreferredCcu(item.id)
    });
  }
  const pending = lookups.users.filter((u) => !u.is_approved);
  const resets = lookups.users.filter((u) => u.password_reset_requested);
  const approved = lookups.users.filter((u) => u.is_approved);
  const tabs = ["Pending Users", "Password Resets", "Approved Users", "Create User", "Payor", "CCU", "Events"];
  const managedItems = tab === "Payor" ? lookups.agencies : tab === "CCU" ? lookups.ccus : lookups.events;
  const searchNeedle = managementSearch.trim().toLowerCase();
  const filteredManagedItems = managedItems.filter((item) => !searchNeedle || Object.values(item).some((value) => String(value || "").toLowerCase().includes(searchNeedle)));
  const filteredApproved = approved.filter((user) => !searchNeedle || [user.id, user.user_id, user.username, user.email, user.role].some((value) => String(value || "").toLowerCase().includes(searchNeedle)));
  const duplicateGroups = [...ccuDuplicateGroups].sort((a, b) => {
    const aLinks = a.items.reduce((sum, item) => sum + Number(item.lead_count || 0), 0);
    const bLinks = b.items.reduce((sum, item) => sum + Number(item.lead_count || 0), 0);
    if (duplicateGroupSort === "Name A-Z") return String(a.name || "").localeCompare(String(b.name || ""));
    if (duplicateGroupSort === "Most Options") return b.items.length - a.items.length || String(a.name || "").localeCompare(String(b.name || ""));
    return bLinks - aLinks || String(a.name || "").localeCompare(String(b.name || ""));
  });
  function sortedDuplicateItems(items) {
    return [...items].sort((a, b) => {
      if (duplicateItemSort === "Most Linked") return Number(b.lead_count || 0) - Number(a.lead_count || 0) || Number(a.id) - Number(b.id);
      if (duplicateItemSort === "ID / Area") return Number(a.id) - Number(b.id);
      if (duplicateItemSort === "Name A-Z") return String(a.name || "").localeCompare(String(b.name || ""));
      return Number(b.is_preferred_suggestion || 0) - Number(a.is_preferred_suggestion || 0) || Number(b.lead_count || 0) - Number(a.lead_count || 0) || Number(a.id) - Number(b.id);
    });
  }
  return <><PageHeader>User Management</PageHeader>
    {loadError && <div className="error">User Management could not load: {loadError}</div>}
    <div className="management-summary-grid">
      <div><b>{pending.length}</b><span>Pending Users</span></div>
      <div><b>{approved.length}</b><span>Approved Users</span></div>
      <div><b>{lookups.agencies.length}</b><span>Payors</span></div>
      <div><b>{lookups.ccus.length}</b><span>CCUs</span></div>
    </div>
    <div className="tabs">{tabs.map((name) => <button key={name} className={tab === name ? "active" : ""} onClick={() => setTab(name)}>{name}</button>)}</div>
    {tab === "Pending Users" && <div className="form-panel"><h3>Pending User Approvals</h3>{pending.length ? pending.map((u) => <div className="admin-row" key={u.id}><div><b>Username:</b> {u.username}<br /><b>Email:</b> {u.email}<br /><b>Requested:</b> {new Date(u.created_at).toLocaleString()}</div><Button variant="primary" onClick={() => askUpdateUser(u.id, { is_approved: 1 }, `Do you want to approve ${u.username}?`)}>Approve</Button><Button onClick={() => askRejectUser(u)}>Reject</Button></div>) : <div className="info">No pending user approvals</div>}</div>}
    {tab === "Password Resets" && <div className="form-panel"><h3>Password Reset Requests</h3>{resets.length ? resets.map((u) => <div className="admin-row" key={u.id}><div><b>{u.username}</b><br />{u.email}</div><input type="password" placeholder="New Password" value={resetPasswords[u.id] || ""} onChange={(e) => setResetPasswords({ ...resetPasswords, [u.id]: e.target.value })} /><Button variant="primary" onClick={() => askResetPassword(u.id, u.username)}>Reset Password</Button></div>) : <div className="info">No password reset requests</div>}</div>}
    {tab === "Approved Users" && <div className="form-panel"><div className="management-tools"><h3>Approved Users</h3><input value={managementSearch} onChange={(e) => setManagementSearch(e.target.value)} placeholder="Search users..." /></div><div className="table-wrap"><table><thead><tr><th>ID</th><th>User ID</th><th>Username</th><th>Email</th><th>Role</th><th>Approved</th><th>Reset</th></tr></thead><tbody>{filteredApproved.map((u) => <tr key={u.id}><td>{u.id}</td><td><input defaultValue={u.user_id || ""} onBlur={(e) => e.target.value !== (u.user_id || "") && askUpdateUser(u.id, { user_id: e.target.value })} /></td><td><input defaultValue={u.username} onBlur={(e) => e.target.value !== u.username && askUpdateUser(u.id, { username: e.target.value })} /></td><td><input defaultValue={u.email} onBlur={(e) => e.target.value !== u.email && askUpdateUser(u.id, { email: e.target.value })} /></td><td><Select value={u.role} onChange={(v) => askUpdateUser(u.id, { role: v }, `Do you want to change ${u.username}'s role to ${v}?`)} options={["user", "admin"]} /></td><td><input type="checkbox" checked={!!u.is_approved} onChange={(e) => askUpdateUser(u.id, { is_approved: e.target.checked ? 1 : 0 }, `Do you want to ${e.target.checked ? "approve" : "unapprove"} ${u.username}?`)} /></td><td><input type="checkbox" checked={!!u.password_reset_requested} onChange={(e) => askUpdateUser(u.id, { password_reset_requested: e.target.checked ? 1 : 0 }, `Do you want to update password reset flag for ${u.username}?`)} /></td></tr>)}</tbody></table></div></div>}
    {tab === "Create User" && <div className="form-panel"><h3>Create New User</h3><div className="form-grid"><Field label="Username"><input value={newUser.username} onChange={(e) => setNewUser({ ...newUser, username: e.target.value })} /></Field><Field label="User ID"><input value={newUser.user_id} onChange={(e) => setNewUser({ ...newUser, user_id: e.target.value })} /></Field><Field label="Email"><input value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} /></Field><Field label="Password"><input type="password" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} /></Field><Field label="Confirm Password"><input type="password" value={newUser.confirm} onChange={(e) => setNewUser({ ...newUser, confirm: e.target.value })} /></Field><Field label="Role"><Select value={newUser.role} onChange={(v) => setNewUser({ ...newUser, role: v })} options={["user", "admin"]} /></Field></div><Button variant="primary" onClick={askCreateUser}>Create User</Button></div>}
    {["Payor", "CCU", "Events"].includes(tab) && <div className="form-panel"><div className="management-tools"><h3>Manage {tab}</h3><input value={managementSearch} onChange={(e) => setManagementSearch(e.target.value)} placeholder={`Search ${tab.toLowerCase()}...`} /></div>{tab === "CCU" && <div className="source-block"><h3>Duplicate CCU Suggestions</h3><p className="muted-text">Pick which CCU should appear in future dropdowns. Existing lead, referral, and authorization records are not changed.</p><div className="ccu-duplicate-toolbar"><Button onClick={loadCcuDuplicates}>Scan Duplicate CCUs</Button><label><span>Sort groups</span><Select value={duplicateGroupSort} onChange={setDuplicateGroupSort} options={["Most Linked", "Most Options", "Name A-Z"]} /></label><label><span>Sort inside group</span><Select value={duplicateItemSort} onChange={setDuplicateItemSort} options={["Future Default First", "Most Linked", "ID / Area", "Name A-Z"]} /></label></div>{duplicateGroups.length ? duplicateGroups.map((group) => <div className="ccu-duplicate-card" key={group.key}><div className="ccu-duplicate-head"><div><b>{group.name}</b><small>Normalized match: {group.normalizedName}</small></div><span>{group.items.length} options · {group.items.reduce((sum, item) => sum + Number(item.lead_count || 0), 0)} linked records</span></div><div className="ccu-duplicate-options">{sortedDuplicateItems(group.items).map((item) => <div className={`ccu-preferred-option ${Number(item.is_preferred_suggestion) === 1 ? "preferred" : ""}`} key={item.id}><div><b>#{item.id} {item.name}</b><span>{item.lead_count} linked records</span></div>{Number(item.is_preferred_suggestion) === 1 ? <strong>Future Default</strong> : <Button onClick={() => askSetPreferredCcu(item)}>Use for Future Leads</Button>}</div>)}</div></div>) : <div className="info">No duplicate CCU names found with the cleanup scanner.</div>}</div>}<div className="form-grid"><Field label="Name"><input value={newItem.name} onChange={(e) => setNewItem({ ...newItem, type: tab === "Payor" ? "agency" : tab === "CCU" ? "ccu" : "event", name: e.target.value })} /></Field>{tab === "Payor" && ["address","phone","fax","email"].map((key) => <Field key={key} label={key}><input value={newItem[key] || ""} onChange={(e) => setNewItem({ ...newItem, [key]: e.target.value })} /></Field>)}{tab === "CCU" && ["street","city","state","zip_code","phone","fax","email","care_coordinator_name"].map((key) => <Field key={key} label={key.replaceAll("_", " ")}><input value={newItem[key] || ""} onChange={(e) => setNewItem({ ...newItem, type: "ccu", [key]: e.target.value })} /></Field>)}</div><Button variant="primary" onClick={askCreateItem}>Add {tab}</Button><div className="table-wrap"><table><thead><tr><th>Name</th><th>Complete Details</th><th>Action</th></tr></thead><tbody>{filteredManagedItems.map((item) => <tr key={item.id}><td>{item.name || item.event_name}{tab === "CCU" && Number(item.is_preferred_suggestion) === 1 ? " • Future Default" : ""}</td><td>{tab === "CCU" ? [item.care_coordinator_name, item.phone, item.fax, item.email, [item.street, item.city, item.state, item.zip_code].filter(Boolean).join(", ")].filter(Boolean).join(" | ") : tab === "Payor" ? [item.phone, item.fax, item.email, item.address].filter(Boolean).join(" | ") : item.event_name}</td><td><Button onClick={() => askDeleteItem(tab === "Payor" ? "agency" : tab === "CCU" ? "ccu" : "event", item)}>Delete</Button></td></tr>)}</tbody></table></div></div>}
  </>;
}
