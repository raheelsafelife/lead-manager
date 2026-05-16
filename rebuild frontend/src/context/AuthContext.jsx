import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../services/api";

const AuthContext = createContext(null);

function readTokenUser() {
  const cached = localStorage.getItem("lead_manager_user");
  if (cached) {
    try {
      return JSON.parse(cached);
    } catch {
      localStorage.removeItem("lead_manager_user");
    }
  }
  const token = localStorage.getItem("lead_manager_token");
  if (!token) return null;
  try {
    const [, payload] = token.split(".");
    const data = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return {
      id: data.user_id,
      user_id: data.employee_id,
      username: data.username || data.sub,
      role: data.role || "user",
      is_approved: true
    };
  } catch {
    localStorage.removeItem("lead_manager_token");
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUserState] = useState(() => readTokenUser());
  const [loading] = useState(false);

  function setUser(value) {
    setUserState((current) => {
      const next = typeof value === "function" ? value(current) : value;
      if (next) localStorage.setItem("lead_manager_user", JSON.stringify(next));
      else localStorage.removeItem("lead_manager_user");
      return next;
    });
  }

  useEffect(() => {
    let mounted = true;
    const token = localStorage.getItem("lead_manager_token");
    if (!token) return () => {};
    api.get("/auth/me")
      .then((res) => {
        if (mounted) setUser(res.data.user);
      })
      .catch(() => {
        localStorage.removeItem("lead_manager_token");
        if (mounted) setUser(null);
      });
    return () => {
      mounted = false;
    };
  }, []);

  async function login(username, password) {
    const res = await api.post("/auth/login", { username, password });
    localStorage.setItem("lead_manager_token", res.data.token);
    setUser(res.data.user);
  }

  async function logout() {
    try { await api.post("/auth/logout"); } catch {}
    localStorage.removeItem("lead_manager_token");
    localStorage.removeItem("lead_manager_user");
    setUser(null);
  }

  const value = useMemo(() => ({ user, loading, login, logout, setUser }), [user, loading]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
