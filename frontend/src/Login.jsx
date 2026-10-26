import { useState } from "react";
import { GoogleLogin } from "@react-oauth/google";
import { api } from "./api.js";

const googleEnabled = Boolean(import.meta.env.VITE_GOOGLE_CLIENT_ID);

function Login({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const path = isRegister ? "/auth/register" : "/auth/login";
      const body = isRegister ? { name, email, password } : { email, password };
      const data = await api(path, { method: "POST", body: JSON.stringify(body) });
      onLogin(data.access_token);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  }

  async function handleGoogle(response) {
    setError("");
    try {
      const data = await api("/auth/google", {
        method: "POST",
        body: JSON.stringify({ credential: response.credential }),
      });
      onLogin(data.access_token);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="login-page">
      <form className="card login-card" onSubmit={handleSubmit}>
        <h1>Expense Tracker</h1>
        <p className="muted">{isRegister ? "Create your account" : "Log in to continue"}</p>

        {isRegister && (
          <input
            placeholder="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        )}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password (min 6 characters)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={loading}>
          {loading ? "Please wait..." : isRegister ? "Register" : "Login"}
        </button>

        {googleEnabled && (
          <div className="google-box">
            <p className="muted">or</p>
            <GoogleLogin
              onSuccess={handleGoogle}
              onError={() => setError("Google login failed")}
            />
          </div>
        )}

        <p className="muted switch" onClick={() => setIsRegister(!isRegister)}>
          {isRegister ? "Already have an account? Login" : "New here? Register"}
        </p>
      </form>
    </div>
  );
}

export default Login;
