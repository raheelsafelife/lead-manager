import axios from "axios";
import { emitToast, refreshAppSignals } from "../utils/appEvents";

const devApiBase = "http://127.0.0.1:3001/api";
const runtimeDefault = import.meta.env.DEV ? devApiBase : `${window.location.origin}/api`;

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || runtimeDefault,
  timeout: 12000
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("lead_manager_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

function cleanUrl(url = "") {
  return String(url).replace(/^https?:\/\/[^/]+\/api/i, "").replace(/^\/api/i, "");
}

function successMessage(config = {}) {
  const method = String(config.method || "get").toLowerCase();
  const url = cleanUrl(config.url || "");
  let data = {};
  if (config.data && !(config.data instanceof FormData)) {
    if (typeof config.data === "string") {
      try { data = JSON.parse(config.data); } catch { data = {}; }
    } else if (typeof config.data === "object") {
      data = config.data;
    }
  }
  if (method === "get" || url.includes("/notifications/read")) return "";
  if (url === "/auth/login") return "Login successful";
  if (url === "/auth/logout") return "Logged out successfully";
  if (url === "/auth/signup") return "Account created successfully. Pending admin approval.";
  if (url === "/auth/forgot") return "Password reset request sent successfully";
  if (method === "post" && url === "/leads") return "";
  if (method === "patch" && /^\/leads\/[^/]+$/.test(url)) {
    if (data.care_status === "Care Start") return "Care Start marked successfully";
    if (Number(data.authorization_received) === 1) return "Authorization marked successfully";
    if (Number(data.active_client) === 1 && Number(data.authorization_received) === 0) return "Referral marked successfully";
    if (Number(data.authorization_received) === 0 && !data.active_client) return "Authorization removed successfully";
    return "Lead updated successfully";
  }
  if (method === "post" && /\/leads\/[^/]+\/comment$/.test(url)) return "Comment added successfully";
  if (method === "post" && /\/leads\/[^/]+\/attachment$/.test(url)) return "Attachment uploaded successfully";
  if (method === "post" && /\/leads\/[^/]+\/soft-delete$/.test(url)) return "Lead moved to recycle bin";
  if (method === "post" && /\/leads\/[^/]+\/restore$/.test(url)) return "Lead restored successfully";
  if (method === "delete" && /^\/leads\/[^/]+$/.test(url)) return "Lead permanently deleted";
  if (method === "delete" && /^\/attachments\/[^/]+$/.test(url)) return "Attachment deleted successfully";
  if (method === "post" && url === "/users") return "User created successfully";
  if (method === "patch" && /^\/users\/[^/]+$/.test(url)) return data.is_approved === 1 ? "User approved successfully" : "User updated successfully";
  if (method === "delete" && /^\/users\/[^/]+$/.test(url)) return "User deleted successfully";
  if (method === "post" && /\/users\/[^/]+\/reset-password$/.test(url)) return "User password reset successfully";
  if (method === "patch" && url === "/users/me") return "Profile updated successfully";
  if (method === "post" && url === "/users/me/password") return "Password changed successfully";
  if (method === "post" && url === "/users/me/request-reset") return "Password reset request sent successfully";
  if (method === "post" && /^\/admin\/event$/.test(url)) return "Event created successfully";
  if (method === "post" && /^\/admin\/agency$/.test(url)) return "Payor created successfully";
  if (method === "post" && /^\/admin\/ccu$/.test(url)) return "CCU created successfully";
  if (method === "delete" && /^\/admin\/event\//.test(url)) return "Event deleted successfully";
  if (method === "delete" && /^\/admin\/agency\//.test(url)) return "Payor deleted successfully";
  if (method === "delete" && /^\/admin\/ccu\//.test(url)) return "CCU deleted successfully";
  if (method === "post" && url === "/ccus") return "CCU created successfully";
  if (method === "patch" && /^\/ccus\/[^/]+$/.test(url)) return "CCU details updated successfully";
  if (method === "patch" && /^\/agencies\/[^/]+$/.test(url)) return "Payor details updated successfully";
  if (method === "post" && url === "/reports/word") return "Report generated successfully";
  return "Operation completed successfully";
}

function shouldRefreshSignals(config = {}) {
  const method = String(config.method || "get").toLowerCase();
  const url = cleanUrl(config.url || "");
  return method !== "get" && !url.includes("/notifications/read");
}

api.interceptors.response.use(
  (response) => {
    const message = successMessage(response.config);
    if (message) emitToast({ type: "success", message });
    if (shouldRefreshSignals(response.config)) refreshAppSignals();
    return response;
  },
  (error) => {
    const method = String(error.config?.method || "get").toLowerCase();
    if (method !== "get") {
      emitToast({ type: error.response?.status === 409 ? "warning" : "error", message: error.response?.data?.error || "Operation failed" });
    }
    return Promise.reject(error);
  }
);

export function downloadUrl(path, params = {}) {
  const url = new URL(`${api.defaults.baseURL}${path}`);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  });
  return url.toString();
}

export function previewUrl(path, params = {}) {
  const token = localStorage.getItem("lead_manager_token");
  const url = new URL(`${api.defaults.baseURL}${path}`);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  });
  if (token) url.searchParams.set("token", token);
  return url.toString();
}

function fileNameFromDisposition(headerValue, fallbackName) {
  if (!headerValue) return fallbackName;
  const utfMatch = headerValue.match(/filename\*=UTF-8''([^;]+)/i);
  if (utfMatch?.[1]) return decodeURIComponent(utfMatch[1]);
  const basicMatch = headerValue.match(/filename="?([^"]+)"?/i);
  return basicMatch?.[1] || fallbackName;
}

export async function downloadFile(path, params = {}, fallbackName = "download") {
  const response = await api.get(path, {
    params,
    responseType: "blob"
  });
  const blobUrl = window.URL.createObjectURL(response.data);
  const fileName = fileNameFromDisposition(response.headers["content-disposition"], fallbackName);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export async function openFile(path, params = {}, fallbackName = "preview") {
  const response = await api.get(path, {
    params,
    responseType: "blob"
  });
  const blobUrl = window.URL.createObjectURL(response.data);
  const fileName = fileNameFromDisposition(response.headers["content-disposition"], fallbackName);
  const openedWindow = window.open(blobUrl, "_blank", "noopener,noreferrer");

  if (!openedWindow) {
    const fallbackLink = document.createElement("a");
    fallbackLink.href = blobUrl;
    fallbackLink.download = fileName;
    document.body.appendChild(fallbackLink);
    fallbackLink.click();
    fallbackLink.remove();
  }

  window.setTimeout(() => {
    window.URL.revokeObjectURL(blobUrl);
  }, 60_000);
}
