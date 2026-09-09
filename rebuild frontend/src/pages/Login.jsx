import { useState } from "react";
import { CirclePlus, Eye, EyeOff, Lock, ShieldCheck, UserPlus, UserRound, UsersRound, Headset } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Button, Field } from "../components/Controls";
import { api } from "../services/api";
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

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (mode === "signup") {
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
    if (mode === "forgot") {
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

  return (
    <div className="auth-page">
      <div className="auth-ornament auth-ornament-plus plus-top-left"><CirclePlus size={28} /></div>
      <div className="auth-ornament auth-ornament-plus plus-bottom-right"><CirclePlus size={28} /></div>
      <div className="auth-ornament auth-dots auth-dots-left" aria-hidden="true" />
      <div className="auth-ornament auth-dots auth-dots-right" aria-hidden="true" />
      <div className="auth-wave" aria-hidden="true" />
      <div className="auth-shell">
        <div className="auth-brand">
          <img src={sidebarLogo} alt="SafeLife" />
          <div className="auth-divider">
            <span />
            <div className="auth-divider-badge"><ShieldCheck size={20} /></div>
            <span />
          </div>
          <h1>Lead Manager</h1>
          <p className="auth-subtitle">
            {mode === "login" && "Sign in to access the Lead Manager dashboard"}
            {mode === "signup" && "Create your account to access Lead Manager"}
            {mode === "forgot" && "Request a Lead Manager password reset"}
          </p>
        </div>

        <form className="auth-card auth-card-rich" onSubmit={submit}>
          {mode === "signup" && (
            <Field label="User ID" required>
              <div className="input-shell">
                <span className="input-icon"><UserPlus size={22} /></span>
                <input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="Enter your employee ID" />
              </div>
            </Field>
          )}

          <Field label="Username" required>
            <div className="input-shell">
              <span className="input-icon"><UserRound size={22} /></span>
              <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Enter your username" />
            </div>
          </Field>

          {mode === "signup" && (
            <Field label="Email" required>
              <div className="input-shell">
                <span className="input-icon"><UsersRound size={22} /></span>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Enter your email address" />
              </div>
            </Field>
          )}

          {mode !== "forgot" && (
            <Field label="Password" required>
              <div className="input-shell">
                <span className="input-icon"><Lock size={22} /></span>
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                />
                <button className="input-toggle" type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"}>
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </Field>
          )}

          {mode === "signup" && (
            <Field label="Confirm Password" required>
              <div className="input-shell">
                <span className="input-icon"><Lock size={22} /></span>
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm your password"
                />
                <button className="input-toggle" type="button" onClick={() => setShowConfirmPassword((value) => !value)} aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}>
                  {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </Field>
          )}

          {error && <div className="error">{error}</div>}

          <Button variant="primary" type="submit">
            <Lock size={19} />
            {mode === "login" ? "Login" : mode === "signup" ? "Sign Up" : "Request Reset"}
          </Button>
        </form>

        <div className="auth-links auth-links-rich">
          <Button variant="primary" onClick={() => setMode(mode === "signup" ? "login" : "signup")}>
            <UserPlus size={19} />
            {mode === "signup" ? "Back to Login" : "Sign Up"}
          </Button>
          <Button onClick={() => setMode(mode === "forgot" ? "login" : "forgot")}>
            <Lock size={19} />
            {mode === "forgot" ? "Back to Login" : "Forgot Password?"}
          </Button>
        </div>

        <div className="auth-footer-panels">
          <article>
            <span><ShieldCheck size={26} /></span>
            <div>
              <b>Secure & Protected</b>
              <small>Your data is safe with enterprise-grade security</small>
            </div>
          </article>
          <article>
            <span><UsersRound size={26} /></span>
            <div>
              <b>All in One Place</b>
              <small>Manage and track all your leads efficiently</small>
            </div>
          </article>
          <article>
            <span><Headset size={26} /></span>
            <div>
              <b>Always Here</b>
              <small>Support when you need it, where you need it</small>
            </div>
          </article>
        </div>

        <p className="auth-copyright">© 2024 SafeLife. All rights reserved.</p>
      </div>
    </div>
  );
}
