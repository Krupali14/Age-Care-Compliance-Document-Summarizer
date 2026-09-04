const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8002";

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
    const body = await response.text();
    throw new Error(`${response.status}: ${body}`);
  }
  return response;
}
