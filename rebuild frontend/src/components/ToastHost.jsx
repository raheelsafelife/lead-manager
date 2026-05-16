import { CheckCircle2, Info, TriangleAlert, X, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

const icons = {
  success: CheckCircle2,
  error: XCircle,
  warning: TriangleAlert,
  info: Info
};

export default function ToastHost() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    function onToast(event) {
      const id = `${Date.now()}-${Math.random()}`;
      const toast = { id, type: "success", duration: 3000, ...event.detail };
      setToasts((items) => [...items, toast].slice(-4));
      window.setTimeout(() => {
        setToasts((items) => items.filter((item) => item.id !== id));
      }, toast.duration);
    }

    window.addEventListener("app:toast", onToast);
    return () => window.removeEventListener("app:toast", onToast);
  }, []);

  if (!toasts.length) return null;

  return (
    <div className="toast-stack" role="status" aria-live="polite">
      {toasts.map((toast) => {
        const Icon = icons[toast.type] || icons.info;
        return (
          <article className={`toast toast-${toast.type}`} key={toast.id}>
            <Icon size={20} />
            <span>{toast.message}</span>
            <button onClick={() => setToasts((items) => items.filter((item) => item.id !== toast.id))} aria-label="Dismiss message">
              <X size={16} />
            </button>
          </article>
        );
      })}
    </div>
  );
}
