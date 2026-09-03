import { useState } from "react";
import { BarChart3, Check, Eye, EyeOff, Lock, Mail, ShieldCheck, UserPlus, UserRound, UsersRound } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import logoMark from "../../favicon.svg";
import sidebarLogo from "../../sidebar_logo.png";

export default function Login() {
  const { login } = useAuth();
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [userId, setUserId] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const isLogin = mode === "login";
  const isSignup = mode === "signup";
  const isForgot = mode === "forgot";

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (isSignup) {
      if (password !== confirmPassword) { setError("Passwords do not match"); return; }
      try {
        await api.post("/auth/signup", { user_id: userId, username, email, password });
        setError("Account created successfully. Your account is now pending admin approval.");
        setMode("login");
      } catch (err) {
        setError(err.response?.data?.error || "Could not create account");
      }
      return;
    }
    if (isForgot) {
      try {
        await api.post("/auth/forgot", { username });
        setError("Password reset requested. An admin will review and reset your password.");
        setMode("login");
      } catch (err) {
        setError(err.response?.data?.error || "Username not found");
      }
      return;
    }
    try { await login(username.trim(), password.trim()); }
    catch (err) { setError(err.response?.data?.error || "Login failed"); }
  }

  const heading = isLogin ? "Welcome Back" : isSignup ? "Create Account" : "Reset Password";
  const subheading = isLogin
    ? "Sign in to access your SafeLife dashboard"
    : isSignup
      ? "Create your account for SafeLife secure access"
      : "Enter your username to request password help";

  return (
    <main className="auth-page">
      <section className="auth-marketing" aria-label="SafeLife overview">
        <div className="auth-marketing-inner">
          <img className="auth-brand-logo" src={sidebarLogo} alt="SafeLife" />
          <div className="auth-kicker">Care operations, thoughtfully connected</div>
          <h1>Empowering<br />Better Care.<br /><span>Every Day.</span></h1>
          <p>
            SafeLife helps Home Health, Home Care, and Hospice organizations streamline referrals,
            authorizations, caregiver management, compliance, and patient care.
          </p>
          <div className="auth-feature-grid">
            {[
              ["Patient & Caregiver Management", UsersRound],
              ["Referral & Authorization Tracking", UserPlus],
              ["Secure Platform", ShieldCheck],
              ["Real-Time Analytics", BarChart3]
            ].map(([label, Icon]) => (
              <div className="auth-feature-pill" key={label}>
                <span><Icon size={20} /></span>
                <b>{label}</b>
                <Check size={16} />
              </div>
            ))}
          </div>
          <div className="auth-trust-card">
            <span><Lock size={22} /></span>
            <div>
              <b>Secure</b>
              <small>Your data is protected with enterprise-grade security.</small>
            </div>
          </div>
        </div>
      </section>

      <section className="auth-panel" aria-label="SafeLife sign in">
        <div className="auth-orb auth-orb-top" />
        <div className="auth-orb auth-orb-bottom" />
        <form className="auth-card auth-card-rich" onSubmit={submit}>
          <div className="auth-card-head">
            <span className="auth-logo-mark"><img src={logoMark} alt="SafeLife" /></span>
            <small>Secure Portal</small>
            <strong className="auth-product-title">Lead Manager</strong>
            <h2>{heading}</h2>
            <p>{subheading}</p>
          </div>

          {isSignup && (
            <label className="auth-field">
              <span>User ID</span>
              <div className="input-shell">
                <UserPlus size={20} />
                <input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="Enter your employee ID" />
              </div>
            </label>
          )}

          <label className="auth-field">
            <span>{isForgot ? "Username" : "Username or Email"}</span>
            <div className="input-shell">
              <UserRound size={20} />
              <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder={isForgot ? "Enter your username" : "Enter your username or email"} />
            </div>
          </label>

          {isSignup && (
            <label className="auth-field">
              <span>Email</span>
              <div className="input-shell">
                <Mail size={20} />
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Enter your email address" />
              </div>
            </label>
          )}

          {!isForgot && (
            <label className="auth-field">
              <span className="auth-field-row">
                Password
                {isLogin && <button type="button" onClick={() => setMode("forgot")}>Forgot password?</button>}
              </span>
              <div className="input-shell">
                <Lock size={20} />
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                />
                <button className="input-toggle" type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"}>
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </label>
          )}

          {isSignup && (
            <label className="auth-field">
              <span>Confirm Password</span>
              <div className="input-shell">
                <Lock size={20} />
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm your password"
                />
                <button className="input-toggle" type="button" onClick={() => setShowConfirmPassword((value) => !value)} aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}>
                  {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </label>
          )}

          {isLogin && (
            <label className="auth-remember">
              <input type="checkbox" />
              <span>Remember me</span>
            </label>
          )}

          {error && <div className="error">{error}</div>}

          <button className="auth-submit" type="submit">
            <Lock size={18} />
            {isLogin ? "Sign In" : isSignup ? "Create Account" : "Request Reset"}
          </button>

          <div className="auth-switch">
            {isSignup || isForgot ? (
              <button type="button" onClick={() => setMode("login")}>Back to login</button>
            ) : (
              <>
                <span>New to SafeLife?</span>
                <button type="button" onClick={() => setMode("signup")}>Create an account</button>
              </>
            )}
          </div>
        </form>
        <p className="auth-secure-note"><ShieldCheck size={15} /> SafeLife secure access portal</p>
      </section>
    </main>
  );
}
