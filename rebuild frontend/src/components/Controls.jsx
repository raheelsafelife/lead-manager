export function PageHeader({ children }) {
  return <div className="main-header">{children}</div>;
}

export function Button({ children, active, variant = "secondary", className = "", ...props }) {
  return <button className={`btn ${active || variant === "primary" ? "btn-primary" : "btn-secondary"} ${className}`.trim()} {...props}>{children}</button>;
}

export function Field({ label, required, children }) {
  return <label className="field"><span>{label}{required && <b>*</b>}</span>{children}</label>;
}

export function Select({ value, onChange, options, ...props }) {
  return <select value={value || ""} onChange={(e) => onChange(e.target.value)} {...props}>{options.map((option) => <option key={option} value={option}>{option}</option>)}</select>;
}

export function StatusPill({ value }) {
  return <span className={`status-pill ${String(value || "Not Called").toLowerCase().replaceAll(" ", "-")}`}>{value || "Not Called"}</span>;
}

export function Modal({ title, children, onClose }) {
  return <div className="modal-backdrop"><div className="modal"><button className="modal-x" onClick={onClose}>×</button>{title ? <h2>{title}</h2> : null}{children}</div></div>;
}
