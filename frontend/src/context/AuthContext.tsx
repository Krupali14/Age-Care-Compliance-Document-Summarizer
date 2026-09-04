import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";
import * as authApi from "../api/auth";

interface AuthContextValue {
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/** Expiry claim of a JWT, in ms, or null if it can't be read. */
function expiryOf(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.exp === "number" ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

/** The stored token, unless it has already expired — a dead token would otherwise
 *  keep the user on a session where every request fails. */
function storedToken(): string | null {
  const token = localStorage.getItem("token");
  if (!token) return null;
  const expiry = expiryOf(token);
  if (expiry !== null && expiry <= Date.now()) {
    localStorage.removeItem("token");
    return null;
  }
  return token;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(storedToken);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setToken(null);
  }, []);

  async function login(email: string, password: string) {
    const t = await authApi.login(email, password);
    localStorage.setItem("token", t);
    setToken(t);
  }

  async function register(email: string, password: string) {
    await authApi.register(email, password);
    await login(email, password);
  }

  // The session lasts exactly as long as the token does: it survives reloads and
  // new tabs, and ends on its own the moment the token expires rather than leaving
  // the user on a dashboard whose every request is rejected.
  useEffect(() => {
    if (!token) return;
    const expiry = expiryOf(token);
    if (expiry === null) return;
    const delay = expiry - Date.now();
    // setTimeout stores its delay in a 32-bit int, so anything longer overflows and
    // fires immediately — which would log the user straight back out on a long
    // session. Those are caught by the expiry check on the next load instead.
    if (delay > 2 ** 31 - 1) return;
    const timer = setTimeout(logout, Math.max(0, delay));
    return () => clearTimeout(timer);
  }, [token, logout]);

  // A request rejected as unauthorised means the token died early (server restart,
  // rotated secret). Treat it the same as expiry instead of failing silently.
  useEffect(() => {
    window.addEventListener("auth:expired", logout);
    return () => window.removeEventListener("auth:expired", logout);
  }, [logout]);

  // Logging out in one tab logs out the others.
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === "token") setToken(storedToken());
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return (
    <AuthContext.Provider value={{ token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
