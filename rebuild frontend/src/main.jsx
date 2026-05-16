import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, useLocation } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext.jsx";
import App from "./App.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import ToastHost from "./components/ToastHost.jsx";
import { ConfirmProvider } from "./components/ConfirmProvider.jsx";
import "./styles.css";

const rootNode = document.getElementById("root");
if (!rootNode) throw new Error("Root element #root was not found");

function AppFrame() {
  const location = useLocation();
  return (
    <ErrorBoundary resetKey={location.pathname}>
      <AuthProvider>
        <ConfirmProvider>
          <App />
          <ToastHost />
        </ConfirmProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

createRoot(rootNode).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppFrame />
    </BrowserRouter>
  </React.StrictMode>
);
