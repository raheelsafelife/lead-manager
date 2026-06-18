import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { Button, Modal } from "./Controls";

const ConfirmContext = createContext(null);

const defaultOptions = {
  title: "Confirm Action",
  message: "Do you want to perform this action?",
  confirmText: "Yes",
  cancelText: "No",
  variant: "primary"
};

export function ConfirmProvider({ children }) {
  const [request, setRequest] = useState(null);
  const [running, setRunning] = useState(false);

  const confirmAction = useCallback((options) => {
    setRequest({ ...defaultOptions, ...options });
  }, []);

  const cancel = useCallback(() => {
    if (running) return;
    setRequest(null);
  }, [running]);

  const run = useCallback(async () => {
    if (!request?.onConfirm) {
      setRequest(null);
      return;
    }
    setRunning(true);
    try {
      await request.onConfirm();
      setRequest(null);
    } catch {
      // API errors already surface through the shared toast interceptor.
    } finally {
      setRunning(false);
    }
  }, [request]);

  const value = useMemo(() => ({ confirmAction }), [confirmAction]);

  return (
    <ConfirmContext.Provider value={value}>
      {children}
      {request && (
        <Modal title={request.title} onClose={cancel}>
          <div className="confirm-dialog">
            <p>{request.message}</p>
            {request.detail && <small>{request.detail}</small>}
            <div className="action-row confirm-actions">
              <Button variant={request.variant === "danger" ? "secondary" : "primary"} className={request.variant === "danger" ? "btn-danger" : ""} onClick={run} disabled={running}>
                {running ? "Working..." : request.confirmText}
              </Button>
              <Button onClick={cancel} disabled={running}>{request.cancelText}</Button>
            </div>
          </div>
        </Modal>
      )}
    </ConfirmContext.Provider>
  );
}

export function useConfirm() {
  const value = useContext(ConfirmContext);
  if (!value) throw new Error("useConfirm must be used inside ConfirmProvider");
  return value.confirmAction;
}
