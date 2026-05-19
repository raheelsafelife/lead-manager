import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ChevronLeft, Plus, Save } from "lucide-react";
import { Button, Field, Modal, Select } from "../components/Controls";
import { useConfirm } from "../components/ConfirmProvider";
import { api } from "../services/api";
import { caregiverTypes, uniqueCcuSuggestions } from "../utils/constants";
import { useAuth } from "../context/AuthContext";
import { WorkflowSkeleton } from "../components/Skeleton";

const referralStatuses = ["Initial Referral Sent", "Assessment Scheduled", "Assessment Done", "Not Approved", "Services Refused", "Inactive"];

function todayValue() {
  return new Date().toISOString().slice(0, 10);
}

function value(v) {
  return v || "N/A";
}

export default function MarkReferralPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const confirmAction = useConfirm();
  const backTo = searchParams.get("from") || "/view-leads";
  const [lead, setLead] = useState(null);
  const [lookups, setLookups] = useState({ agencies: [], ccus: [] });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showAgencyForm, setShowAgencyForm] = useState(false);
  const [showCcuForm, setShowCcuForm] = useState(false);
  const [ccuDetailsOpen, setCcuDetailsOpen] = useState(false);
  const [updateNotice, setUpdateNotice] = useState("");
  const [agencyName, setAgencyName] = useState("");
  const [ccuForm, setCcuForm] = useState({ name: "", street: "", city: "", state: "IL", zip_code: "", phone: "", fax: "", email: "", care_coordinator_name: "" });
  const [ccuEditForm, setCcuEditForm] = useState({ name: "", street: "", city: "", state: "IL", zip_code: "", phone: "", fax: "", email: "", care_coordinator_name: "" });
  const [form, setForm] = useState({
    last_contact_status: "Initial Referral Sent",
    referral_sent_date: todayValue(),
    referral_type: "Regular",
    caregiver_type: "None",
    agency_id: "",
    ccu_id: "",
    send_reminders: true
  });
  const ccuSuggestions = uniqueCcuSuggestions(lookups.ccus, form.ccu_id);

  const canEdit = useMemo(() => lead && (user.role === "admin" || lead.staff_name === user.username), [lead, user]);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const [leadRes, lookupRes] = await Promise.all([
          api.get(`/leads/${id}`),
          api.get("/lookups")
        ]);
        if (!mounted) return;
        setLead(leadRes.data);
        setLookups(lookupRes.data);
        setForm((current) => ({
          ...current,
          referral_type: leadRes.data.referral_type || "Regular",
          caregiver_type: leadRes.data.caregiver_type || "None",
          agency_id: leadRes.data.agency_id ? String(leadRes.data.agency_id) : "",
          ccu_id: leadRes.data.ccu_id ? String(leadRes.data.ccu_id) : "",
          send_reminders: leadRes.data.send_reminders !== 0
        }));
        setCcuDetailsOpen(Boolean(leadRes.data.ccu_id));
      } catch (err) {
        if (!mounted) return;
        setError(err.response?.data?.error || "Could not load lead");
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, [id]);

  function patch(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  useEffect(() => {
    if (!form.ccu_id) return;
    const selected = lookups.ccus.find((entry) => String(entry.id) === String(form.ccu_id));
    if (!selected) return;
    setCcuDetailsOpen(true);
    setCcuEditForm({
      name: selected.name || "",
      street: selected.street || "",
      city: selected.city || "",
      state: selected.state || "IL",
      zip_code: selected.zip_code || "",
      phone: selected.phone || "",
      fax: selected.fax || "",
      email: selected.email || "",
      care_coordinator_name: selected.care_coordinator_name || ""
    });
  }, [form.ccu_id, lookups.ccus]);

  async function refreshLookups() {
    const res = await api.get("/lookups");
    setLookups(res.data);
    return res.data;
  }

  async function addAgency() {
    if (!agencyName.trim()) return;
    try {
      await api.post("/admin/agency", { name: agencyName.trim() });
      const nextLookups = await refreshLookups();
      const agency = (nextLookups.agencies || []).find((entry) => entry.name === agencyName.trim());
      if (agency) patch("agency_id", String(agency.id));
      setAgencyName("");
      setShowAgencyForm(false);
    } catch (err) {
      setError(err.response?.data?.error || "Could not add payor");
    }
  }

  function confirmAddAgency() {
    if (!agencyName.trim()) return;
    confirmAction({
      title: "Add Payor?",
      message: `Do you want to create payor ${agencyName.trim()}?`,
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: addAgency
    });
  }

  async function addCcu() {
    if (!ccuForm.name.trim()) return;
    try {
      await api.post("/ccus", ccuForm);
      const nextLookups = await refreshLookups();
      const ccu = (nextLookups.ccus || []).find((entry) => entry.name === ccuForm.name.trim());
      if (ccu) patch("ccu_id", String(ccu.id));
      setCcuForm({ name: "", street: "", city: "", state: "IL", zip_code: "", phone: "", fax: "", email: "", care_coordinator_name: "" });
      setShowCcuForm(false);
    } catch (err) {
      setError(err.response?.data?.error || "Could not add CCU");
    }
  }

  function confirmAddCcu() {
    if (!ccuForm.name.trim()) return;
    confirmAction({
      title: "Add CCU?",
      message: `Do you want to create CCU ${ccuForm.name.trim()}?`,
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: addCcu
    });
  }

  async function updateSelectedCcu() {
    if (!form.ccu_id) return;
    try {
      await api.patch(`/ccus/${form.ccu_id}`, ccuEditForm);
      await refreshLookups();
      setCcuDetailsOpen(false);
      setUpdateNotice("CCU details updated successfully.");
    } catch (err) {
      setError(err.response?.data?.error || "Could not update CCU");
    }
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

  async function confirmMarkReferral() {
    setSubmitting(true);
    setError("");
    try {
      await api.patch(`/leads/${id}`, {
        active_client: 1,
        authorization_received: 0,
        last_contact_status: form.last_contact_status,
        referral_sent_date: form.referral_sent_date,
        referral_type: form.referral_type,
        caregiver_type: form.caregiver_type === "None" ? null : form.caregiver_type,
        agency_id: form.agency_id ? Number(form.agency_id) : null,
        ccu_id: form.ccu_id ? Number(form.ccu_id) : null,
        send_reminders: form.send_reminders ? 1 : 0
      });
      navigate(backTo);
    } catch (err) {
      setError(err.response?.data?.error || "Could not mark referral");
    } finally {
      setSubmitting(false);
    }
  }

  function askMarkReferral() {
    confirmAction({
      title: "Mark Referral?",
      message: `Do you want to mark ${lead.first_name} ${lead.last_name} as a referral?`,
      confirmText: "Yes",
      cancelText: "No",
      onConfirm: confirmMarkReferral
    });
  }

  if (error && !lead) return <div className="error">{error}</div>;
  if (!lead) return <WorkflowSkeleton />;
  if (!canEdit) return <div className="error">You do not have permission to mark this lead as a referral.</div>;

  return (
    <div className="mark-referral-page">
      <div className="mark-referral-header">MARK REFERRAL</div>

      <Button onClick={() => navigate(backTo)}>
        <ChevronLeft size={16} />
        Back to View Leads
      </Button>

      <div className="mark-referral-divider" />

      <div className="mark-referral-summary">
        <div>
          <h3>{lead.first_name} {lead.last_name}</h3>
          <p><b>ID:</b> {lead.id}</p>
          <p><b>Staff:</b> {value(lead.staff_name)}</p>
          <p><b>Phone:</b> {value(lead.phone)}</p>
          <p><b>Source:</b> {value(lead.source)}</p>
        </div>
        <div>
          <p><b>Status:</b> {value(lead.last_contact_status)}</p>
          <p><b>City:</b> {value(lead.city)}</p>
          <p><b>Medicaid #:</b> {value(lead.medicaid_no)}</p>
        </div>
      </div>

      <div className="mark-referral-divider" />

      {lead.active_client && (
        <div className="warning-box">
          This lead is already marked as a referral ({lead.referral_type || "Regular"}).
        </div>
      )}

      {!lead.active_client && (
        <>
          <section className="mark-referral-section">
            <h3>Select Referral Type and Payor</h3>
            <p>If you switch on "Mark as Referral", it will be categorized as Referral Sent by default.</p>

            <div className="mark-referral-grid">
              <div>
                <Field label="Initial Status">
                  <Select value={form.last_contact_status} onChange={(value) => patch("last_contact_status", value)} options={referralStatuses} />
                </Field>
                <Field label="Referral Sent Date">
                  <input type="date" value={form.referral_sent_date} onChange={(e) => patch("referral_sent_date", e.target.value)} />
                </Field>
              </div>

              <div>
                <Field label="Referral Type">
                  <div className="mark-referral-radio-row">
                    {["Regular", "Interim"].map((option) => (
                      <label className="check" key={option}>
                        <input type="radio" name="referral_type" checked={form.referral_type === option} onChange={() => patch("referral_type", option)} />
                        {option}
                      </label>
                    ))}
                  </div>
                </Field>
                <Field label="Caregiver Type">
                  <Select value={form.caregiver_type} onChange={(value) => patch("caregiver_type", value)} options={caregiverTypes} />
                </Field>
              </div>
            </div>
          </section>

          <div className="mark-referral-divider" />

          <section className="mark-referral-section">
            <h4>Payor:</h4>
            {user.role === "admin" && (
              <div className="mark-referral-inline-add">
                <button className="mark-referral-inline-toggle" onClick={() => setShowAgencyForm((current) => !current)}>
                  <Plus size={15} />
                  Add New Payor
                </button>
                {showAgencyForm && (
                  <div className="mark-referral-inline-form">
                    <input value={agencyName} onChange={(e) => setAgencyName(e.target.value)} placeholder="New Payor Name" />
                    <Button variant="primary" onClick={confirmAddAgency}>Add Payor</Button>
                  </div>
                )}
              </div>
            )}
            <select value={form.agency_id || "none"} onChange={(e) => patch("agency_id", e.target.value === "none" ? "" : e.target.value)}>
              <option value="none">None</option>
              {lookups.agencies.map((entry) => <option key={entry.id} value={entry.id}>{entry.name}</option>)}
            </select>
            <div className="mark-referral-option-hints">
              <span>{form.agency_id ? lookups.agencies.find((entry) => String(entry.id) === form.agency_id)?.name || "Selected payor" : "None"}</span>
            </div>
          </section>

          <div className="mark-referral-divider" />

          <section className="mark-referral-section">
            <h4>CCU Details:</h4>
            <div className="mark-referral-inline-add">
              <button className="mark-referral-inline-toggle" onClick={() => setShowCcuForm((current) => !current)}>
                <Plus size={15} />
                Add New CCU
              </button>
              {showCcuForm && (
                <div className="mark-referral-ccu-grid">
                  <input value={ccuForm.name} onChange={(e) => setCcuForm({ ...ccuForm, name: e.target.value })} placeholder="CCU Name *" />
                  <input value={ccuForm.street} onChange={(e) => setCcuForm({ ...ccuForm, street: e.target.value })} placeholder="Street" />
                  <input value={ccuForm.city} onChange={(e) => setCcuForm({ ...ccuForm, city: e.target.value })} placeholder="City" />
                  <input value={ccuForm.state} onChange={(e) => setCcuForm({ ...ccuForm, state: e.target.value })} placeholder="State" maxLength={2} />
                  <input value={ccuForm.zip_code} onChange={(e) => setCcuForm({ ...ccuForm, zip_code: e.target.value })} placeholder="Zip Code" />
                  <input value={ccuForm.phone} onChange={(e) => setCcuForm({ ...ccuForm, phone: e.target.value })} placeholder="Phone" />
                  <input value={ccuForm.fax} onChange={(e) => setCcuForm({ ...ccuForm, fax: e.target.value })} placeholder="Fax" />
                  <input value={ccuForm.email} onChange={(e) => setCcuForm({ ...ccuForm, email: e.target.value })} placeholder="Email" />
                  <input value={ccuForm.care_coordinator_name} onChange={(e) => setCcuForm({ ...ccuForm, care_coordinator_name: e.target.value })} placeholder="Care Coordinator" />
                  <Button variant="primary" onClick={confirmAddCcu}>Add CCU</Button>
                </div>
              )}
            </div>
            <select value={form.ccu_id || "none"} onChange={(e) => {
              const nextValue = e.target.value === "none" ? "" : e.target.value;
              patch("ccu_id", nextValue);
              setCcuDetailsOpen(Boolean(nextValue));
            }}>
              <option value="none">None</option>
              {ccuSuggestions.map((entry) => <option key={entry.id} value={entry.id}>{entry.name}</option>)}
            </select>
            {form.ccu_id && (
              <>
                <div className="mark-referral-option-hints">
                  <span>{lookups.ccus.find((entry) => String(entry.id) === form.ccu_id)?.name || "Selected CCU"}</span>
                </div>
                <details className="mark-referral-details-block" open={ccuDetailsOpen}>
                  <summary onClick={(e) => {
                    e.preventDefault();
                    setCcuDetailsOpen((current) => !current);
                  }}>Edit CCU Details (Update)</summary>
                  <div className="mark-referral-ccu-grid mark-referral-ccu-grid-edit">
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
                </details>
              </>
            )}
          </section>

          <section className="mark-referral-section">
            <h4>Notifications & Tracking</h4>
            <label className="check">
              <input type="checkbox" checked={form.send_reminders} onChange={(e) => patch("send_reminders", e.target.checked)} />
              Send Auto Email Reminders for this Lead
            </label>
          </section>

          {error && <div className="error">{error}</div>}

          <div className="mark-referral-actions">
            <Button variant="primary" onClick={askMarkReferral} disabled={submitting}>
              <Save size={16} />
              {submitting ? "Saving..." : "Confirm"}
            </Button>
            <Button onClick={() => navigate(backTo)}>Cancel</Button>
          </div>
        </>
      )}
      {updateNotice && <Modal title="Updated" onClose={() => setUpdateNotice("")}>
        <div className="info">{updateNotice}</div>
      </Modal>}
    </div>
  );
}
