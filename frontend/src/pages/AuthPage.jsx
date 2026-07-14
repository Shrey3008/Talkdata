import { useState } from "react";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function AuthPage() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await signup(email, password, fullName);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="card auth-card" onSubmit={onSubmit}>
        <span className="brand">
          <span className="brand-mark">T</span>
          TalkData
        </span>
        <div>
          <h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1>
          <p className="sub">Ask your data questions in plain English.</p>
        </div>
        {mode === "signup" && (
          <input
            placeholder="Full name (optional)"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            autoComplete="name"
          />
        )}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />
        <input
          type="password"
          placeholder={mode === "signup" ? "Password (min 8 characters)" : "Password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={mode === "signup" ? 8 : undefined}
          autoComplete={mode === "login" ? "current-password" : "new-password"}
        />
        {error && <span className="error-text">{error}</span>}
        <button disabled={busy}>
          {busy ? <span className="spinner" /> : mode === "login" ? "Log in" : "Sign up"}
        </button>
        <span className="auth-toggle">
          {mode === "login" ? (
            <>No account? <a onClick={() => { setMode("signup"); setError(""); }}>Sign up</a></>
          ) : (
            <>Already registered? <a onClick={() => { setMode("login"); setError(""); }}>Log in</a></>
          )}
        </span>
      </form>
    </div>
  );
}
