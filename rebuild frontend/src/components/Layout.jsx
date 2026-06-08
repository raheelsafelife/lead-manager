import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { Activity, BarChart3, Bell, Check, ChevronDown, FileClock, FilePlus2, FileText, Home, LogIn, LogOut, MessageCircleMore, PanelLeftClose, PanelLeftOpen, Pencil, Search, Settings, ShieldCheck, Volume2, VolumeX, UserCog, Users, X } from "lucide-react";
import logoMark from "../../favicon.svg";
import sidebarLogo from "../../sidebar_logo.png";
import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { isAdminRole } from "../utils/roles";
import SmartSearch from "./SmartSearch";
import { emitToast } from "../utils/appEvents";

const nav = [
  ["/dashboard", Home, "Dashboard"],
  ["/lead-discovery", Search, "Lead Discovery"],
  ["/add-lead", FilePlus2, "Add Lead"],
  ["/view-leads", Users, "View Leads"],
  ["/referrals", FileText, "Referrals Sent"],
  ["/authorizations", ShieldCheck, "Authorizations"],
  ["/reports", BarChart3, "Reports"],
  ["/activity", Activity, "Activity Logs"]
];

const pageTitles = {
  "/dashboard": "Dashboard",
  "/lead-discovery": "Lead Discovery",
  "/add-lead": "Add Lead",
  "/view-leads": "View Leads",
  "/referrals": "Referral Sent",
  "/authorizations": "Authorizations",
  "/mark-referral": "Mark Referral",
  "/reports": "Reports",
  "/activity": "Activity Logs",
  "/settings": "User Settings",
  "/users": "System Management"
};

export default function Layout({ children }) {
  const { user, logout, setUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [notificationTotal, setNotificationTotal] = useState(0);
  const [soundEnabled, setSoundEnabled] = useState(() => {
    if (typeof window === "undefined") return true;
    return window.localStorage.getItem("notificationSoundEnabled") !== "false";
  });
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [historianRows, setHistorianRows] = useState([]);
  const [userDirectory, setUserDirectory] = useState({});
  const soundUnlockedRef = useRef(false);
  const audioContextRef = useRef(null);
  const notificationReadyRef = useRef(false);
  const notificationCountRef = useRef(0);
  const title = Object.entries(pageTitles).find(([path]) => location.pathname === path || location.pathname.startsWith(`${path}/`))?.[1] || "Dashboard";
  const showTopbarSmartSearch = location.pathname !== "/dashboard";
  const regionLocale = typeof navigator !== "undefined" ? navigator.languages?.[0] || navigator.language || "en-US" : "en-US";
  const regionTimeZone = typeof Intl !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : "UTC";

  function unlockNotificationSound() {
    soundUnlockedRef.current = true;
  }

  function playNotificationSound() {
    if (!soundEnabled || !soundUnlockedRef.current || typeof window === "undefined") return;
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;
      const context = audioContextRef.current || new AudioContext();
      audioContextRef.current = context;
      if (context.state === "suspended") context.resume();

      const now = context.currentTime;
      const gain = context.createGain();
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(0.22, now + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.55);
      gain.connect(context.destination);

      [660, 880].forEach((frequency, index) => {
        const oscillator = context.createOscillator();
        oscillator.type = "sine";
        oscillator.frequency.setValueAtTime(frequency, now + index * 0.11);
        oscillator.connect(gain);
        oscillator.start(now + index * 0.11);
        oscillator.stop(now + 0.34 + index * 0.11);
      });
    } catch {
      // Browsers may still block audio in strict modes; notification toast remains visible.
    }
  }

  function toggleNotificationSound() {
    setSoundEnabled((enabled) => {
      const next = !enabled;
      if (typeof window !== "undefined") window.localStorage.setItem("notificationSoundEnabled", String(next));
      return next;
    });
  }

  useEffect(() => {
    const unlock = () => unlockNotificationSound();
    window.addEventListener("pointerdown", unlock, { once: true });
    window.addEventListener("keydown", unlock, { once: true });
    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
      audioContextRef.current?.close?.();
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    async function loadMountedSidebarData() {
      try {
        const bootstrapRes = await api.get("/bootstrap");
        const notificationData = bootstrapRes.data.notifications || {};
        const activityData = bootstrapRes.data.activity || {};
        const lookupData = bootstrapRes.data.lookups || {};
        if (mounted) {
          if (bootstrapRes.data.user) setUser((current) => ({ ...current, ...bootstrapRes.data.user }));
          setNotifications(notificationData.notifications || []);
          setNotificationTotal(notificationData.count || 0);
          setHistorianRows(activityData.rows || []);
          setUserDirectory(Object.fromEntries((lookupData.users || []).map((entry) => [entry.username, entry])));
          const nextCount = notificationData.count || 0;
          const firstUnread = (notificationData.notifications || []).find((item) => !item.read);
          if (notificationReadyRef.current && nextCount > notificationCountRef.current && firstUnread) {
            playNotificationSound();
            emitToast({ type: "info", message: `New notification: ${firstUnread.title}` });
          }
          notificationReadyRef.current = true;
          notificationCountRef.current = nextCount;
        }
      } catch {
        if (mounted) {
          setNotifications([]);
          setNotificationTotal(0);
          setHistorianRows([]);
          setUserDirectory({});
        }
      }
    }
    loadMountedSidebarData();
    window.addEventListener("app:refresh-signals", loadMountedSidebarData);
    const interval = setInterval(loadMountedSidebarData, 60000);
    return () => {
      mounted = false;
      window.removeEventListener("app:refresh-signals", loadMountedSidebarData);
      clearInterval(interval);
    };
  }, [soundEnabled]);

  function goNotification(item) {
    setNotificationOpen(false);
    navigate(item.link || "/dashboard");
  }

  async function markAllRead() {
    await api.post("/notifications/read-all");
    setNotifications((items) => items.map((item) => ({ ...item, read: true })));
    setNotificationTotal(0);
    notificationCountRef.current = 0;
  }

  async function markOneRead(id) {
    await api.post("/notifications/read", { id });
    setNotifications((items) => items.filter((item) => item.id !== id));
    setNotificationTotal((count) => Math.max(0, count - 1));
    notificationCountRef.current = Math.max(0, notificationCountRef.current - 1);
  }

  function parseServerTimestamp(value) {
    if (!value) return null;
    if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
    const raw = String(value).trim();
    if (!/\d{4}-\d{2}-\d{2}/.test(raw) && !/[A-Za-z]{3,}/.test(raw)) return null;
    const normalized = raw.replace(" ", "T");
    const utcLike = normalized.endsWith("Z") ? normalized : `${normalized}Z`;
    const date = new Date(utcLike);
    if (!Number.isNaN(date.getTime())) return date;
    const fallback = new Date(normalized);
    return Number.isNaN(fallback.getTime()) ? null : fallback;
  }

  function relativeTime(value) {
    if (!value) return "";
    const date = parseServerTimestamp(value);
    if (!date) return value;
    const diff = Date.now() - date.getTime();
    const minute = 60 * 1000;
    const hour = 60 * minute;
    const day = 24 * hour;
    const month = 30 * day;
    if (diff < minute && diff >= 0) return "just now";
    if (diff < hour && diff >= 0) {
      const count = Math.max(1, Math.round(diff / minute));
      return `${count} minute${count === 1 ? "" : "s"} ago`;
    }
    if (diff < day && diff >= 0) {
      const count = Math.max(1, Math.round(diff / hour));
      return `${count} hour${count === 1 ? "" : "s"} ago`;
    }
    if (diff < month && diff >= 0) {
      const count = Math.max(1, Math.round(diff / day));
      return `${count} day${count === 1 ? "" : "s"} ago`;
    }
    if (diff >= 0) {
      const count = Math.max(1, Math.round(diff / month));
      return `${count} month${count === 1 ? "" : "s"} ago`;
    }
    return date.toLocaleDateString();
  }

  function exactTime(value) {
    if (!value) return "";
    const date = parseServerTimestamp(value);
    if (!date) return value;
    return new Intl.DateTimeFormat(regionLocale, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: regionTimeZone,
      timeZoneName: "short"
    }).format(date);
  }

  function notificationTime(item) {
    const relative = relativeTime(item.detail);
    const exact = exactTime(item.detail);
    if (!relative && !exact) return "";
    return `${relative}${relative && exact ? " at " : ""}${exact.split(", ")[1] || exact}`;
  }

  function parseJsonMaybe(value) {
    if (!value) return null;
    try {
      return JSON.parse(value);
    } catch {
      return null;
    }
  }

  function historianTone(actionType = "") {
    if (actionType === "USER_LOGIN" || actionType.startsWith("CREATE_") || actionType === "REFERRAL_MARKED") return "success";
    if (actionType === "USER_LOGOUT" || actionType.includes("DELETE")) return "danger";
    if (actionType.includes("COMMENT")) return "warning";
    if (actionType.includes("UPDATE") || actionType.includes("STATUS")) return "info";
    return "neutral";
  }

  function historianIcon(actionType = "") {
    if (actionType === "USER_LOGIN") return LogIn;
    if (actionType === "USER_LOGOUT") return LogOut;
    if (actionType.includes("COMMENT")) return MessageCircleMore;
    if (actionType.includes("UPDATE") || actionType.includes("STATUS")) return Pencil;
    return FileClock;
  }

  function summarizeHistorianChange(row) {
    const next = parseJsonMaybe(row.new_value);
    const prev = parseJsonMaybe(row.old_value);
    if (row.action_type === "ADD_COMMENT" && next?.content) return next.content;
    if (next && prev) {
      const changedKey = Object.keys(next).find((key) => JSON.stringify(next[key]) !== JSON.stringify(prev[key]));
      if (changedKey) {
        const before = prev[changedKey] ?? "None";
        const after = next[changedKey] ?? "None";
        return `${changedKey}: (${before}) -> (${after})`;
      }
    }
    return row.description || row.entity_name || "";
  }

  function historianHeadline(row) {
    const action = row.action_type || "";
    const actor = row.username || "Unknown";
    if (action === "USER_LOGIN") return `User Login by: ${actor}`;
    if (action === "USER_LOGOUT") return `User Logout by: ${actor}`;
    if (action.includes("UPDATE")) return `${row.entity_type || "Record"} Updated by: ${actor}`;
    if (action.includes("CREATE")) return `${row.entity_type || "Record"} Created by: ${actor}`;
    if (action.includes("COMMENT")) return `Comment Added by: ${actor}`;
    if (action.includes("DELETE")) return `${row.entity_type || "Record"} Deleted by: ${actor}`;
    return `${(row.entity_type || "Activity")} Updated by: ${actor}`;
  }

  const avatar = user.profile_pic ? <img src={user.profile_pic} alt={user.username} /> : <span>{user.username.slice(0, 1).toUpperCase()}</span>;

  return (
    <div className={`app-shell ${sidebarOpen ? "" : "sidebar-closed"}`}>
      <aside className="sidebar">
        <div className="sidebar-head">
          <img className="sidebar-logo sidebar-logo-full" src={sidebarLogo} alt="SafeLife" />
          <img className="sidebar-logo sidebar-logo-mark" src={logoMark} alt="SafeLife" />
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen((open) => !open)}
            aria-label={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
            title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            {sidebarOpen ? <PanelLeftClose size={21} /> : <PanelLeftOpen size={21} />}
          </button>
        </div>
        <h2>Navigation</h2>
        <nav>
          {nav.map(([to, Icon, label]) => (
            <NavLink key={to} to={to} title={label}>
              <Icon size={18} />
              <span className="sidebar-label">{label}</span>
            </NavLink>
          ))}
          {isAdminRole(user.role) && (
            <NavLink to="/users" title="System Management">
              <UserCog size={18} />
              <span className="sidebar-label">System Management</span>
            </NavLink>
          )}
        </nav>
        <section className="historian-panel">
          <div className="historian-card">
            <div className="historian-card-head">
              <div>
                <h3>Historian</h3>
              </div>
              <button className="historian-link" onClick={() => navigate("/activity")}>
                <Activity size={15} />
                Open
              </button>
            </div>
            <div className="historian-timeline">
              {historianRows.length ? historianRows.map((row) => {
                const Icon = historianIcon(row.action_type);
                const tone = historianTone(row.action_type);
                const userMeta = userDirectory[row.username] || {};
                return (
                  <article className={`historian-entry historian-${tone}`} key={row.id} onClick={() => navigate("/activity")}>
                    <div className="historian-rail">
                      <span className="historian-icon"><Icon size={15} /></span>
                      <span className="historian-line" />
                    </div>
                    <div className="historian-copy">
                      <h4>{historianHeadline(row)}</h4>
                      <div className="historian-meta">
                        {userMeta.email ? <strong>{userMeta.email}</strong> : null}
                        <span>{exactTime(row.timestamp)}</span>
                      </div>
                      <span className="historian-pill">{relativeTime(row.timestamp)}</span>
                      {summarizeHistorianChange(row) ? <p>{summarizeHistorianChange(row)}</p> : null}
                    </div>
                  </article>
                );
              }) : (
                <div className="historian-empty">No recent activity yet.</div>
              )}
            </div>
          </div>
        </section>
        <div className="api-ok">API Healthy</div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="topbar-left">
            <div>
              <div className="breadcrumb">HOME / {title.toUpperCase()}</div>
              <h1>{title}</h1>
            </div>
          </div>
          {showTopbarSmartSearch && (
            <div className="topbar-center">
              <SmartSearch className="smart-top-search" />
            </div>
          )}
          <div className="topbar-actions">
            <div className="notification-menu">
              <button className="icon-button bell-button" onClick={() => setNotificationOpen((open) => !open)} aria-label="Notifications">
                <Bell size={30} />
                {notificationTotal > 0 && <span className="notification-dot">{notificationTotal}</span>}
              </button>
              {notificationOpen && <div className="notification-dropdown">
                <div className="notification-head">
                  <h3>Notifications</h3>
                  <div className="notification-head-actions">
                    <button
                      className={`notification-sound-toggle ${soundEnabled ? "enabled" : ""}`}
                      onClick={toggleNotificationSound}
                      aria-label={soundEnabled ? "Turn notification sound off" : "Turn notification sound on"}
                      title={soundEnabled ? "Notification sound on" : "Notification sound off"}
                    >
                      {soundEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
                      <span>{soundEnabled ? "Sound On" : "Sound Off"}</span>
                    </button>
                    <button className="notification-close" onClick={() => setNotificationOpen(false)} aria-label="Close notifications"><X size={26} /></button>
                  </div>
                </div>
                <div className="notification-list">
                  {notifications.length ? notifications.map((item) => <article className={`notification-card ${item.read ? "read" : ""}`} key={item.id}>
                    <button className="notification-main" onClick={() => goNotification(item)}>
                      <span className="notification-icon"><img src={logoMark} alt="SafeLife" /></span>
                      <span className="notification-copy">
                        <span className="notification-title-row">
                          <b>{item.title}</b>
                          {notificationTime(item) && <em>{notificationTime(item)}</em>}
                        </span>
                        <span className="notification-message">{item.message || item.type}</span>
                        {item.due && <small>{exactTime(item.due)}</small>}
                      </span>
                    </button>
                    <button className="notification-check" onClick={() => markOneRead(item.id)} disabled={item.read} aria-label={item.read ? "Notification already read" : "Mark notification read"}><Check size={28} /></button>
                  </article>) : <div className="empty-notifications">No notifications</div>}
                </div>
                <div className="notification-footer">
                  <span>You have {notificationTotal} notifications</span>
                  <button onClick={markAllRead} disabled={!notificationTotal}>Mark All As Read</button>
                </div>
              </div>}
            </div>
            <div className="user-menu">
              <button className="profile-button" onClick={() => setMenuOpen(!menuOpen)} aria-label="User menu">
                <span className="top-avatar">{avatar}</span>
                <span className="profile-copy">
                  <strong>{user.username.toUpperCase()}</strong>
                  <small>ID Number = {user.user_id || user.employee_id || `ADMIN${String(user.id).padStart(3, "0")}`}</small>
                </span>
                <ChevronDown size={22} />
              </button>
            {menuOpen && <div className="dropdown">
              <div className="dropdown-user"><b>{user.username}</b><span>{user.role}</span></div>
              <button onClick={() => { setMenuOpen(false); navigate("/settings"); }}><Settings size={16} />User Settings</button>
              <button onClick={logout}><LogOut size={16} />Logout</button>
            </div>}
            </div>
          </div>
        </header>
        <section className="content">{children}</section>
      </main>
    </div>
  );
}
