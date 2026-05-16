export function emitToast({ type = "success", message, duration = 3000 }) {
  if (!message || typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent("app:toast", { detail: { type, message, duration } }));
}

export function refreshAppSignals() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event("app:refresh-signals"));
}
