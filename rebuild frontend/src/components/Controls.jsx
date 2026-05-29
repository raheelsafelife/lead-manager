import { Children, cloneElement, isValidElement, useId } from "react";

export function PageHeader({ children }) {
  return <div className="main-header">{children}</div>;
}

export function Button({ children, active, variant = "secondary", className = "", ...props }) {
  return <button className={`btn ${active || variant === "primary" ? "btn-primary" : "btn-secondary"} ${className}`.trim()} {...props}>{children}</button>;
}

function controlName(value) {
  return String(value || "field")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "") || "field";
}

export function Field({ label, required, children }) {
  const reactId = useId().replace(/[^a-z0-9]/gi, "");
  const fallbackName = controlName(label);
  const fallbackId = `${fallbackName}_${reactId}`;
  let renderedChildren = children;

  try {
    const child = Children.only(children);
    if (isValidElement(child)) {
      renderedChildren = cloneElement(child, {
        id: child.props.id || fallbackId,
        name: child.props.name || fallbackName
      });
    }
  } catch {
    renderedChildren = children;
  }

  return <label className="field" htmlFor={fallbackId}><span>{label}{required && <b>*</b>}</span>{renderedChildren}</label>;
}

export function Select({ value, onChange, options, ...props }) {
  const reactId = useId().replace(/[^a-z0-9]/gi, "");
  const id = props.id || `select_${reactId}`;
  const name = props.name || id;
  return <select id={id} name={name} value={value || ""} onChange={(e) => onChange(e.target.value)} {...props}>{options.map((option) => <option key={option} value={option}>{option}</option>)}</select>;
}

export function StatusPill({ value }) {
  return <span className={`status-pill ${String(value || "Not Called").toLowerCase().replaceAll(" ", "-")}`}>{value || "Not Called"}</span>;
}

export function Modal({ title, children, onClose }) {
  return <div className="modal-backdrop"><div className="modal"><button className="modal-x" onClick={onClose}>×</button>{title ? <h2>{title}</h2> : null}{children}</div></div>;
}
