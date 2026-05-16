import { useState } from "react";
import { Button, Field, PageHeader } from "../components/Controls";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";

export default function UserSettings() {
  const { user, setUser } = useAuth();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ username: user.username, user_id: user.user_id || "", email: user.email, profile_pic: user.profile_pic || "" });
  const [passwords, setPasswords] = useState({ currentPassword: "", newPassword: "", confirmPassword: "" });
  const [message, setMessage] = useState("");
  async function saveProfile() {
    const res = await api.patch("/users/me", form);
    setUser(res.data.user);
    setEditing(false);
    setMessage("Identity updated successfully.");
  }
  function uploadPicture(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setForm((f) => ({ ...f, profile_pic: reader.result }));
    reader.readAsDataURL(file);
  }
  async function changePassword() {
    if (passwords.newPassword !== passwords.confirmPassword) { setMessage("New passwords do not match."); return; }
    try {
      await api.post("/users/me/password", passwords);
      setPasswords({ currentPassword: "", newPassword: "", confirmPassword: "" });
      setMessage("Password updated successfully.");
    } catch (err) {
      setMessage(err.response?.data?.error || "Password update failed.");
    }
  }
  async function requestReset() {
    await api.post("/users/me/request-reset");
    setMessage("Your reset request has been sent to the administrators.");
  }
  return <><PageHeader>User Profile & Security</PageHeader>{message && <div className="info">{message}</div>}
    <div className="profile-grid">
      <div className="form-panel">
        <div className="avatar">{form.profile_pic ? <img src={form.profile_pic} alt="Profile" /> : <span>{user.username.slice(0, 1).toUpperCase()}</span>}</div>
        <Field label="Change Picture"><input type="file" accept="image/png,image/jpeg" onChange={uploadPicture} /></Field>
        {form.profile_pic !== (user.profile_pic || "") && <Button variant="primary" onClick={saveProfile}>Save New Picture</Button>}
      </div>
      <div className="form-panel">
        <div className="toolbar"><h3>Account Details</h3><Button onClick={() => setEditing(!editing)}>{editing ? "Cancel" : "Edit"}</Button></div>
        {editing ? <div className="form-grid"><Field label="Username"><input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></Field><Field label="Employee ID"><input value={form.user_id} onChange={(e) => setForm({ ...form, user_id: e.target.value })} /></Field><Field label="Email Address"><input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field><Button variant="primary" onClick={saveProfile}>Save Changes</Button></div> : <><p><b>Username:</b> {user.username}</p><p><b>Employee ID:</b> {user.user_id || "N/A"}</p><p><b>Email Address:</b> {user.email}</p><p><b>Role:</b> {user.role}</p></>}
      </div>
      <div className="form-panel">
        <h3>Change Password</h3>
        <Field label="Current Password"><input type="password" value={passwords.currentPassword} onChange={(e) => setPasswords({ ...passwords, currentPassword: e.target.value })} /></Field>
        <Field label="New Password (min 6 characters)"><input type="password" value={passwords.newPassword} onChange={(e) => setPasswords({ ...passwords, newPassword: e.target.value })} /></Field>
        <Field label="Confirm New Password"><input type="password" value={passwords.confirmPassword} onChange={(e) => setPasswords({ ...passwords, confirmPassword: e.target.value })} /></Field>
        <Button variant="primary" onClick={changePassword}>Update Password</Button>
      </div>
      <div className="form-panel">
        <h3>Account Recovery</h3><p>If you've forgotten your current password or need a complete reset, request an administrative reset.</p>
        <Button onClick={requestReset}>Request Account Reset</Button>
      </div>
    </div>
  </>;
}
