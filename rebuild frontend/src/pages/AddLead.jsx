import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertOctagon, ExternalLink } from "lucide-react";
import { Button, Field, Modal, PageHeader, Select } from "../components/Controls";
import { useConfirm } from "../components/ConfirmProvider";
import { api } from "../services/api";
import { leadSources, leadStatuses, referralStatuses } from "../utils/constants";
import { useAuth } from "../context/AuthContext";
import { emitToast, refreshAppSignals } from "../utils/appEvents";

const blank = { source: "Home Health Notify", staff_name: "", custom_user_id: "", first_name: "", last_name: "", phone: "", email: "", gender: "", state: "IL", last_contact_status: "Initial Call", priority: "Not Called" };
const genderOptions = ["Male", "Female", "Other"];

function existingLeadPath(lead) {
  if (!lead) return "/view-leads";
  const query = new URLSearchParams({ idSearch: String(lead.id) });
  if (lead.deleted_at) {
    query.set("includeDeleted", "true");
    return `/view-leads?${query.toString()}`;
  }
  if (Number(lead.authorization_received) === 1) {
    if (lead.source === "Transfer" && lead.care_status !== "Care Start") query.set("transferView", "true");
    return `/authorizations?${query.toString()}`;
  }
  if (Number(lead.active_client) === 1) return `/referrals?${query.toString()}`;
  return `/view-leads?${query.toString()}`;
}

function duplicateStatus(lead) {
  if (!lead) return "Lead";
  if (Number(lead.authorization_received) === 1) return lead.care_status || "Authorization";
  if (Number(lead.active_client) === 1) return lead.last_contact_status || "Referral";
  return lead.last_contact_status || "Lead";
}

function duplicateFolderLabel(lead) {
  const status = duplicateStatus(lead);
  if (Number(lead.authorization_received) === 1) return status;
  if (Number(lead.active_client) === 1) return status;
  return status;
}

function duplicateBucket(lead) {
  const status = duplicateStatus(lead);
  if (["Initial Call", "No Response", "Initial Referral Sent", "Assessment Scheduled", "Assessment Done", "Care Start", "Not Start", "Transfer", "Transfer Received"].includes(status)) return "Active";
  return "Inactive";
}

export default function AddLead() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const confirmAction = useConfirm();
  const [lookups, setLookups] = useState({ approvedUsers: [], agencies: [], agencySuboptions: [], ccus: [], events: [] });
  const [form, setForm] = useState(blank);
  const [message, setMessage] = useState("");
  const [ccuNotice, setCcuNotice] = useState("");
  const [duplicate, setDuplicate] = useState(null);
  const [newEvent, setNewEvent] = useState("");
  const [newPayor, setNewPayor] = useState({ name: "", address: "", phone: "", fax: "", email: "" });
  const [newCcu, setNewCcu] = useState({ name: "", street: "", city: "", state: "IL", zip_code: "", phone: "", fax: "", email: "", care_coordinator_name: "" });
  const [ccuDetailsOpen, setCcuDetailsOpen] = useState(false);
  const [ccuEditForm, setCcuEditForm] = useState({ name: "", street: "", city: "", state: "IL", zip_code: "", phone: "", fax: "", email: "", care_coordinator_name: "" });
  useEffect(() => { api.get("/lookups").then((res) => { setLookups(res.data); if (user.role !== "admin") setForm((f) => ({ ...f, staff_name: user.username, custom_user_id: user.user_id || "", owner_id: user.id })); }); }, []);
  useEffect(() => {
    const selected = lookups.approvedUsers.find((u) => u.username === form.staff_name);
    if (selected) setForm((f) => ({ ...f, custom_user_id: selected.user_id || "", owner_id: selected.id }));
  }, [form.staff_name]);
  useEffect(() => {
    if (!form.ccu_id) {
      setCcuDetailsOpen(false);
      return;
    }
    const ccu = lookups.ccus.find((entry) => String(entry.id) === String(form.ccu_id));
    if (!ccu) return;
    setCcuDetailsOpen(true);
    setCcuEditForm({
      name: ccu.name || "",
      street: ccu.street || "",
      city: ccu.city || "",
      state: ccu.state || "IL",
      zip_code: ccu.zip_code || "",
      phone: ccu.phone || "",
      fax: ccu.fax || "",
      email: ccu.email || "",
      care_coordinator_name: ccu.care_coordinator_name || ""
    });
  }, [form.ccu_id, lookups.ccus]);

  function showMessage(text, type = "error") {
    setMessage(text);
    emitToast({ type, message: text });
  }

  function patch(key, value) {
    if (key === "ccu_id") setCcuNotice("");
    const next = { ...form, [key]: value };
    if (key === "dob" && value) {
      const birth = new Date(value);
      const today = new Date();
      next.age = today.getFullYear() - birth.getFullYear() - ((today.getMonth() + 1 < birth.getMonth() + 1 || (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())) ? 1 : 0);
    }
    if (key === "source") {
      const isReferral = ["Direct Through CCU", "Transfer"].includes(value);
      next.last_contact_status = value === "Transfer" ? "Care Start" : isReferral ? "Initial Referral Sent" : "Initial Call";
      next.active_client = isReferral ? 1 : 0;
      next.authorization_received = value === "Transfer" || value === "Direct Through CCU" ? 1 : 0;
      next.care_status = value === "Transfer" ? "Transfer Received" : null;
    }
    setForm(next);
  }

  async function submit(override = {}) {
    setMessage("");
    setDuplicate(null);
    for (const key of ["staff_name", "custom_user_id", "first_name", "last_name", "source", "phone"]) {
      if (!form[key]) { showMessage(`Missing Required Fields - Please fill in: ${key.replaceAll("_", " ")}`); return; }
    }
    try {
      const res = await api.post("/leads", { ...form, ...override });
      emitToast({ type: "success", message: "Lead created successfully" });
      refreshAppSignals();
      navigate(`/view-leads?idSearch=${res.data.lead.id}`);
    } catch (err) {
      if (err.response?.status === 409) {
        setDuplicate(err.response.data);
        emitToast({ type: "warning", message: err.response.data?.error || "Duplicate lead found" });
      } else showMessage(err.response?.data?.error || "Unable to save lead");
    }
  }

  function validateBeforeConfirm() {
    setMessage("");
    for (const key of ["staff_name", "custom_user_id", "first_name", "last_name", "source", "phone"]) {
      if (!form[key]) { showMessage(`Missing Required Fields - Please fill in: ${key.replaceAll("_", " ")}`); return; }
    }
    if (form.source === "Event" && !form.event_name) { showMessage("Event Required - Please select an Event"); return; }
    if (form.source === "Direct Through CCU" && !form.agency_id) { showMessage("Payor Required - Please select a Payor"); return; }
    if (form.source === "Other" && !form.other_source_type) { showMessage("Source Type Required - Please specify Source Type"); return; }
    if (form.source === "Transfer" && !form.soc_date) { showMessage("SOC Date Required - SOC Date is required for Transfer source"); return; }
    confirmAction({
      title: "Create Lead?",
      message: `Do you want to create lead ${form.first_name} ${form.last_name}?`,
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: () => submit()
    });
  }

  async function refreshLookups() {
    const res = await api.get("/lookups");
    setLookups(res.data);
  }

  async function addEvent() {
    if (!newEvent.trim()) return;
    await api.post("/admin/event", { name: newEvent.trim() });
    setNewEvent("");
    await refreshLookups();
    patch("event_name", newEvent.trim());
  }

  function confirmAddEvent() {
    if (!newEvent.trim()) return;
    confirmAction({
      title: "Add Event?",
      message: `Do you want to create event ${newEvent.trim()}?`,
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: addEvent
    });
  }

  async function addPayor() {
    if (!newPayor.name.trim()) return;
    await api.post("/admin/agency", newPayor);
    const name = newPayor.name;
    setNewPayor({ name: "", address: "", phone: "", fax: "", email: "" });
    await refreshLookups();
    const agency = (await api.get("/lookups")).data.agencies.find((a) => a.name === name);
    if (agency) patch("agency_id", agency.id);
  }

  function confirmAddPayor() {
    if (!newPayor.name.trim()) return;
    confirmAction({
      title: "Add Payor?",
      message: `Do you want to create payor ${newPayor.name.trim()}?`,
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: addPayor
    });
  }

  async function addCcu() {
    if (!newCcu.name.trim()) return;
    await api.post("/admin/ccu", newCcu);
    const name = newCcu.name;
    setNewCcu({ name: "", street: "", city: "", state: "IL", zip_code: "", phone: "", fax: "", email: "", care_coordinator_name: "" });
    await refreshLookups();
    const ccu = (await api.get("/lookups")).data.ccus.find((c) => c.name === name);
    if (ccu) patch("ccu_id", ccu.id);
  }

  function confirmAddCcu() {
    if (!newCcu.name.trim()) return;
    confirmAction({
      title: "Add CCU?",
      message: `Do you want to create CCU ${newCcu.name.trim()}?`,
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: addCcu
    });
  }

  async function updateSelectedCcu() {
    if (!form.ccu_id) return;
    await api.patch(`/ccus/${form.ccu_id}`, ccuEditForm);
    await refreshLookups();
    setCcuDetailsOpen(false);
    setCcuNotice("CCU details updated successfully.");
  }

  function confirmUpdateSelectedCcu() {
    if (!form.ccu_id) return;
    confirmAction({
      title: "Update CCU?",
      message: "Do you want to update this CCU's details?",
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: updateSelectedCcu
    });
  }

  const isReferralSource = ["Direct Through CCU", "Transfer"].includes(form.source);
  const duplicateLead = duplicate?.duplicate || duplicate?.deletedDuplicate;
  return <><PageHeader>Add New Lead</PageHeader>
    {message && <div className="error">{message}</div>}
    {ccuNotice && <div className="info">{ccuNotice}</div>}
    {duplicate && duplicateLead && <Modal onClose={() => setDuplicate(null)}>
      <div className="duplicate-lead-modal">
        <div className="duplicate-lead-heading">
          <AlertOctagon size={42} />
          <h2>Duplicate Lead Detected!</h2>
        </div>
        <div className="duplicate-lead-alert">
          <p><b>{duplicateLead.first_name} {duplicateLead.last_name}</b> already exists as {duplicateStatus(duplicateLead)}.</p>
          <p>Duplicate leads are blocked by the system by default.</p>
        </div>
        <h3 className="duplicate-lead-section-title">Information</h3>
        <div className="duplicate-lead-summary">
          <span><b>ID</b>{duplicateLead.id}</span>
          <span><b>Name</b>{duplicateLead.first_name} {duplicateLead.last_name}</span>
          <span><b>DOB</b>{duplicateLead.dob || "N/A"}</span>
          <span><b>Phone Number</b>{duplicateLead.phone || "N/A"}</span>
          <span><b>State</b>{duplicateLead.state || "N/A"}</span>
          <span><b>Status</b>{duplicateBucket(duplicateLead)}</span>
        </div>
        <div className="duplicate-lead-actions">
          <Button variant="primary" onClick={() => navigate(existingLeadPath(duplicateLead))}>
            <ExternalLink size={20} /> Take me to {duplicateFolderLabel(duplicateLead)}
          </Button>
        </div>
      </div>
    </Modal>}
    <div className="form-panel">
      <h3>Lead Source</h3>
      <Field label="Source" required><Select value={form.source} onChange={(v) => patch("source", v)} options={leadSources} /></Field>
      {form.source === "Transfer" && <Field label="SOC Date" required><input type="date" value={form.soc_date || ""} onChange={(e) => patch("soc_date", e.target.value)} /></Field>}
      {form.source === "Event" && <><Field label="Select Event" required><Select value={form.event_name || ""} onChange={(v) => patch("event_name", v)} options={["", ...lookups.events.map((e) => e.event_name)]} /></Field>{user.role === "admin" && <div className="inline-add"><Field label="Add New Event"><input value={newEvent} onChange={(e) => setNewEvent(e.target.value)} placeholder="e.g. Health Fair 2026" /></Field><Button onClick={confirmAddEvent}>Add Event</Button></div>}</>}
      {form.source === "Word of Mouth" && <Field label="Word of Mouth Type" required><Select value={form.word_of_mouth_type || "Caregiver"} onChange={(v) => patch("word_of_mouth_type", v)} options={["Caregiver", "Community", "Client"]} /></Field>}
      {form.source === "Other" && <Field label="Specify Source Type" required><input value={form.other_source_type || ""} onChange={(e) => patch("other_source_type", e.target.value)} /></Field>}
      {form.source === "Direct Through CCU" && <div className="source-block">
        <div className="two-col">
          <Field label="Payor" required><select value={form.agency_id || ""} onChange={(e) => patch("agency_id", Number(e.target.value) || null)}><option value="">None</option>{lookups.agencies.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</select></Field>
          <Field label="CCU"><select value={form.ccu_id || ""} onChange={(e) => patch("ccu_id", Number(e.target.value) || null)}><option value="">None</option>{lookups.ccus.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
        </div>
        {form.agency_id && lookups.agencySuboptions.filter((s) => Number(s.agency_id) === Number(form.agency_id)).length > 0 && <Field label="Select Suboption"><select value={form.agency_suboption_id || ""} onChange={(e) => patch("agency_suboption_id", Number(e.target.value) || null)}><option value="">None</option>{lookups.agencySuboptions.filter((s) => Number(s.agency_id) === Number(form.agency_id)).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></Field>}
        {form.ccu_id && <details className="inline-details entity-edit-dropdown" open={ccuDetailsOpen}>
          <summary onClick={(e) => {
            e.preventDefault();
            setCcuDetailsOpen((current) => !current);
          }}>Edit CCU Details (Update)</summary>
          <div className="form-grid">
            <Field label="Name"><input value={ccuEditForm.name} onChange={(e) => setCcuEditForm({ ...ccuEditForm, name: e.target.value })} /></Field>
            <Field label="Email"><input value={ccuEditForm.email} onChange={(e) => setCcuEditForm({ ...ccuEditForm, email: e.target.value })} /></Field>
            <Field label="Street"><input value={ccuEditForm.street} onChange={(e) => setCcuEditForm({ ...ccuEditForm, street: e.target.value })} /></Field>
            <Field label="Coordinator"><input value={ccuEditForm.care_coordinator_name} onChange={(e) => setCcuEditForm({ ...ccuEditForm, care_coordinator_name: e.target.value })} /></Field>
            <Field label="City"><input value={ccuEditForm.city} onChange={(e) => setCcuEditForm({ ...ccuEditForm, city: e.target.value })} /></Field>
            <Field label="State"><input value={ccuEditForm.state} onChange={(e) => setCcuEditForm({ ...ccuEditForm, state: e.target.value })} maxLength={2} /></Field>
            <Field label="Zip Code"><input value={ccuEditForm.zip_code} onChange={(e) => setCcuEditForm({ ...ccuEditForm, zip_code: e.target.value })} /></Field>
            <Field label="Phone"><input value={ccuEditForm.phone} onChange={(e) => setCcuEditForm({ ...ccuEditForm, phone: e.target.value })} /></Field>
            <Field label="Fax"><input value={ccuEditForm.fax} onChange={(e) => setCcuEditForm({ ...ccuEditForm, fax: e.target.value })} /></Field>
          </div>
          <Button variant="primary" onClick={confirmUpdateSelectedCcu}>Update CCU Details</Button>
        </details>}
        {user.role === "admin" && <details className="inline-details"><summary>Add New Payor</summary><div className="form-grid">{["name","address","phone","fax","email"].map((key) => <Field key={key} label={key}><input value={newPayor[key]} onChange={(e) => setNewPayor({ ...newPayor, [key]: e.target.value })} /></Field>)}</div><Button onClick={confirmAddPayor}>Add Payor</Button></details>}
        <details className="inline-details"><summary>Add New CCU</summary><div className="form-grid">{["name","street","city","state","zip_code","phone","fax","email","care_coordinator_name"].map((key) => <Field key={key} label={key.replaceAll("_", " ")}><input value={newCcu[key]} onChange={(e) => setNewCcu({ ...newCcu, [key]: e.target.value })} /></Field>)}</div><Button onClick={confirmAddCcu}>Add CCU</Button></details>
      </div>}
      <h3>Lead Details</h3>
      <div className="form-grid">
        {user.role === "admin" ? <Field label="Staff Name" required><Select value={form.staff_name} onChange={(v) => patch("staff_name", v)} options={["", ...lookups.approvedUsers.map((u) => u.username)]} /></Field> : <div className="info">Lead will be created by: <b>{user.username}</b></div>}
        <Field label="User ID" required><input value={form.custom_user_id || ""} onChange={(e) => patch("custom_user_id", e.target.value)} disabled={!!form.owner_id} /></Field>
        <Field label="First Name" required><input value={form.first_name} onChange={(e) => patch("first_name", e.target.value)} /></Field>
        <Field label="Last Name" required><input value={form.last_name} onChange={(e) => patch("last_name", e.target.value)} /></Field>
        <Field label="Date of Birth"><input type="date" value={form.dob || ""} onChange={(e) => patch("dob", e.target.value)} /></Field>
        <Field label="Age / Year"><input type="number" value={form.age || ""} onChange={(e) => patch("age", Number(e.target.value) || null)} disabled={!!form.dob} /></Field>
        <Field label="Gender"><div className="segmented gender-buttons">{genderOptions.map((option) => <Button key={option} active={form.gender === option} onClick={() => patch("gender", form.gender === option ? "" : option)}>{option}</Button>)}</div></Field>
        <div />
        <Field label="Email"><input value={form.email || ""} onChange={(e) => patch("email", e.target.value)} /></Field>
        <Field label="Phone" required><input value={form.phone} onChange={(e) => patch("phone", e.target.value)} /></Field>
        <Field label="SSN"><input value={form.ssn || ""} onChange={(e) => patch("ssn", e.target.value)} /></Field>
        <Field label="Medicaid Number"><input value={form.medicaid_no || ""} onChange={(e) => patch("medicaid_no", e.target.value)} /></Field>
        <Field label="Contact Status" required><Select value={form.last_contact_status} onChange={(v) => patch("last_contact_status", v)} options={isReferralSource ? referralStatuses.filter((x) => x !== "All") : leadStatuses} /></Field>
        {isReferralSource && <Field label="Referral Type" required><Select value={form.referral_type || "Regular"} onChange={(v) => patch("referral_type", v)} options={["Regular", "Interim"]} /></Field>}
        <Field label="Street"><input value={form.street || ""} onChange={(e) => patch("street", e.target.value)} /></Field>
        <Field label="City"><input value={form.city || ""} onChange={(e) => patch("city", e.target.value)} /></Field>
        <Field label="State"><input maxLength={2} value={form.state || ""} onChange={(e) => patch("state", e.target.value)} /></Field>
        <Field label="Zip Code"><input value={form.zip_code || ""} onChange={(e) => patch("zip_code", e.target.value)} /></Field>
        <Field label="Emergency Contact Name"><input value={form.e_contact_name || ""} onChange={(e) => patch("e_contact_name", e.target.value)} /></Field>
        <Field label="Relation"><input value={form.e_contact_relation || ""} onChange={(e) => patch("e_contact_relation", e.target.value)} /></Field>
        <Field label="Emergency Contact Phone"><input value={form.e_contact_phone || ""} onChange={(e) => patch("e_contact_phone", e.target.value)} /></Field>
        <Field label="Comments"><textarea value={form.comments || ""} onChange={(e) => patch("comments", e.target.value)} /></Field>
        <label className="check"><input type="checkbox" checked={form.send_reminders !== false} onChange={(e) => patch("send_reminders", e.target.checked)} />Send Auto Email Reminders for this Lead</label>
      </div>
      <small>Fields marked with * are required</small>
      <Button variant="primary" onClick={validateBeforeConfirm}>Save Lead</Button>
    </div>
  </>;
}
