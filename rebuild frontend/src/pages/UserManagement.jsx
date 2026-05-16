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
  const [ccuMergeMasters, setCcuMergeMasters] = useState({});
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
  async function createItem() { if (!newItem.name) return; await api.post(`/admin/${newItem.type}`, newItem); setNewItem({ ...newItem, name: "" }); load(); }
  async function deleteItem(type, id) { await api.delete(`/admin/${type}/${id}`); load(); }
  async function loadCcuDuplicates() {
    const res = await api.get("/ccus/duplicates");
    setCcuDuplicateGroups(res.data.groups || []);
  }
  async function mergeCcuGroup(group) {
    const masterId = Number(ccuMergeMasters[group.key] || group.items[0]?.id);
    const duplicateIds = group.items.map((item) => item.id).filter((id) => Number(id) !== masterId);
    if (!masterId || !duplicateIds.length) return;
    await api.post("/ccus/merge", { masterId, duplicateIds });
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
  function askMergeCcuGroup(group) {
    confirmAction({
      title: "Merge Duplicate CCUs?",
      message: `Do you want to merge duplicate CCUs for ${group.name}?`,
      detail: "Leads attached to duplicate CCUs will be moved to the selected master CCU.",
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: () => mergeCcuGroup(group)
    });
  }
  const pending = lookups.users.filter((u) => !u.is_approved);
  const resets = lookups.users.filter((u) => u.password_reset_requested);
  const approved = lookups.users.filter((u) => u.is_approved);
  const tabs = ["Pending Users", "Password Resets", "Approved Users", "Create User", "Payor", "CCU", "Events"];
  return <><PageHeader>User Management</PageHeader>
    {loadError && <div className="error">User Management could not load: {loadError}</div>}
    <div className="tabs">{tabs.map((name) => <button key={name} className={tab === name ? "active" : ""} onClick={() => setTab(name)}>{name}</button>)}</div>
    {tab === "Pending Users" && <div className="form-panel"><h3>Pending User Approvals</h3>{pending.length ? pending.map((u) => <div className="admin-row" key={u.id}><div><b>Username:</b> {u.username}<br /><b>Email:</b> {u.email}<br /><b>Requested:</b> {new Date(u.created_at).toLocaleString()}</div><Button variant="primary" onClick={() => askUpdateUser(u.id, { is_approved: 1 }, `Do you want to approve ${u.username}?`)}>Approve</Button><Button onClick={() => askRejectUser(u)}>Reject</Button></div>) : <div className="info">No pending user approvals</div>}</div>}
    {tab === "Password Resets" && <div className="form-panel"><h3>Password Reset Requests</h3>{resets.length ? resets.map((u) => <div className="admin-row" key={u.id}><div><b>{u.username}</b><br />{u.email}</div><input type="password" placeholder="New Password" value={resetPasswords[u.id] || ""} onChange={(e) => setResetPasswords({ ...resetPasswords, [u.id]: e.target.value })} /><Button variant="primary" onClick={() => askResetPassword(u.id, u.username)}>Reset Password</Button></div>) : <div className="info">No password reset requests</div>}</div>}
    {tab === "Approved Users" && <div className="table-wrap"><table><thead><tr><th>ID</th><th>User ID</th><th>Username</th><th>Email</th><th>Role</th><th>Approved</th><th>Reset</th></tr></thead><tbody>{approved.map((u) => <tr key={u.id}><td>{u.id}</td><td><input defaultValue={u.user_id || ""} onBlur={(e) => e.target.value !== (u.user_id || "") && askUpdateUser(u.id, { user_id: e.target.value })} /></td><td><input defaultValue={u.username} onBlur={(e) => e.target.value !== u.username && askUpdateUser(u.id, { username: e.target.value })} /></td><td><input defaultValue={u.email} onBlur={(e) => e.target.value !== u.email && askUpdateUser(u.id, { email: e.target.value })} /></td><td><Select value={u.role} onChange={(v) => askUpdateUser(u.id, { role: v }, `Do you want to change ${u.username}'s role to ${v}?`)} options={["user", "admin"]} /></td><td><input type="checkbox" checked={!!u.is_approved} onChange={(e) => askUpdateUser(u.id, { is_approved: e.target.checked ? 1 : 0 }, `Do you want to ${e.target.checked ? "approve" : "unapprove"} ${u.username}?`)} /></td><td><input type="checkbox" checked={!!u.password_reset_requested} onChange={(e) => askUpdateUser(u.id, { password_reset_requested: e.target.checked ? 1 : 0 }, `Do you want to update password reset flag for ${u.username}?`)} /></td></tr>)}</tbody></table></div>}
    {tab === "Create User" && <div className="form-panel"><h3>Create New User</h3><div className="form-grid"><Field label="Username"><input value={newUser.username} onChange={(e) => setNewUser({ ...newUser, username: e.target.value })} /></Field><Field label="User ID"><input value={newUser.user_id} onChange={(e) => setNewUser({ ...newUser, user_id: e.target.value })} /></Field><Field label="Email"><input value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} /></Field><Field label="Password"><input type="password" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} /></Field><Field label="Confirm Password"><input type="password" value={newUser.confirm} onChange={(e) => setNewUser({ ...newUser, confirm: e.target.value })} /></Field><Field label="Role"><Select value={newUser.role} onChange={(v) => setNewUser({ ...newUser, role: v })} options={["user", "admin"]} /></Field></div><Button variant="primary" onClick={askCreateUser}>Create User</Button></div>}
    {["Payor", "CCU", "Events"].includes(tab) && <div className="form-panel"><h3>Manage {tab}</h3>{tab === "CCU" && <div className="source-block"><h3>Duplicate CCU Cleanup</h3><Button onClick={loadCcuDuplicates}>Scan Duplicate CCUs</Button>{ccuDuplicateGroups.length ? ccuDuplicateGroups.map((group) => <div className="admin-row" key={group.key}><div><b>{group.name}</b><br />{group.items.map((item) => `#${item.id} (${item.lead_count} leads)`).join(" | ")}</div><select value={ccuMergeMasters[group.key] || group.items[0].id} onChange={(e) => setCcuMergeMasters({ ...ccuMergeMasters, [group.key]: e.target.value })}>{group.items.map((item) => <option key={item.id} value={item.id}>Keep #{item.id} - {item.name} ({item.lead_count} leads)</option>)}</select><Button variant="primary" onClick={() => askMergeCcuGroup(group)}>Merge Duplicates</Button></div>) : <div className="info">No exact duplicate CCU names found. Use this scanner after adding/importing CCUs.</div>}</div>}<div className="form-grid"><Field label="Name"><input value={newItem.name} onChange={(e) => setNewItem({ ...newItem, type: tab === "Payor" ? "agency" : tab === "CCU" ? "ccu" : "event", name: e.target.value })} /></Field>{tab !== "Events" && ["address","phone","fax","email"].map((key) => <Field key={key} label={key}><input value={newItem[key] || ""} onChange={(e) => setNewItem({ ...newItem, [key]: e.target.value })} /></Field>)}</div><Button variant="primary" onClick={askCreateItem}>Add {tab}</Button><div className="table-wrap"><table><thead><tr><th>Name</th><th>Details</th><th>Action</th></tr></thead><tbody>{(tab === "Payor" ? lookups.agencies : tab === "CCU" ? lookups.ccus : lookups.events).map((item) => <tr key={item.id}><td>{item.name || item.event_name}</td><td>{item.phone || item.email || item.address || ""}</td><td><Button onClick={() => askDeleteItem(tab === "Payor" ? "agency" : tab === "CCU" ? "ccu" : "event", item)}>Delete</Button></td></tr>)}</tbody></table></div></div>}
  </>;
}
