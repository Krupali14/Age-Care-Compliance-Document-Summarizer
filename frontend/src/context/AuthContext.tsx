import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";
import * as authApi from "../api/auth";

interface AuthContextValue {
  token: string | null;
  email: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: (reason?: string) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/** Claims of a JWT, or null if the payload can't be read. */
function claimsOf(token: string): { exp?: number; email?: string } | null {
  try {
    return JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return null;
  }
}

/** Expiry claim of a JWT, in ms, or null if it can't be read. */
function expiryOf(token: string): number | null {
  const exp = claimsOf(token)?.exp;
  return typeof exp === "number" ? exp * 1000 : null;
}

/** Why the last session ended, read once by the login screen.
 *  Being returned to a sign-in form with no explanation reads as lost work. */
export const SESSION_ENDED_KEY = "session-ended";

export const SESSION_EXPIRED_MESSAGE =
  "Your session expired. Sign in again to pick up where you left off.";

/** The stored token, unless it has already expired — a dead token would otherwise
 *  keep the user on a session where every request fails.
 *
 *  This is a separate path from logout(): a token that died while the tab was
 *  closed is noticed here, at boot, and it has to leave the same explanation
 *  behind or the user is returned to a sign-in form with no reason given. */
function storedToken(): string | null {
  const token = localStorage.getItem("token");
  if (!token) return null;
  const expiry = expiryOf(token);
  if (expiry !== null && expiry <= Date.now()) {
    localStorage.removeItem("token");
    sessionStorage.setItem(SESSION_ENDED_KEY, SESSION_EXPIRED_MESSAGE);
    return null;
  }
  return token;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(storedToken);

  const logout = useCallback((reason?: string) => {
    localStorage.removeItem("token");
    if (reason) sessionStorage.setItem(SESSION_ENDED_KEY, reason);
    setToken(null);
  }, []);

  const expire = useCallback(() => {
    logout(SESSION_EXPIRED_MESSAGE);
  }, [logout]);

  async function login(email: string, password: string) {
    const t = await authApi.login(email, password);
    sessionStorage.removeItem(SESSION_ENDED_KEY);
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
    const timer = setTimeout(expire, Math.max(0, delay));
    return () => clearTimeout(timer);
  }, [token, expire]);

  // A request rejected as unauthorised means the token died early (server restart,
  // rotated secret). Treat it the same as expiry instead of failing silently.
  useEffect(() => {
    window.addEventListener("auth:expired", expire);
    return () => window.removeEventListener("auth:expired", expire);
  }, [expire]);

  // Logging out in one tab logs out the others.
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === "token") setToken(storedToken());
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return (
    <AuthContext.Provider value={{ token, email: token ? claimsOf(token)?.email ?? null : null, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
