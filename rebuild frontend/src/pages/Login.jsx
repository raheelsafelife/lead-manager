import { useState } from "react";
import {
  ArrowLeft,
  BarChart3,
  Check,
  ClipboardCheck,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldCheck,
  UserPlus,
  UserRound,
  UsersRound
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import sidebarLogo from "../../sidebar_logo.png";
import safeLifeMark from "../../favicon.svg";
import heroImage from "../assets/safelife-home-care-hero-centered.jpg";

const features = [
  { icon: UsersRound, label: "Patient & Caregiver Management" },
  { icon: ClipboardCheck, label: "Referral & Authorization Tracking" },
  { icon: ShieldCheck, label: "Secure Platform" },
  { icon: BarChart3, label: "Real-Time Analytics" }
];

const modeCopy = {
  login: {
    eyebrow: "Secure portal",
    title: "Welcome Back",
    subtitle: "Sign in to access your SafeLife dashboard",
    submit: "Sign In"
  },
  forgot: {
    eyebrow: "Account recovery",
    title: "Reset Password",
    subtitle: "Enter your username and an administrator will help you reset your password.",
    submit: "Request Reset"
  },
  signup: {
    eyebrow: "Join SafeLife",
    title: "Create Account",
    subtitle: "Set up your account to access the SafeLife dashboard.",
    submit: "Create Account"
  }
};

export default function Login() {
  const { login } = useAuth();
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [userId, setUserId] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const copy = modeCopy[mode];

  function changeMode(nextMode) {
    setFeedback(null);
    setMode(nextMode);
  }

  async function submit(e) {
    e.preventDefault();
    setFeedback(null);
    if (mode === "signup") {
      if (password !== confirmPassword) {
        setFeedback({ type: "error", text: "Passwords do not match." });
        return;
      }
      try {
        await api.post("/auth/signup", { user_id: userId, username, email, password });
        setFeedback({ type: "success", text: "Account created. An administrator will review your access request." });
        setMode("login");
      } catch (err) {
        setFeedback({ type: "error", text: err.response?.data?.error || "Could not create account." });
      }
      return;
    }
    if (mode === "forgot") {
      try {
        await api.post("/auth/forgot", { username });
        setFeedback({ type: "success", text: "Reset request sent. An administrator will review your request." });
        setMode("login");
      } catch (err) {
        setFeedback({ type: "error", text: err.response?.data?.error || "Username not found." });
      }
      return;
    }
    try {
      await login(username.trim(), password.trim());
    } catch (err) {
      setFeedback({ type: "error", text: err.response?.data?.error || "Login failed." });
    }
  }

  return (
    <main className="auth-page" style={{ "--auth-hero": `url(${heroImage})` }}>
      <section className="auth-story">
        <div className="auth-story-glow" aria-hidden="true" />
        <div className="auth-story-inner">
          <img className="auth-wordmark" src={sidebarLogo} alt="SafeLife Home Health, Home Care, Hospice" />

          <div className="auth-story-copy">
            <p className="auth-story-kicker">Care operations, thoughtfully connected</p>
            <h1>Empowering Better Care.<span>Every Day.</span></h1>
            <p className="auth-story-lede">
              SafeLife helps Home Health, Home Care, and Hospice organizations streamline referrals,
              authorizations, caregiver management, compliance, and patient care.
            </p>

            <div className="auth-feature-list">
              {features.map(({ icon: Icon, label }) => (
                <div className="auth-feature" key={label}>
                  <span><Icon size={18} /></span>
                  <b>{label}</b>
                  <Check className="auth-feature-check" size={16} />
                </div>
              ))}
            </div>
          </div>

          <div className="auth-trust">
            <span><LockKeyhole size={19} /></span>
            <div>
              <b>Secure</b>
              <p>Your data is protected with enterprise-grade security.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-panel-shape auth-panel-shape-one" aria-hidden="true" />
        <div className="auth-panel-shape auth-panel-shape-two" aria-hidden="true" />
        <form className={`auth-card auth-card-${mode}`} onSubmit={submit}>
          {mode !== "login" && (
            <button className="auth-back" type="button" onClick={() => changeMode("login")}>
              <ArrowLeft size={17} /> Back to sign in
            </button>
          )}

          <div className="auth-card-head">
            <span className="auth-mark-wrap"><img src={safeLifeMark} alt="" /></span>
            <small>{copy.eyebrow}</small>
            <h2>{copy.title}</h2>
            <p>{copy.subtitle}</p>
          </div>

          <div className="auth-fields">
            {mode === "signup" && (
              <label className="auth-field">
                <span>Employee ID</span>
                <div className="auth-input"><UserPlus size={19} /><input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="Enter your employee ID" required /></div>
              </label>
            )}

            <label className="auth-field">
              <span>{mode === "login" ? "Username or Email" : "Username"}</span>
              <div className="auth-input"><UserRound size={19} /><input value={username} onChange={(e) => setUsername(e.target.value)} placeholder={mode === "login" ? "Enter your username or email" : "Enter your username"} required /></div>
            </label>

            {mode === "signup" && (
              <label className="auth-field">
                <span>Email Address</span>
                <div className="auth-input"><Mail size={19} /><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Enter your email address" required /></div>
              </label>
            )}

            {mode !== "forgot" && (
              <label className="auth-field">
                <span className="auth-field-row">
                  <span>Password</span>
                  {mode === "login" && <button type="button" onClick={() => changeMode("forgot")}>Forgot password?</button>}
                </span>
                <div className="auth-input">
                  <LockKeyhole size={19} />
                  <input type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" required />
                  <button className="auth-input-toggle" type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"}>
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </label>
            )}

            {mode === "signup" && (
              <label className="auth-field">
                <span>Confirm Password</span>
                <div className="auth-input">
                  <LockKeyhole size={19} />
                  <input type={showConfirmPassword ? "text" : "password"} value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Confirm your password" required />
                  <button className="auth-input-toggle" type="button" onClick={() => setShowConfirmPassword((value) => !value)} aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}>
                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </label>
            )}
          </div>

          {mode === "login" && (
            <label className="auth-remember">
              <input type="checkbox" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} />
              <span>Remember me</span>
            </label>
          )}

          {feedback && <div className={`auth-feedback ${feedback.type}`}>{feedback.text}</div>}

          <button className="auth-submit" type="submit">
            <LockKeyhole size={18} /> {copy.submit}
          </button>

          {mode === "login" && (
            <p className="auth-switch">New to SafeLife? <button type="button" onClick={() => changeMode("signup")}>Create an account</button></p>
          )}
          {mode === "signup" && (
            <p className="auth-switch">Already have an account? <button type="button" onClick={() => changeMode("login")}>Sign in</button></p>
          )}
        </form>
        <p className="auth-panel-footer"><ShieldCheck size={15} /> SafeLife secure access portal</p>
      </section>
    </main>
  );
}
