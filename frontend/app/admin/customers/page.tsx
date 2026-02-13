"use client";

import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";
import Modal from "../../_components/Modal";

type Customer = any;
type Contact = any;
type ContactMethod = any;

export default function AdminCustomersPage() {
  const [err, setErr] = useState("");
  const [items, setItems] = useState<Customer[]>([]);
  const [usageByCustomer, setUsageByCustomer] = useState<Record<string, any>>({});

  const [q, setQ] = useState("");
  const [activeOnly, setActiveOnly] = useState(false);
  const [hoveredCustomerId, setHoveredCustomerId] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Customer | null>(null);

  const [contacts, setContacts] = useState<Contact[]>([]);
  const [contactMethodsByContactId, setContactMethodsByContactId] = useState<Record<string, ContactMethod[]>>({});
  const [contactModalOpen, setContactModalOpen] = useState(false);
  const [editingContact, setEditingContact] = useState<Contact | null>(null);
  const [contactMethods, setContactMethods] = useState<ContactMethod[]>([]);
  const [methodModalOpen, setMethodModalOpen] = useState(false);
  const [editingMethod, setEditingMethod] = useState<ContactMethod | null>(null);
  const [mKind, setMKind] = useState<"phone" | "email" | "whatsapp" | "other">("phone");
  const [mLabel, setMLabel] = useState("");
  const [mValue, setMValue] = useState("");
  const [mIsPrimary, setMIsPrimary] = useState(false);
  const [mCanSms, setMCanSms] = useState(false);
  const [mCanWhatsapp, setMCanWhatsapp] = useState(false);
  const [mActive, setMActive] = useState(true);
  const [mSortOrder, setMSortOrder] = useState(0);
  const [cFirstName, setCFirstName] = useState("");
  const [cLastName, setCLastName] = useState("");
  const [cJobTitle, setCJobTitle] = useState("");
  const [cName, setCName] = useState("");
  const [cEmail, setCEmail] = useState("");
  const [cPhone, setCPhone] = useState("");
  const [cMobilePhone, setCMobilePhone] = useState("");
  const [cRole, setCRole] = useState("");
  const [cDepartment, setCDepartment] = useState("");
  const [cNotes, setCNotes] = useState("");
  const [cIsPrimary, setCIsPrimary] = useState(false);
  const [cActive, setCActive] = useState(true);
  const [cSortOrder, setCSortOrder] = useState(0);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [website, setWebsite] = useState("");
  const [vatNumber, setVatNumber] = useState("");
  const [accountRef, setAccountRef] = useState("");
  const [notes, setNotes] = useState("");
  const [billingName, setBillingName] = useState("");
  const [billingEmail, setBillingEmail] = useState("");
  const [billingPhone, setBillingPhone] = useState("");
  const [billingAddress, setBillingAddress] = useState("");
  const [active, setActive] = useState(true);
  const [metaJson, setMetaJson] = useState("{}");
  const [submitting, setSubmitting] = useState(false);

  function resetForm() {
    setName("");
    setEmail("");
    setPhone("");
    setWebsite("");
    setVatNumber("");
    setAccountRef("");
    setNotes("");
    setBillingName("");
    setBillingEmail("");
    setBillingPhone("");
    setBillingAddress("");
    setActive(true);
    setMetaJson("{}");
  }

  function openCreate() {
    setEditing(null);
    resetForm();
    setModalOpen(true);
  }

  function openEdit(c: Customer) {
    setEditing(c);
    setName(c.name || "");
    setEmail(c.email || "");
    setPhone(c.phone || "");
    setWebsite(c.website || "");
    setVatNumber(c.vat_number || "");
    setAccountRef(c.account_ref || "");
    setNotes(c.notes || "");
    setBillingName(c.billing_name || "");
    setBillingEmail(c.billing_email || "");
    setBillingPhone(c.billing_phone || "");
    setBillingAddress(c.billing_address || "");
    setActive(!!c.active);
    setMetaJson(JSON.stringify(c.meta && typeof c.meta === "object" ? c.meta : {}, null, 2));
    setModalOpen(true);
    if (c.id) loadUsage(c.id);
  }

  function closeModal() {
    setContactModalOpen(false);
    setEditingContact(null);
    setModalOpen(false);
    setEditing(null);
  }

  async function load() {
    setErr("");
    try {
      const list = await api<any[]>("/api/customers");
      setItems(list ?? []);
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function loadUsage(customerId: string) {
    if (usageByCustomer[customerId]) return;
    try {
      const u = await api<any>(`/api/customers/${customerId}/usage`);
      setUsageByCustomer((prev) => ({ ...prev, [customerId]: u }));
    } catch {
      setUsageByCustomer((prev) => ({ ...prev, [customerId]: null }));
    }
  }

  async function loadContacts(customerId: string) {
    try {
      const list = await api<any[]>(`/api/customers/${customerId}/contacts`);
      setContacts(list ?? []);
    } catch {
      setContacts([]);
    }
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (modalOpen && editing?.id) loadContacts(editing.id);
    else setContacts([]);
  }, [modalOpen, editing?.id]);

  const contactIds = useMemo(() => contacts.map((c) => c.id).join(","), [contacts]);
  useEffect(() => {
    if (contacts.length > 0 && modalOpen && editing?.id) {
      loadMethodsForContacts(contacts.map((c) => c.id));
    }
  }, [modalOpen, editing?.id, contactIds]);

  useEffect(() => {
    const hash = window.location.hash?.replace("#", "");
    if (!hash) return;
    const found = items.find((c) => c.id === hash);
    if (found) openEdit(found);
  }, [items]);

  const filtered = useMemo(() => {
    const text = q.trim().toLowerCase();
    return (items || [])
      .filter((c) => {
        if (activeOnly && !c.active) return false;
        if (!text) return true;
        return (
          (c.name || "").toLowerCase().includes(text) ||
          (c.email || "").toLowerCase().includes(text) ||
          (c.phone || "").toLowerCase().includes(text) ||
          (c.account_ref || "").toLowerCase().includes(text) ||
          (c.billing_name || "").toLowerCase().includes(text)
        );
      })
      .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
  }, [items, q, activeOnly]);

  async function saveCustomer() {
    if (submitting) return;
    if (!name.trim()) {
      setErr("Name is required");
      return;
    }
    setErr("");
    setSubmitting(true);
    try {
      let meta: Record<string, unknown> = {};
      try {
        meta = JSON.parse(metaJson.trim() || "{}");
        if (typeof meta !== "object" || meta === null || Array.isArray(meta)) {
          setErr("Meta must be a JSON object");
          return;
        }
      } catch {
        setErr("Meta JSON invalid");
        return;
      }
      const payload = {
        name: name.trim(),
        email: email || "",
        phone: phone || "",
        website: website || "",
        billing_name: billingName || "",
        billing_email: billingEmail || "",
        billing_phone: billingPhone || "",
        billing_address: billingAddress || "",
        vat_number: vatNumber || "",
        account_ref: accountRef || "",
        notes: notes || "",
        meta,
        active,
        default_margin_profile_id: editing?.default_margin_profile_id ?? null,
      };
      if (!payload.name) {
        setErr("Name is required");
        return;
      }
      if (editing) {
        await api(`/api/customers/${editing.id}`, { method: "PUT", body: JSON.stringify(payload) });
      } else {
        await api("/api/customers", { method: "POST", body: JSON.stringify(payload) });
      }
      closeModal();
      await load();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleActive(c: Customer): Promise<boolean> {
    setErr("");
    try {
      await api(`/api/customers/${c.id}`, { method: "PUT", body: JSON.stringify({ active: !c.active }) });
      await load();
      return true;
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
      return false;
    }
  }

  async function del(c: Customer): Promise<boolean> {
    if (!confirm(`Delete customer "${c.name}"?`)) return false;
    setErr("");
    try {
      await api(`/api/customers/${c.id}`, { method: "DELETE" });
      await load();
      return true;
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
      return false;
    }
  }

  async function handleToggleActiveInModal() {
    if (!editing) return;
    const ok = await toggleActive(editing);
    if (ok) closeModal();
  }

  async function handleDeleteInModal() {
    if (!editing) return;
    const deleted = await del(editing);
    if (deleted) closeModal();
  }

  function resetContactForm() {
    setCFirstName("");
    setCLastName("");
    setCJobTitle("");
    setCName("");
    setCEmail("");
    setCPhone("");
    setCMobilePhone("");
    setCRole("");
    setCDepartment("");
    setCNotes("");
    setCIsPrimary(false);
    setCActive(true);
    setCSortOrder(0);
  }

  async function loadContactMethods(contactId: string) {
    try {
      const list = await api<any[]>(`/api/customer-contacts/${contactId}/methods`);
      setContactMethods(list ?? []);
    } catch {
      setContactMethods([]);
    }
  }

  async function loadMethodsForContacts(contactIds: string[]) {
    const out: Record<string, ContactMethod[]> = {};
    await Promise.all(
      contactIds.map(async (id) => {
        try {
          out[id] = await api<any[]>(`/api/customer-contacts/${id}/methods`);
        } catch {
          out[id] = [];
        }
      })
    );
    setContactMethodsByContactId((prev) => ({ ...prev, ...out }));
  }

  function openNewContact() {
    setErr("");
    setEditingContact(null);
    setContactMethods([]);
    resetContactForm();
    setContactModalOpen(true);
  }

  function openEditContact(contact: Contact) {
    setErr("");
    setEditingContact(contact);
    setCFirstName(contact.first_name ?? "");
    setCLastName(contact.last_name ?? "");
    setCJobTitle(contact.job_title ?? "");
    setCName(contact.name || "");
    setCEmail(contact.email || "");
    setCPhone(contact.phone || "");
    setCMobilePhone(contact.mobile_phone || "");
    setCRole(contact.role || "");
    setCDepartment(contact.department || "");
    setCNotes(contact.notes || "");
    setCIsPrimary(!!contact.is_primary);
    setCActive(!!contact.active);
    setCSortOrder(Number(contact.sort_order) || 0);
    setContactModalOpen(true);
    if (contact.id) loadContactMethods(contact.id);
  }

  function closeContactModal() {
    setMethodModalOpen(false);
    setContactModalOpen(false);
    setEditingContact(null);
    setContactMethods([]);
    if (editing?.id) loadContacts(editing.id);
  }

  function openNewMethod(kind: "phone" | "email" | "whatsapp" | "other") {
    setErr("");
    setEditingMethod(null);
    setMKind(kind);
    setMLabel("");
    setMValue("");
    setMIsPrimary(false);
    setMCanSms(kind === "phone" || kind === "whatsapp");
    setMCanWhatsapp(kind === "whatsapp");
    setMActive(true);
    setMSortOrder(0);
    setMethodModalOpen(true);
  }

  function openEditMethod(m: ContactMethod) {
    setErr("");
    setEditingMethod(m);
    setMKind((m.kind || "other") as "phone" | "email" | "whatsapp" | "other");
    setMLabel(m.label || "");
    setMValue(m.value || "");
    setMIsPrimary(!!m.is_primary);
    setMCanSms(!!m.can_sms);
    setMCanWhatsapp(!!m.can_whatsapp);
    setMActive(!!m.active);
    setMSortOrder(Number(m.sort_order) || 0);
    setMethodModalOpen(true);
  }

  function closeMethodModal() {
    setMethodModalOpen(false);
    setEditingMethod(null);
    if (editingContact?.id) {
      loadContactMethods(editingContact.id);
      loadMethodsForContacts(contacts.map((c) => c.id));
    }
  }

  async function saveMethod() {
    if (!editingContact?.id) return;
    setErr("");
    const base = {
      kind: mKind,
      label: mLabel.trim(),
      value: mValue.trim(),
      is_primary: mIsPrimary,
      can_sms: mCanSms,
      can_whatsapp: mCanWhatsapp,
      active: mActive,
      sort_order: mSortOrder,
    };
    try {
      if (editingMethod) {
        await api(`/api/customer-contact-methods/${editingMethod.id}`, {
          method: "PUT",
          body: JSON.stringify(base),
        });
      } else {
        await api("/api/customer-contact-methods", {
          method: "POST",
          body: JSON.stringify({ contact_id: editingContact.id, ...base }),
        });
      }
      closeMethodModal();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function deleteMethod() {
    if (!editingMethod?.id) return;
    if (!confirm("Delete this contact method?")) return;
    setErr("");
    try {
      await api(`/api/customer-contact-methods/${editingMethod.id}`, { method: "DELETE" });
      closeMethodModal();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function saveContact() {
    setErr("");
    if (!editing?.id) {
      setErr("Customer not selected. Close this dialog and open the customer again.");
      return;
    }
    const displayName = [cFirstName.trim(), cLastName.trim()].filter(Boolean).join(" ") || cName.trim();
    const base = {
      first_name: cFirstName.trim(),
      last_name: cLastName.trim(),
      job_title: cJobTitle.trim(),
      department: cDepartment || "",
      name: displayName,
      email: cEmail || "",
      phone: cPhone || "",
      mobile_phone: cMobilePhone || "",
      role: cRole || "",
      notes: cNotes || "",
      is_primary: cIsPrimary,
      active: cActive,
      sort_order: Number(cSortOrder) || 0,
    };
    if (!displayName) {
      setErr("First name, last name, or name is required");
      return;
    }
    try {
      if (editingContact) {
        await api(`/api/customer-contacts/${editingContact.id}`, {
          method: "PUT",
          body: JSON.stringify(base),
        });
      } else {
        await api("/api/customer-contacts", {
          method: "POST",
          body: JSON.stringify({ customer_id: editing.id, ...base }),
        });
      }
      closeContactModal();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  async function deleteContact() {
    if (!editingContact?.id) return;
    if (!confirm(`Delete contact "${editingContact.name}"?`)) return;
    setErr("");
    try {
      await api(`/api/customer-contacts/${editingContact.id}`, { method: "DELETE" });
      closeContactModal();
    } catch (e: any) {
      setErr(e instanceof ApiError ? e.message : String(e));
    }
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0 }}>Customers</h1>
          <div className="subtle">Manage customer records for quotes and billing.</div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button type="button" onClick={load}>Refresh</button>
          <button type="button" className="primary" onClick={openCreate}>New Customer</button>
        </div>
      </div>

      {err && (
        <div className="card" style={{ borderColor: "#c00", whiteSpace: "pre-wrap", marginBottom: 12 }}>
          {err}
        </div>
      )}

      <div className="card section">
        <div className="row" style={{ alignItems: "center" }}>
          <div className="col">
            <input placeholder="Search customers..." value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <div className="col" style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="checkbox" checked={activeOnly} onChange={(e) => setActiveOnly(e.target.checked)} />
              Active only
            </label>
          </div>
        </div>
      </div>

      <div className="card">
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: "0 10px" }}>
            <thead>
              <tr className="subtle" style={{ textAlign: "left" }}>
                <th style={{ padding: "0 10px" }}>Name</th>
                <th style={{ padding: "0 10px" }}>Contact</th>
                <th style={{ padding: "0 10px" }}>Account</th>
                <th style={{ padding: "0 10px" }}></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c, index) => (
                <tr
                  key={c.id}
                  style={{
                    background: hoveredCustomerId === c.id ? "#f0f0f2" : index % 2 === 0 ? "#ffffff" : "#f8f8f8",
                    border: "1px solid #eee",
                    cursor: "pointer",
                  }}
                  onMouseEnter={() => setHoveredCustomerId(c.id)}
                  onMouseLeave={() => setHoveredCustomerId(null)}
                  onDoubleClick={() => openEdit(c)}
                >
                  <td style={{ padding: "12px 10px", borderTopLeftRadius: 12, borderBottomLeftRadius: 12 }}>
                    <div style={{ fontWeight: 600 }}>
                      {c.name} {!c.active && <span className="subtle"> (inactive)</span>}
                    </div>
                    <div className="subtle">{c.website || ""}</div>
                  </td>
                  <td style={{ padding: "12px 10px" }}>
                    <div>{c.email || "-"}</div>
                    <div className="subtle">{c.phone || ""}</div>
                  </td>
                  <td style={{ padding: "12px 10px" }}>
                    <div>{c.account_ref || "-"}</div>
                  </td>
                  <td style={{ padding: "12px 10px", borderTopRightRadius: 12, borderBottomRightRadius: 12 }}>
                    <div
                      style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}
                      onDoubleClick={(e) => e.stopPropagation()}
                    >
                      <button type="button" onClick={() => openEdit(c)} onDoubleClick={(e) => e.stopPropagation()}>
                        Edit
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && <div className="subtle" style={{ marginTop: 10 }}>No customers found.</div>}
      </div>

      <Modal
        open={modalOpen}
        title={editing ? "Edit Customer" : "New Customer"}
        onClose={closeModal}
        wide
      >
        <form
          style={{ display: "grid", gap: 12 }}
          onSubmit={(e) => {
            e.preventDefault();
            saveCustomer();
          }}
        >
          {editing && !editing.active && (
            <div
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                background: "rgba(255, 149, 0, 0.12)",
                border: "1px solid rgba(255, 149, 0, 0.3)",
                color: "#b45309",
                fontSize: 14,
              }}
            >
              This customer is inactive.
            </div>
          )}

          <div className="row">
            <div className="col">
              <label className="subtle">Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">Email</label>
              <input value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">Phone</label>
              <input value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
          </div>

          <div className="row">
            <div className="col">
              <label className="subtle">Website</label>
              <input value={website} onChange={(e) => setWebsite(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">VAT number</label>
              <input value={vatNumber} onChange={(e) => setVatNumber(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">Account ref</label>
              <input value={accountRef} onChange={(e) => setAccountRef(e.target.value)} />
            </div>
          </div>

          <div className="row">
            <div className="col">
              <label className="subtle">Notes</label>
              <textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
          </div>

          <div style={{ borderTop: "1px solid #eee", paddingTop: 12 }}>
            <div className="subtle" style={{ marginBottom: 8 }}>Billing</div>
            <div className="row">
              <div className="col">
                <label className="subtle">Billing name</label>
                <input value={billingName} onChange={(e) => setBillingName(e.target.value)} />
              </div>
              <div className="col">
                <label className="subtle">Billing email</label>
                <input value={billingEmail} onChange={(e) => setBillingEmail(e.target.value)} />
              </div>
              <div className="col">
                <label className="subtle">Billing phone</label>
                <input value={billingPhone} onChange={(e) => setBillingPhone(e.target.value)} />
              </div>
            </div>
            <div className="row">
              <div className="col">
                <label className="subtle">Billing address</label>
                <textarea rows={2} value={billingAddress} onChange={(e) => setBillingAddress(e.target.value)} />
              </div>
            </div>
          </div>

          <div>
            <label className="subtle">Meta (optional JSON)</label>
            <textarea
              rows={3}
              value={metaJson}
              onChange={(e) => setMetaJson(e.target.value)}
              style={{ fontFamily: "monospace", fontSize: 12, width: "100%", marginTop: 4 }}
              placeholder='{"key": "value"}'
            />
          </div>

          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
            Active
          </label>

          {editing && editing.id && (
            <div style={{ borderTop: "1px solid #eee", paddingTop: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <div className="subtle">Contacts</div>
                <button type="button" onClick={openNewContact}>
                  New Contact
                </button>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                  <thead>
                    <tr className="subtle" style={{ textAlign: "left" }}>
                      <th style={{ padding: "6px 8px" }}>Name</th>
                      <th style={{ padding: "6px 8px" }}>Email</th>
                      <th style={{ padding: "6px 8px" }}>Mobile</th>
                      <th style={{ padding: "6px 8px" }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contacts.map((ct, index) => {
                      const displayName = [ct.first_name, ct.last_name].filter(Boolean).join(" ") || ct.name || "-";
                      const displayEmail = ct.email ?? "-";
                      const rawMobile = ct.mobile_phone || ct.phone || "";
                      const telValue = rawMobile.replace(/\s+/g, "");
                      return (
                        <tr
                          key={ct.id}
                          style={{
                            background: index % 2 === 0 ? "#fff" : "#f8f8f8",
                            border: "1px solid #eee",
                            cursor: "pointer",
                          }}
                          onDoubleClick={() => openEditContact(ct)}
                        >
                          <td style={{ padding: "8px" }}>{displayName}</td>
                          <td style={{ padding: "8px" }}>{displayEmail}</td>
                          <td style={{ padding: "8px" }}>
                            {rawMobile ? (
                              <a
                                href={`tel:${telValue}`}
                                className="contact-phone"
                                onClick={(e) => e.stopPropagation()}
                              >
                                {rawMobile}
                              </a>
                            ) : (
                              "-"
                            )}
                          </td>
                          <td style={{ padding: "8px" }}>
                            <button type="button" onClick={(e) => { e.stopPropagation(); openEditContact(ct); }}>
                              Edit
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {contacts.length === 0 && (
                <div className="subtle" style={{ fontSize: 14, marginTop: 8 }}>No contacts yet.</div>
              )}
            </div>
          )}

          {err && modalOpen && (
            <div style={{ color: "#c00", fontSize: 14, whiteSpace: "pre-wrap" }}>{err}</div>
          )}

          {editing && (
            <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 12, background: "#fafafa" }}>
              {usageByCustomer[editing.id] != null ? (
                <div style={{ fontSize: 14 }}>
                  <div>Quotes: {usageByCustomer[editing.id].quotes_count ?? 0}</div>
                </div>
              ) : (
                <div className="subtle" style={{ fontSize: 14 }}>Usage data unavailable.</div>
              )}
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 8 }}>
            <div style={{ display: "flex", gap: 10 }}>
              {editing && (
                <>
<button type="button" onClick={handleToggleActiveInModal}>
                  {editing.active ? "Deactivate" : "Activate"}
                  </button>
                  <button type="button" className="danger" onClick={handleDeleteInModal}>
                    Delete Customer
                  </button>
                </>
              )}
            </div>
            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <button type="button" onClick={closeModal}>Cancel</button>
              <button
                type="button"
                className="primary"
                disabled={!name.trim() || submitting}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  saveCustomer();
                }}
                onPointerDown={(e) => {
                  e.stopPropagation();
                  if (name.trim() && !submitting) {
                    e.preventDefault();
                    saveCustomer();
                  }
                }}
              >
                {submitting ? "Saving…" : editing ? "Save changes" : "Create customer"}
              </button>
              {!name.trim() && (
                <span className="subtle" style={{ fontSize: 13 }}>Enter a name above to enable Create</span>
              )}
            </div>
          </div>
        </form>
      </Modal>

      <Modal
        open={contactModalOpen}
        title={editingContact ? "Edit Contact" : "New Contact"}
        onClose={closeContactModal}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <div className="row">
            <div className="col">
              <label className="subtle">First name</label>
              <input value={cFirstName} onChange={(e) => setCFirstName(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">Last name</label>
              <input value={cLastName} onChange={(e) => setCLastName(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">Job title</label>
              <input value={cJobTitle} onChange={(e) => setCJobTitle(e.target.value)} />
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Name (legacy)</label>
              <input value={cName} onChange={(e) => setCName(e.target.value)} placeholder="Or use first + last above" />
            </div>
            <div className="col">
              <label className="subtle">Department</label>
              <input value={cDepartment} onChange={(e) => setCDepartment(e.target.value)} />
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Email</label>
              <input value={cEmail} onChange={(e) => setCEmail(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">Phone</label>
              <input value={cPhone} onChange={(e) => setCPhone(e.target.value)} />
            </div>
            <div className="col">
              <label className="subtle">Mobile</label>
              <input value={cMobilePhone} onChange={(e) => setCMobilePhone(e.target.value)} />
            </div>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Role</label>
              <input value={cRole} onChange={(e) => setCRole(e.target.value)} placeholder="e.g. Buyer, Accounts" />
            </div>
            <div className="col">
              <label className="subtle">Sort order</label>
              <input
                type="number"
                value={cSortOrder}
                onChange={(e) => setCSortOrder(Number(e.target.value) || 0)}
              />
            </div>
          </div>

          {editingContact?.id && (
            <div style={{ borderTop: "1px solid #eee", paddingTop: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, flexWrap: "wrap", gap: 8 }}>
                <div className="subtle">Contact methods</div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button type="button" onClick={() => openNewMethod("phone")}>+ Add phone</button>
                  <button type="button" onClick={() => openNewMethod("email")}>+ Add email</button>
                  <button type="button" onClick={() => openNewMethod("whatsapp")}>+ Add WhatsApp</button>
                </div>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr className="subtle" style={{ textAlign: "left" }}>
                      <th style={{ padding: "4px 8px" }}>Kind</th>
                      <th style={{ padding: "4px 8px" }}>Label</th>
                      <th style={{ padding: "4px 8px" }}>Value</th>
                      <th style={{ padding: "4px 8px" }}>Primary</th>
                      <th style={{ padding: "4px 8px" }}>SMS</th>
                      <th style={{ padding: "4px 8px" }}>WhatsApp</th>
                      <th style={{ padding: "4px 8px" }}>Active</th>
                      <th style={{ padding: "4px 8px" }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {contactMethods.map((meth: ContactMethod, idx: number) => (
                      <tr key={meth.id} style={{ background: idx % 2 === 0 ? "#fff" : "#f8f8f8", border: "1px solid #eee" }}>
                        <td style={{ padding: "6px 8px" }}>{meth.kind}</td>
                        <td style={{ padding: "6px 8px" }}>{meth.label || "-"}</td>
                        <td style={{ padding: "6px 8px" }}>{meth.value || "-"}</td>
                        <td style={{ padding: "6px 8px" }}>{meth.is_primary ? "Yes" : ""}</td>
                        <td style={{ padding: "6px 8px" }}>{meth.can_sms ? "Yes" : ""}</td>
                        <td style={{ padding: "6px 8px" }}>{meth.can_whatsapp ? "Yes" : ""}</td>
                        <td style={{ padding: "6px 8px" }}>{meth.active ? "Yes" : ""}</td>
                        <td style={{ padding: "6px 8px" }}>
                          <button type="button" onClick={() => openEditMethod(meth)}>Edit</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {contactMethods.length === 0 && (
                <div className="subtle" style={{ fontSize: 13, marginTop: 6 }}>No contact methods yet.</div>
              )}
            </div>
          )}

          <div className="row">
            <div className="col">
              <label className="subtle">Notes</label>
              <textarea rows={2} value={cNotes} onChange={(e) => setCNotes(e.target.value)} />
            </div>
          </div>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="checkbox" checked={cIsPrimary} onChange={(e) => setCIsPrimary(e.target.checked)} />
              Primary contact
            </label>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="checkbox" checked={cActive} onChange={(e) => setCActive(e.target.checked)} />
              Active
            </label>
          </div>
          {err && contactModalOpen && (
            <div style={{ color: "#c00", fontSize: 14, whiteSpace: "pre-wrap" }}>{err}</div>
          )}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 8 }}>
            <div style={{ display: "flex", gap: 10 }}>
              {editingContact && (
                <button type="button" className="danger" onClick={deleteContact}>
                  Delete
                </button>
              )}
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button type="button" onClick={closeContactModal}>Cancel</button>
              <button
                type="button"
                className="primary"
                onClick={saveContact}
                disabled={!cName.trim() && !cFirstName.trim() && !cLastName.trim()}
              >
                {editingContact ? "Save changes" : "Create contact"}
              </button>
            </div>
          </div>
        </div>
      </Modal>

      <Modal
        open={methodModalOpen}
        title={editingMethod ? "Edit contact method" : "Add contact method"}
        onClose={closeMethodModal}
      >
        <div style={{ display: "grid", gap: 12 }}>
          <div className="row">
            <div className="col">
              <label className="subtle">Kind</label>
              <select value={mKind} onChange={(e) => setMKind(e.target.value as "phone" | "email" | "whatsapp" | "other")}>
                <option value="phone">phone</option>
                <option value="email">email</option>
                <option value="whatsapp">whatsapp</option>
                <option value="other">other</option>
              </select>
            </div>
            <div className="col">
              <label className="subtle">Label</label>
              <input value={mLabel} onChange={(e) => setMLabel(e.target.value)} placeholder="Work, Mobile, Direct..." />
            </div>
            <div className="col">
              <label className="subtle">Value</label>
              <input value={mValue} onChange={(e) => setMValue(e.target.value)} placeholder="Number or address" />
            </div>
          </div>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="checkbox" checked={mIsPrimary} onChange={(e) => setMIsPrimary(e.target.checked)} />
              Primary (for this kind)
            </label>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="checkbox" checked={mCanSms} onChange={(e) => setMCanSms(e.target.checked)} />
              Can SMS
            </label>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="checkbox" checked={mCanWhatsapp} onChange={(e) => setMCanWhatsapp(e.target.checked)} />
              WhatsApp
            </label>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="checkbox" checked={mActive} onChange={(e) => setMActive(e.target.checked)} />
              Active
            </label>
          </div>
          <div className="row">
            <div className="col">
              <label className="subtle">Sort order</label>
              <input type="number" value={mSortOrder} onChange={(e) => setMSortOrder(Number(e.target.value) || 0)} />
            </div>
          </div>
          {err && methodModalOpen && (
            <div style={{ color: "#c00", fontSize: 14, whiteSpace: "pre-wrap" }}>{err}</div>
          )}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 8 }}>
            <div>
              {editingMethod && (
                <button type="button" className="danger" onClick={deleteMethod}>
                  Delete
                </button>
              )}
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button type="button" onClick={closeMethodModal}>Cancel</button>
              <button type="button" className="primary" onClick={saveMethod}>
                {editingMethod ? "Save changes" : "Add method"}
              </button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}
