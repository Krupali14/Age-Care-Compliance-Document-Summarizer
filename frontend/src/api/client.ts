const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8002";

/**
 * The readable part of a failed response. The API explains refusals precisely
 * ("Password must be at most 72 bytes", "File is larger than the 25MB limit");
 * throwing the raw status and JSON body instead meant callers fell back to a
 * generic message and the explanation was lost.
 */
async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    // FastAPI validation errors arrive as [{ loc, msg, type }, ...].
    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((d: { msg?: string }) => (d.msg ?? "").replace(/^Value error,\s*/, ""))
        .filter(Boolean)
        .join(". ");
    }
  } catch {
    // Not JSON — fall through to the status-based wording below.
  }
  if (response.status === 401) return "Incorrect email or password.";
  if (response.status >= 500) return "The server is unavailable right now. Try again shortly.";
  return `Request failed (${response.status}).`;
}

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem("token");
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    // A rejected token on an authenticated request means the session is over. Tell
    // the app so it can return to the login screen, rather than leaving the user
    // clicking around a dashboard where every request fails. Sign-in failures are
    // not session expiry — those belong to the login form.
    if (response.status === 401 && !path.startsWith("/api/auth/")) {
      localStorage.removeItem("token");
      window.dispatchEvent(new Event("auth:expired"));
    }
    throw new Error(await errorMessage(response));
  }
  return response;
}
