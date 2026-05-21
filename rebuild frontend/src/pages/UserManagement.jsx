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
  const [managementSearch, setManagementSearch] = useState("");
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
      })
      .catch((err) => {
        setLoadError(err.response?.data?.error || err.message || "Could not load user management data");
      });
  }
  useEffect(load, []);
  async function updateUser(id, patch) { await api.patch(`/users/${id}`, patch); load(); }
  async function createItem() {
    if (!newItem.name) return;
    await api.post(`/admin/${newItem.type}`, newItem);
    setNewItem({ type: newItem.type, name: "", address: "", phone: "", fax: "", email: "", street: "", city: "", state: "IL", zip_code: "", care_coordinator_name: "" });
    load();
  }
  async function deleteItem(type, id) { await api.delete(`/admin/${type}/${id}`); load(); }
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
  const pending = lookups.users.filter((u) => !u.is_approved);
  const resets = lookups.users.filter((u) => u.password_reset_requested);
  const approved = lookups.users.filter((u) => u.is_approved);
  const tabs = ["Pending Users", "Password Resets", "Approved Users", "Create User", "Payor", "CCU", "Events"];
  const managedItems = tab === "Payor" ? lookups.agencies : tab === "CCU" ? lookups.ccus : lookups.events;
  const searchNeedle = managementSearch.trim().toLowerCase();
  const filteredManagedItems = managedItems.filter((item) => !searchNeedle || Object.values(item).some((value) => String(value || "").toLowerCase().includes(searchNeedle)));
  const filteredApproved = approved.filter((user) => !searchNeedle || [user.id, user.user_id, user.username, user.email, user.role].some((value) => String(value || "").toLowerCase().includes(searchNeedle)));
  const valueOrDash = (value) => String(value || "").trim() || "Not added";
  const ccuAddress = (item) => [item.street, item.city, item.state, item.zip_code].filter(Boolean).join(", ") || "Not added";
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
    {["Payor", "CCU", "Events"].includes(tab) && <div className="form-panel">
      <div className="management-tools">
        <div>
          <h3>{tab === "CCU" ? "CCU Directory" : `Manage ${tab}`}</h3>
          {tab === "CCU" && <p className="management-subtitle">Add and review Case Coordination Units. These CCUs appear in lead, referral, and authorization dropdowns.</p>}
        </div>
        <input value={managementSearch} onChange={(e) => setManagementSearch(e.target.value)} placeholder={`Search ${tab.toLowerCase()}...`} />
      </div>

      {tab === "CCU" ? (
        <>
          <div className="ccu-entry-panel">
            <div className="ccu-entry-head">
              <div>
                <h4>Add New CCU</h4>
                <p>Name is required. Contact and address details help staff choose the correct CCU later.</p>
              </div>
              <span>{lookups.ccus.length} saved CCUs</span>
            </div>
            <div className="ccu-form-section">
              <h5>Basic Information</h5>
              <div className="form-grid ccu-form-grid">
                <Field label="CCU Name"><input value={newItem.name} onChange={(e) => setNewItem({ ...newItem, type: "ccu", name: e.target.value })} placeholder="e.g. DuPage County Department of Community Services" /></Field>
                <Field label="Care Coordinator"><input value={newItem.care_coordinator_name || ""} onChange={(e) => setNewItem({ ...newItem, type: "ccu", care_coordinator_name: e.target.value })} placeholder="Coordinator name" /></Field>
              </div>
            </div>
            <div className="ccu-form-section">
              <h5>Contact</h5>
              <div className="form-grid ccu-form-grid">
                <Field label="Phone"><input value={newItem.phone || ""} onChange={(e) => setNewItem({ ...newItem, type: "ccu", phone: e.target.value })} placeholder="Main phone number" /></Field>
                <Field label="Fax"><input value={newItem.fax || ""} onChange={(e) => setNewItem({ ...newItem, type: "ccu", fax: e.target.value })} placeholder="Fax number" /></Field>
                <Field label="Email"><input value={newItem.email || ""} onChange={(e) => setNewItem({ ...newItem, type: "ccu", email: e.target.value })} placeholder="CCU email" /></Field>
              </div>
            </div>
            <div className="ccu-form-section">
              <h5>Address</h5>
              <div className="form-grid ccu-form-grid">
                <Field label="Street"><input value={newItem.street || ""} onChange={(e) => setNewItem({ ...newItem, type: "ccu", street: e.target.value })} placeholder="Street address" /></Field>
                <Field label="City"><input value={newItem.city || ""} onChange={(e) => setNewItem({ ...newItem, type: "ccu", city: e.target.value })} placeholder="City" /></Field>
                <Field label="State"><input value={newItem.state || ""} onChange={(e) => setNewItem({ ...newItem, type: "ccu", state: e.target.value })} placeholder="IL" maxLength={2} /></Field>
                <Field label="ZIP Code"><input value={newItem.zip_code || ""} onChange={(e) => setNewItem({ ...newItem, type: "ccu", zip_code: e.target.value })} placeholder="ZIP" /></Field>
              </div>
            </div>
            <Button variant="primary" className="ccu-add-button" onClick={askCreateItem}>Add CCU</Button>
          </div>

          <div className="ccu-directory-list">
            <div className="ccu-directory-head">
              <h4>Saved CCUs</h4>
              <span>Showing {filteredManagedItems.length} of {lookups.ccus.length}</span>
            </div>
            {filteredManagedItems.length ? filteredManagedItems.map((item) => (
              <div className="ccu-directory-card" key={item.id}>
                <div className="ccu-directory-main">
                  <strong>{item.name}</strong>
                  <span>ID #{item.id}</span>
                </div>
                <div className="ccu-directory-details">
                  <p><b>Coordinator</b>{valueOrDash(item.care_coordinator_name)}</p>
                  <p><b>Phone</b>{valueOrDash(item.phone)}</p>
                  <p><b>Fax</b>{valueOrDash(item.fax)}</p>
                  <p><b>Email</b>{valueOrDash(item.email)}</p>
                  <p className="wide"><b>Address</b>{ccuAddress(item)}</p>
                </div>
                <Button onClick={() => askDeleteItem("ccu", item)}>Delete</Button>
              </div>
            )) : <div className="info">No CCUs match your search.</div>}
          </div>
        </>
      ) : (
        <>
          <div className="form-grid"><Field label="Name"><input value={newItem.name} onChange={(e) => setNewItem({ ...newItem, type: tab === "Payor" ? "agency" : "event", name: e.target.value })} /></Field>{tab === "Payor" && ["address","phone","fax","email"].map((key) => <Field key={key} label={key}><input value={newItem[key] || ""} onChange={(e) => setNewItem({ ...newItem, [key]: e.target.value })} /></Field>)}</div>
          <Button variant="primary" onClick={askCreateItem}>Add {tab}</Button>
          <div className="table-wrap"><table><thead><tr><th>Name</th><th>Complete Details</th><th>Action</th></tr></thead><tbody>{filteredManagedItems.map((item) => <tr key={item.id}><td>{item.name || item.event_name}</td><td>{tab === "Payor" ? [item.phone, item.fax, item.email, item.address].filter(Boolean).join(" | ") : item.event_name}</td><td><Button onClick={() => askDeleteItem(tab === "Payor" ? "agency" : "event", item)}>Delete</Button></td></tr>)}</tbody></table></div>
        </>
      )}
    </div>}
  </>;
}
