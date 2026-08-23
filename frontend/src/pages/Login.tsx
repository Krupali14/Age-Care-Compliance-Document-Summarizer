import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password);
      navigate("/dashboard");
    } catch {
      setError("Authentication failed. Check your credentials.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-parchment px-6">
      <div className="w-full max-w-sm animate-fade-up">
        <Link to="/" className="flex items-center gap-2 font-display text-lg font-semibold text-ink">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-ink text-xs font-mono text-parchment">§</span>
          Compliance Summariser
        </Link>

        <div className="mt-8 rounded-xl border border-ink/10 bg-white p-8 shadow-card">
          <h1 className="font-display text-2xl font-semibold">
            {mode === "login" ? "Sign in" : "Create an account"}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {mode === "login" ? "Welcome back — your documents are waiting." : "Takes a minute. No credit card, no confirmation email."}
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label htmlFor="email" className="block text-xs font-medium uppercase tracking-wide text-slate-400">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                placeholder="you@facility.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1.5 w-full rounded-md border border-ink/15 px-3 py-2.5 text-sm text-ink transition placeholder:text-slate-400 focus:border-teal"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-xs font-medium uppercase tracking-wide text-slate-400">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1.5 w-full rounded-md border border-ink/15 px-3 py-2.5 text-sm text-ink transition placeholder:text-slate-400 focus:border-teal"
              />
            </div>

            {error && (
              <p className="rounded-md bg-coral-50 px-3 py-2 text-sm text-coral">{error}</p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-md bg-ink px-4 py-2.5 text-sm font-semibold text-parchment transition hover:-translate-y-0.5 hover:shadow-card disabled:translate-y-0 disabled:opacity-60"
            >
              {submitting ? "Please wait…" : mode === "login" ? "Sign in" : "Register"}
            </button>
          </form>
        </div>

        <button
          onClick={() => setMode(mode === "login" ? "register" : "login")}
          className="mt-5 w-full text-center text-sm font-medium text-teal hover:text-teal-600"
        >
          {mode === "login" ? "Need an account? Register" : "Already have an account? Sign in"}
        </button>
      </div>
    </div>
  );
}
