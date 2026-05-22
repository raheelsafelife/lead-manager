import { Building2, CalendarDays, Copy, Download, Eye, History, Mail, MessageSquare, Paperclip, Phone, Trash2, Upload, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, downloadFile, previewUrl } from "../services/api";
import { Button, Field, Modal, Select, StatusPill } from "./Controls";
import { useConfirm } from "./ConfirmProvider";
import { callStatuses, caregiverTypes, leadSources } from "../utils/constants";
import { useAuth } from "../context/AuthContext";
import { emitToast } from "../utils/appEvents";

const fmt = (v) => v ? new Date(v).toLocaleString() : "N/A";
const dateOnly = (v) => v ? new Date(v).toLocaleDateString() : "N/A";
const value = (v) => v || "N/A";
const shortDateTime = (v) => v ? new Date(v).toLocaleString([], { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "";
const joinAddress = (...parts) => parts.filter(Boolean).join(", ") || "N/A";
const referralEditStatuses = ["Initial Referral Sent", "Assessment Scheduled", "Assessment Done", "Not Approved", "Services Refused"];
const standardLeadStatuses = ["Initial Call", "Not Interested", "No Response", "Initial Referral Sent"];
const leadStatusControls = ["Initial Call", "No Response", "Not Interested"];
const referralStatusControls = ["Initial Referral Sent", "Assessment Scheduled", "Assessment Done", "Not Approved", "Services Refused"];
const genderOptions = ["Male", "Female", "Other"];

function DetailLine({ label, children }) {
  return <p><b>{label}:</b><span>{children}</span></p>;
}

function isCopyable(value) {
  return Boolean(value && value !== "N/A");
}

export default function LeadCard({ lead, type, onChanged }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const confirmAction = useConfirm();
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [history, setHistory] = useState([]);
  const [comment, setComment] = useState("");
  const [edit, setEdit] = useState(false);
  const [form, setForm] = useState(lead);
  const [lookups, setLookups] = useState({ agencies: [], ccus: [], approvedUsers: [] });
  const [manageEntities, setManageEntities] = useState(false);
  const [selectedAgencyId, setSelectedAgencyId] = useState("");
  const [selectedCcuId, setSelectedCcuId] = useState("");
  const [agencyForm, setAgencyForm] = useState({ name: "", address: "", phone: "", fax: "", email: "" });
  const [ccuForm, setCcuForm] = useState({ name: "", street: "", city: "", state: "IL", zip_code: "", phone: "", fax: "", email: "", care_coordinator_name: "" });
  const [ccuDetailsOpen, setCcuDetailsOpen] = useState(false);
  const [updateNotice, setUpdateNotice] = useState("");
  const [copiedKey, setCopiedKey] = useState("");
  const commentInputRef = useRef(null);
  const canModify = user.role === "admin" || lead.staff_name === user.username;

  useEffect(() => { if (open) api.get(`/leads/${lead.id}`).then((res) => setDetail(res.data)); }, [open, lead.id]);
  useEffect(() => {
    if (!selectedAgencyId) return;
    const agency = lookups.agencies.find((entry) => String(entry.id) === String(selectedAgencyId));
    if (!agency) return;
    setAgencyForm({
      name: agency.name || "",
      address: agency.address || "",
      phone: agency.phone || "",
      fax: agency.fax || "",
      email: agency.email || ""
    });
  }, [selectedAgencyId, lookups.agencies]);
  useEffect(() => {
    if (!selectedCcuId) return;
    const ccu = lookups.ccus.find((entry) => String(entry.id) === String(selectedCcuId));
    if (!ccu) return;
    setCcuDetailsOpen(true);
    setCcuForm({
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
  }, [selectedCcuId, lookups.ccus]);

  async function updateLead(data) {
    await api.patch(`/leads/${lead.id}`, data);
    onChanged();
  }

  function askUpdateLead({ title = "Update Lead?", message = "Do you want to update this lead?", data, after }) {
    confirmAction({
      title,
      message,
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: async () => {
        await updateLead(data);
        if (after) after();
      }
    });
  }

  async function addComment() {
    if (!comment.trim()) return;
    await api.post(`/leads/${lead.id}/comment`, { content: comment });
    setComment("");
    const res = await api.get(`/leads/${lead.id}`);
    setDetail(res.data);
  }

  function askAddComment() {
    if (!comment.trim()) return;
    confirmAction({
      title: "Add Comment?",
      message: "Do you want to add this comment?",
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: addComment
    });
  }

  async function uploadFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    const input = e.target;
    confirmAction({
      title: "Upload Attachment?",
      message: `Do you want to upload ${file.name}?`,
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: async () => {
        await api.post(`/leads/${lead.id}/attachment`, body);
        input.value = "";
        const res = await api.get(`/leads/${lead.id}`);
        setDetail(res.data);
      }
    });
  }

  async function showHistory() {
    const res = await api.get(`/leads/${lead.id}/history`);
    setHistory(history.length ? [] : res.data.rows);
  }

  async function downloadAttachment(attachment) {
    await downloadFile(`/attachments/${attachment.id}/download`, {}, attachment.filename);
  }

  async function previewAttachment(attachment) {
    window.open(previewUrl(`/attachments/${attachment.id}/preview`), "_blank", "noopener,noreferrer");
  }

  async function saveEdit() {
    await updateLead({
      ...form,
      caregiver_type: form.caregiver_type === "None" ? null : form.caregiver_type,
      agency_id: selectedAgencyId ? Number(selectedAgencyId) : null,
      ccu_id: selectedCcuId ? Number(selectedCcuId) : null,
      send_reminders: form.send_reminders ? 1 : 0
    });
    setEdit(false);
  }

  function askSaveEdit() {
    confirmAction({
      title: "Save Lead Changes?",
      message: `Do you want to update lead ${fullName}?`,
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: saveEdit
    });
  }

  async function openEdit() {
    setForm({
      ...lead,
      caregiver_type: lead.caregiver_type || "None",
      referral_type: lead.referral_type || "Regular",
      source: lead.source || leadSources[0],
      send_reminders: lead.send_reminders !== 0
    });
    setSelectedAgencyId(lead.agency_id ? String(lead.agency_id) : "");
    setSelectedCcuId(lead.ccu_id ? String(lead.ccu_id) : "");
    setManageEntities(false);
    setCcuDetailsOpen(Boolean(lead.ccu_id));
    setUpdateNotice("");
    const res = await api.get("/lookups");
    setLookups(res.data);
    setEdit(true);
  }

  function changeStaffName(username) {
    const selected = lookups.approvedUsers.find((entry) => entry.username === username);
    setForm({
      ...form,
      staff_name: username,
      custom_user_id: selected?.user_id || form.custom_user_id || "",
      owner_id: selected?.id || form.owner_id || null
    });
  }

  async function saveAgencyDetails() {
    if (!selectedAgencyId) return;
    await api.patch(`/agencies/${selectedAgencyId}`, agencyForm);
    const res = await api.get("/lookups");
    setLookups(res.data);
  }

  function askSaveAgencyDetails() {
    if (!selectedAgencyId) return;
    confirmAction({
      title: "Update Payor?",
      message: "Do you want to update this payor's details?",
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: saveAgencyDetails
    });
  }

  async function saveCcuDetails() {
    if (!selectedCcuId) return;
    await api.patch(`/ccus/${selectedCcuId}`, ccuForm);
    const res = await api.get("/lookups");
    setLookups(res.data);
    setCcuDetailsOpen(false);
    setUpdateNotice("CCU details updated successfully.");
  }

  function askSaveCcuDetails() {
    if (!selectedCcuId) return;
    confirmAction({
      title: "Update CCU?",
      message: "Do you want to update this CCU's details?",
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: saveCcuDetails
    });
  }

  function askSoftDelete() {
    confirmAction({
      title: "Delete Lead?",
      message: `Do you want to delete lead ${fullName}?`,
      detail: "This moves the lead to deleted leads.",
      confirmText: "Yes",
      cancelText: "No",
      variant: "danger",
      onConfirm: async () => {
        await api.post(`/leads/${lead.id}/soft-delete`);
        onChanged();
      }
    });
  }

  function askRestore() {
    confirmAction({
      title: "Restore Lead?",
      message: `Do you want to restore lead ${fullName}?`,
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: async () => {
        await api.post(`/leads/${lead.id}/restore`);
        onChanged();
      }
    });
  }

  async function copyContact(label, text, key) {
    if (!isCopyable(text)) return;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(String(text));
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = String(text);
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }
      setCopiedKey(key);
      window.setTimeout(() => setCopiedKey((current) => current === key ? "" : current), 1600);
      emitToast({ type: "success", message: `${label} copied` });
    } catch {
      emitToast({ type: "error", message: `Unable to copy ${label.toLowerCase()}` });
    }
  }

  function CopyValue({ label, text, copyKey }) {
    const canCopy = isCopyable(text);
    return (
      <span className="copy-value">
        <span>{value(text)}</span>
        {canCopy && (
          <button type="button" className="copy-value-btn" onClick={() => copyContact(label, text, copyKey)} aria-label={`Copy ${label}`}>
            <Copy size={14} />
          </button>
        )}
      </span>
    );
  }

  function ProfileContact({ icon: Icon, label, text, copyKey }) {
    return (
      <span className="profile-copy-line">
        <Icon size={16} />
        <CopyValue label={label} text={text} copyKey={copyKey} />
      </span>
    );
  }

  function askPermanentDelete() {
    confirmAction({
      title: "Permanently Delete Lead?",
      message: `Do you want to permanently delete lead ${fullName}?`,
      detail: "This cannot be undone.",
      confirmText: "Yes",
      cancelText: "No",
      variant: "danger",
      onConfirm: async () => {
        await api.delete(`/leads/${lead.id}`);
        onChanged();
      }
    });
  }

  function askDeleteAttachment(attachment) {
    confirmAction({
      title: "Delete Attachment?",
      message: `Do you want to delete ${attachment.filename}?`,
      confirmText: "Yes",
      cancelText: "No",
      variant: "danger",
      onConfirm: async () => {
        await api.delete(`/attachments/${attachment.id}`);
        setDetail((d) => ({ ...d, attachments: d.attachments.filter((x) => x.id !== attachment.id) }));
      }
    });
  }

  const fullName = `${lead.first_name} ${lead.last_name}`;
  const priority = lead.priority || "Not Called";
  const priorityClass = priority.toLowerCase().replaceAll(" ", "-");
  const mainStatus = lead.care_status || lead.last_contact_status || (lead.authorization_received ? "Authorization" : lead.active_client ? "Referral" : "Lead");
  const initials = fullName.split(" ").filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "LM";
  const commentRows = detail?.comments || [];
  const visibleComments = commentRows.slice(0, 2);
  const olderComments = commentRows.slice(2);
  const attachmentRows = detail?.attachments || [];
  const summaryPairsLeft = [
    ["Employee ID", value(lead.custom_user_id)],
    ["Authorization", lead.authorization_received ? "Received" : "Pending"],
    ["Care Status", value(lead.care_status)],
    ["SOC Date", dateOnly(lead.soc_date)],
    ["Gender", value(lead.gender)],
    ["Address", joinAddress(lead.street, lead.city, lead.state, lead.zip_code)],
    ["Emergency Contact", lead.e_contact_name || "N/A"]
  ];
  const summaryPairsRight = [
    ["Referral No.", value(lead.referral_id)],
    ["EC Phone", <CopyValue label="Emergency phone" text={lead.e_contact_phone} copyKey={`lead-${lead.id}-ec-phone`} />],
    ["Relationship", value(lead.e_contact_relation)],
    ["Phone", <CopyValue label="Phone" text={lead.phone} copyKey={`lead-${lead.id}-phone-info`} />],
    ["Email", <CopyValue label="Email" text={lead.email} copyKey={`lead-${lead.id}-email-info`} />],
    ["Medicaid #", value(lead.medicaid_no)],
    ["SSN", value(lead.ssn)]
  ];
  return (
    <div className={`lead-row lead-card-shell ${open ? "expanded" : ""}`}>
      <button className="lead-summary" onClick={() => setOpen(!open)}>
        <span className="lead-caret">{open ? "⌄" : "›"}</span>
        {lead.tag_color && <span className={`tag-dot ${lead.tag_color || ""}`}></span>}
        <span className="lead-title-block">
          <strong>ID: {lead.id} | {fullName}</strong>
          <small>{lead.staff_name}</small>
        </span>
        {lead.caregiver_type && lead.caregiver_type !== "None" && <em>{lead.caregiver_type}</em>}
      </button>
      <div className="inline-status">
        <Select value={lead.priority || "Not Called"} options={callStatuses} onChange={(value) => askUpdateLead({ title: "Update Call Status?", message: `Do you want to set call status to ${value}?`, data: { priority: value, call_status_updated_by: user.username, call_status_updated_at: new Date().toISOString() } })} />
        <div className={`header-status-card ${priorityClass}`}>
          <div><StatusPill value={priority} /></div>
          <small>{lead.call_status_updated_by || lead.updated_by || lead.staff_name || "N/A"}{shortDateTime(lead.call_status_updated_at || lead.updated_at) ? ` • ${shortDateTime(lead.call_status_updated_at || lead.updated_at)}` : ""}</small>
        </div>
      </div>
      {open && <div className="lead-detail professional-lead-card">
        <div className="lead-profile-shell">
          <div className="lead-profile-main">
            <div className="lead-profile-avatar">{initials}</div>
            <div className="lead-profile-copy">
              <div className="lead-profile-title-row">
                <h3>{fullName}</h3>
                <span className="lead-profile-id">ID: {lead.id}</span>
                <span className="lead-profile-status">{mainStatus}</span>
                {Number(lead.is_chicago_referral) === 1 && <span className="lead-profile-status chicago">Chicago Referral</span>}
              </div>
              <div className="lead-profile-contact-list">
                <span><UserRound size={16} />{value(lead.staff_name)}</span>
                <ProfileContact icon={Phone} label="Phone" text={lead.phone} copyKey={`lead-${lead.id}-phone`} />
                <ProfileContact icon={Mail} label="Email" text={lead.email} copyKey={`lead-${lead.id}-email`} />
                <span><CalendarDays size={16} />DOB: {dateOnly(lead.dob)} ({value(lead.age)}{lead.age ? " Years" : ""})</span>
              </div>
            </div>
          </div>
          <div className="lead-profile-facts">
            <div><b><Building2 size={16} />Source</b><span>{value(lead.source)}</span></div>
            <div><b><UserRound size={16} />Staff</b><span>{value(lead.staff_name)}</span></div>
            <div><b><CalendarDays size={16} />Assigned Date</b><span>{dateOnly(lead.created_at)}</span></div>
            <div><b><UserRound size={16} />Owner</b><span>{value(lead.updated_by || lead.staff_name)}</span></div>
          </div>
        </div>

        <div className="lead-context-strip">
          <article>
            <b><Building2 size={17} /> Payor</b>
            <strong>{value(lead.agency_name)}</strong>
            <div className="lead-context-detail">
              <span><b>Phone</b><CopyValue label="Payor phone" text={lead.agency_phone} copyKey={`lead-${lead.id}-agency-phone`} /></span>
              <span><b>Fax</b>{value(lead.agency_fax)}</span>
              <span><b>Email</b><CopyValue label="Payor email" text={lead.agency_email} copyKey={`lead-${lead.id}-agency-email`} /></span>
              <span><b>Address</b>{value(lead.agency_address)}</span>
            </div>
          </article>
          <article>
            <b><Building2 size={17} /> CCU</b>
            <strong>{value(lead.ccu_name)}</strong>
            <div className="lead-context-detail">
              <span><b>Coordinator</b>{value(lead.ccu_care_coordinator_name)}</span>
              <span><b>Phone</b><CopyValue label="CCU phone" text={lead.ccu_phone} copyKey={`lead-${lead.id}-ccu-phone`} /></span>
              <span><b>Fax</b>{value(lead.ccu_fax)}</span>
              <span><b>Email</b><CopyValue label="CCU email" text={lead.ccu_email} copyKey={`lead-${lead.id}-ccu-email`} /></span>
              <span><b>Address</b>{joinAddress(lead.ccu_street, lead.ccu_city, lead.ccu_state, lead.ccu_zip_code)}</span>
            </div>
          </article>
        </div>

        <div className="lead-card-topline">
          <div className="tag-picker card-tag-picker">
            <span>Assign Color Tag:</span>
            {["", "Blue", "Purple"].map((color) => <Button key={color || "none"} active={(lead.tag_color || "") === color} onClick={() => askUpdateLead({ title: "Update Color Tag?", message: `Do you want to set this lead's color tag to ${color || "None"}?`, data: { tag_color: color || null } })}>{color || "None"}</Button>)}
          </div>
        </div>
        <div className="lead-panels-grid">
          <section className="lead-panel lead-information-panel">
            <h3>Lead Information</h3>
            <div className="lead-information-columns">
              <div className="lead-information-list">
                {summaryPairsLeft.map(([label, item]) => <DetailLine key={label} label={label}>{item}</DetailLine>)}
              </div>
              <div className="lead-information-list">
                {summaryPairsRight.map(([label, item]) => <DetailLine key={label} label={label}>{item}</DetailLine>)}
              </div>
            </div>
          </section>

          <section className="lead-panel lead-comments-panel">
            <h3><MessageSquare size={18} /> Comments</h3>
            {commentRows.length ? (
              <div className="lead-comments-preview">
                {visibleComments.map((entry) => (
                  <div className="comment-card" key={entry.id}>
                    <b>{entry.username}</b>
                    <time>{fmt(entry.created_at)}</time>
                    <p>{entry.content}</p>
                  </div>
                ))}
                {olderComments.length > 0 && (
                  <details className="comments-dropdown">
                    <summary>Show {olderComments.length} older comment{olderComments.length === 1 ? "" : "s"}</summary>
                    <div className="comments-dropdown-list">
                      {olderComments.map((entry) => (
                        <div className="comment-card" key={entry.id}>
                          <b>{entry.username}</b>
                          <time>{fmt(entry.created_at)}</time>
                          <p>{entry.content}</p>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            ) : (
              <div className="lead-comments-empty">
                <p>No comments yet</p>
                <strong>Be the first to add a comment</strong>
                <Button variant="primary" onClick={() => commentInputRef.current?.focus()}>Add Comment</Button>
              </div>
            )}
          </section>
        </div>

        {lead.deleted_at && <div className="warning-box">Deleted by {lead.deleted_by || "Unknown"} on {fmt(lead.deleted_at)}</div>}
        <div className="lead-card-meta">
          <span>Created by: <b>{lead.created_by || lead.staff_name || "N/A"}</b> on {fmt(lead.created_at)}</span>
          <span>Last updated by: <b>{lead.updated_by || "N/A"}</b> on {fmt(lead.updated_at)}</span>
        </div>
        <div className="action-row">
          {!lead.deleted_at && canModify && <Button onClick={openEdit}>Edit Lead</Button>}
          {!lead.deleted_at && canModify && (
            <Button onClick={() => askUpdateLead({
              title: Number(lead.is_chicago_referral) === 1 ? "Remove Chicago Referral?" : "Mark Chicago Referral?",
              message: Number(lead.is_chicago_referral) === 1
                ? `Do you want to remove ${fullName} from the Chicago Referral folder?`
                : `Do you want to move ${fullName} to the Chicago Referral folder?`,
              data: { is_chicago_referral: Number(lead.is_chicago_referral) === 1 ? 0 : 1 }
            })}>
              {Number(lead.is_chicago_referral) === 1 ? "Remove Chicago Referral" : "Mark Chicago Referral"}
            </Button>
          )}
          {!lead.deleted_at && canModify && !lead.active_client && <Button onClick={() => navigate(`/mark-referral/${lead.id}?from=${encodeURIComponent(location.pathname)}`)}>Mark Referral Sent</Button>}
          {!lead.deleted_at && type === "referral" && <Button onClick={() => askUpdateLead({ title: "Mark Authorization?", message: `Do you want to mark authorization for ${fullName}?`, data: { authorization_received: 1, active_client: 1, last_contact_status: "Care Start", care_status: "Care Start" } })}>Mark Authorization</Button>}
          {!lead.deleted_at && type === "authorization" && <Button onClick={() => askUpdateLead({ title: "Unmark Authorization?", message: `Do you want to unmark authorization for ${fullName}?`, data: { authorization_received: 0, care_status: null } })}>Unmark Authorization</Button>}
          {!lead.deleted_at && canModify && <Button onClick={askSoftDelete}><Trash2 size={15} />Delete Lead</Button>}
          {lead.deleted_at && <Button variant="primary" onClick={askRestore}>Restore</Button>}
          {lead.deleted_at && user.role === "admin" && <Button onClick={askPermanentDelete}>Permanent Delete</Button>}
          <Button onClick={showHistory}><History size={15} />History</Button>
        </div>
        {type !== "authorization" && !lead.deleted_at && canModify && (
          <div className="status-controls">
            <b>{type === "referral" ? "Referral Status:" : "Lead Status:"}</b>
            {(type === "referral" ? referralStatusControls : leadStatusControls).map((status) => (
              <Button
                key={status}
                active={lead.last_contact_status === status}
                onClick={() => askUpdateLead({
                  title: "Update Status?",
                  message: `Do you want to set ${fullName}'s status to ${status}?`,
                  data: { last_contact_status: status }
                })}
              >
                {status}
              </Button>
            ))}
          </div>
        )}
        {type === "authorization" && !lead.deleted_at && canModify && <div className="status-controls">
          <b>Manage Status:</b>
          {["Active", "Hold", "Terminated", "Deceased", "Transfer"].map((s) => <Button key={s} active={(s === "Active" && !["Hold", "Terminated", "Deceased", "Transfer Received"].includes(lead.care_status)) || lead.care_status === s || (s === "Transfer" && String(lead.care_status || "").includes("Transfer"))} onClick={() => askUpdateLead({ title: "Update Authorization Status?", message: `Do you want to set authorization status to ${s}?`, data: { care_status: s === "Active" ? null : s === "Transfer" ? "Transfer Received" : s, soc_date: s === "Active" ? lead.soc_date : null } })}>{s}</Button>)}
          <Button active={lead.care_status === "Care Start"} onClick={() => askUpdateLead({ title: "Mark Care Start?", message: `Do you want to mark Care Start for ${fullName}?`, data: { care_status: "Care Start" } })}>Care Start</Button>
          <Button active={lead.care_status === "Not Start"} onClick={() => askUpdateLead({ title: "Mark Care Not Start?", message: `Do you want to mark Care Not Start for ${fullName}?`, data: { care_status: "Not Start", soc_date: null } })}>Care Not Start</Button>
        </div>}

        <div className="lead-bottom-grid">
          <section className="lead-panel comments lead-composer-panel">
            <h3>Add a Comment</h3>
            <div className="comment-entry">
              <textarea ref={commentInputRef} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Type your comment here..." />
              <Button variant="primary" onClick={askAddComment}><MessageSquare size={15} />Comment</Button>
            </div>
          </section>

          <section className="lead-panel attachments lead-attachments-panel">
            <h3><Paperclip size={16} /> Attachments</h3>
            <div className="lead-attachments-toolbar">
              <label className="upload lead-upload-card">Upload Attachment<input type="file" onChange={uploadFile} /></label>
              <small>Allowed: PDF, DOC, DOCX, JPG, PNG</small>
            </div>
            {attachmentRows.length ? (
              attachmentRows.map((a) => (
                <div className="attachment" key={a.id}>
                  <span>{a.filename} · {a.uploaded_by} · {fmt(a.uploaded_at)}</span>
                  <div className="attachment-actions">
                    <button type="button" aria-label={`Preview ${a.filename}`} onClick={() => previewAttachment(a)}>
                      <Eye size={16} />
                    </button>
                    <button type="button" aria-label={`Download ${a.filename}`} onClick={() => downloadAttachment(a)}>
                      <Download size={16} />
                    </button>
                    {user.role === "admin" && (
                      <button
                        type="button"
                        aria-label={`Delete ${a.filename}`}
                        onClick={() => askDeleteAttachment(a)}
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="lead-attachments-empty">
                <p>No attachments yet</p>
                <strong>Add the first file for this lead</strong>
              </div>
            )}
          </section>
        </div>

        {history.length > 0 && <div className="history"><h3>Updates / Comments History</h3>{history.map((h) => <div className="history-card" key={h.id}><b>{h.username}</b><time>{fmt(h.timestamp)}</time><p>{h.action_type}: {h.description}</p></div>)}</div>}
      </div>}
      {edit && <Modal title="" onClose={() => setEdit(false)}>
        <div className="edit-lead-dialog">
          <div className="edit-lead-banner">Edit Lead: {fullName}</div>
          <div className="edit-grid edit-grid-rich">
            <Field label="First Name"><input value={form.first_name || ""} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></Field>
            <Field label="Status"><Select value={form.last_contact_status || (lead.active_client ? "Initial Referral Sent" : "Initial Call")} onChange={(value) => setForm({ ...form, last_contact_status: value })} options={lead.active_client ? referralEditStatuses : standardLeadStatuses} /></Field>
            <Field label="Last Name"><input value={form.last_name || ""} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></Field>
            <Field label="Referral Sent Date"><input type="date" value={form.referral_sent_date || ""} onChange={(e) => setForm({ ...form, referral_sent_date: e.target.value })} /></Field>
            <Field label="Employee ID"><input value={form.custom_user_id || ""} onChange={(e) => setForm({ ...form, custom_user_id: e.target.value })} /></Field>
            <Field label="Date of Birth"><input type="date" value={form.dob ? String(form.dob).slice(0, 10) : ""} onChange={(e) => setForm({ ...form, dob: e.target.value })} /></Field>
            <Field label="Phone"><input value={form.phone || ""} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
            <Field label="Age / Year"><input type="number" value={form.age || ""} onChange={(e) => setForm({ ...form, age: e.target.value })} /></Field>
            <Field label="Gender"><div className="segmented gender-buttons">{genderOptions.map((option) => <Button key={option} active={form.gender === option} onClick={() => setForm({ ...form, gender: form.gender === option ? "" : option })}>{option}</Button>)}</div></Field>
            <div />
            <Field label="Email"><input value={form.email || ""} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
            <Field label="SSN"><input value={form.ssn || ""} onChange={(e) => setForm({ ...form, ssn: e.target.value })} /></Field>
            <Field label="Staff Name">
              <Select
                value={form.staff_name || ""}
                onChange={changeStaffName}
                options={["", ...lookups.approvedUsers.map((entry) => entry.username)]}
              />
            </Field>
            <Field label="Medicaid #"><input value={form.medicaid_no || ""} onChange={(e) => setForm({ ...form, medicaid_no: e.target.value })} /></Field>
            <Field label="Source"><Select value={form.source || leadSources[0]} onChange={(value) => setForm({ ...form, source: value })} options={leadSources} /></Field>
            <Field label="Emergency Contact"><input value={form.e_contact_name || ""} onChange={(e) => setForm({ ...form, e_contact_name: e.target.value })} /></Field>
            <Field label="Street"><input value={form.street || ""} onChange={(e) => setForm({ ...form, street: e.target.value })} /></Field>
            <Field label="Relation"><input value={form.e_contact_relation || ""} onChange={(e) => setForm({ ...form, e_contact_relation: e.target.value })} /></Field>
            <Field label="City"><input value={form.city || ""} onChange={(e) => setForm({ ...form, city: e.target.value })} /></Field>
            <Field label="Emergency Phone"><input value={form.e_contact_phone || ""} onChange={(e) => setForm({ ...form, e_contact_phone: e.target.value })} /></Field>
            <Field label="State"><input value={form.state || "IL"} onChange={(e) => setForm({ ...form, state: e.target.value })} maxLength={2} /></Field>
            <div />
            <Field label="Zip Code"><input value={form.zip_code || ""} onChange={(e) => setForm({ ...form, zip_code: e.target.value })} /></Field>
            <div />
            <Field label="Caregiver Type"><Select value={form.caregiver_type || "None"} onChange={(value) => setForm({ ...form, caregiver_type: value })} options={caregiverTypes} /></Field>
            <div />
          </div>

          <Field label="Comments"><textarea value={form.comments || ""} onChange={(e) => setForm({ ...form, comments: e.target.value })} /></Field>

          <div className="edit-entity-toggle">
            <label className="check"><input type="checkbox" checked={manageEntities} onChange={(e) => setManageEntities(e.target.checked)} />Edit CCU/Payor</label>
          </div>

          {manageEntities && (
            <div className="edit-entity-grid">
              <div className="edit-entity-panel">
                <Field label="Payor">
                  <select value={selectedAgencyId || "none"} onChange={(e) => setSelectedAgencyId(e.target.value === "none" ? "" : e.target.value)}>
                    <option value="none">None</option>
                    {lookups.agencies.map((entry) => <option key={entry.id} value={entry.id}>{entry.name}</option>)}
                  </select>
                </Field>
                {selectedAgencyId && (
                  <details className="entity-edit-dropdown">
                    <summary>Edit {lookups.agencies.find((entry) => String(entry.id) === String(selectedAgencyId))?.name || "Payor"} (Globally)</summary>
                    <div className="edit-grid entity-edit-form">
                      <Field label="Payor Address"><input value={agencyForm.address} onChange={(e) => setAgencyForm({ ...agencyForm, address: e.target.value })} /></Field>
                      <Field label="Payor Phone"><input value={agencyForm.phone} onChange={(e) => setAgencyForm({ ...agencyForm, phone: e.target.value })} /></Field>
                      <Field label="Payor Fax"><input value={agencyForm.fax} onChange={(e) => setAgencyForm({ ...agencyForm, fax: e.target.value })} /></Field>
                      <Field label="Payor Email"><input value={agencyForm.email} onChange={(e) => setAgencyForm({ ...agencyForm, email: e.target.value })} /></Field>
                    </div>
                    <Button variant="primary" onClick={askSaveAgencyDetails}>Update Payor Details</Button>
                  </details>
                )}
              </div>

              <div className="edit-entity-panel">
                <Field label="CCU">
                  <select value={selectedCcuId || "none"} onChange={(e) => {
                    const nextValue = e.target.value === "none" ? "" : e.target.value;
                    setSelectedCcuId(nextValue);
                    setCcuDetailsOpen(Boolean(nextValue));
                  }}>
                    <option value="none">None</option>
                    {lookups.ccus.map((entry) => <option key={entry.id} value={entry.id}>{entry.name}</option>)}
                  </select>
                </Field>
                {selectedCcuId && (
                  <details className="entity-edit-dropdown" open={ccuDetailsOpen}>
                    <summary onClick={(e) => {
                      e.preventDefault();
                      setCcuDetailsOpen((current) => !current);
                    }}>Edit CCU Details (Update)</summary>
                    <div className="edit-grid entity-edit-form">
                      <Field label="Name"><input value={ccuForm.name} onChange={(e) => setCcuForm({ ...ccuForm, name: e.target.value })} /></Field>
                      <Field label="Email"><input value={ccuForm.email} onChange={(e) => setCcuForm({ ...ccuForm, email: e.target.value })} /></Field>
                      <Field label="Street"><input value={ccuForm.street} onChange={(e) => setCcuForm({ ...ccuForm, street: e.target.value })} /></Field>
                      <Field label="Coordinator"><input value={ccuForm.care_coordinator_name} onChange={(e) => setCcuForm({ ...ccuForm, care_coordinator_name: e.target.value })} /></Field>
                      <Field label="City"><input value={ccuForm.city} onChange={(e) => setCcuForm({ ...ccuForm, city: e.target.value })} /></Field>
                      <Field label="State"><input value={ccuForm.state} onChange={(e) => setCcuForm({ ...ccuForm, state: e.target.value })} maxLength={2} /></Field>
                      <Field label="Zip Code"><input value={ccuForm.zip_code} onChange={(e) => setCcuForm({ ...ccuForm, zip_code: e.target.value })} /></Field>
                      <Field label="Phone"><input value={ccuForm.phone} onChange={(e) => setCcuForm({ ...ccuForm, phone: e.target.value })} /></Field>
                      <Field label="Fax"><input value={ccuForm.fax} onChange={(e) => setCcuForm({ ...ccuForm, fax: e.target.value })} /></Field>
                    </div>
                    <Button variant="primary" onClick={askSaveCcuDetails}>Update CCU Details</Button>
                  </details>
                )}
              </div>
            </div>
          )}

          <div className="edit-tracking-block">
            <h4>Notifications & Tracking</h4>
            <label className="check"><input type="checkbox" checked={Boolean(form.send_reminders)} onChange={(e) => setForm({ ...form, send_reminders: e.target.checked })} />Send Auto Email Reminders for this Lead</label>
          </div>

          {lead.active_client && (
            <Button className="edit-unmark-button" onClick={() => askUpdateLead({ title: "Unmark Referral?", message: `Do you want to unmark ${fullName} as a referral?`, data: { active_client: 0, referral_type: null, referral_sent_date: null, agency_id: null, ccu_id: null, caregiver_type: null, send_reminders: 0, last_contact_status: "Initial Call" }, after: () => setEdit(false) })}>
              UNMARK AS REFERRAL
            </Button>
          )}

          <div className="edit-lead-actions">
            <Button onClick={() => setEdit(false)}>Cancel</Button>
            <Button variant="primary" onClick={askSaveEdit}>Save Changes</Button>
          </div>
        </div>
      </Modal>}
      {updateNotice && <Modal title="Updated" onClose={() => setUpdateNotice("")}>
        <div className="info">{updateNotice}</div>
      </Modal>}
    </div>
  );
}
