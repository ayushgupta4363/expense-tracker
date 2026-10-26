const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// One helper for all backend calls. It adds the login token automatically.
export async function api(path, options = {}) {
  const token = localStorage.getItem("token");

  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = "Bearer " + token;
  }

  const res = await fetch(API_URL + path, { ...options, headers });

  // token expired or invalid -> log the user out
  if (res.status === 401 && token) {
    localStorage.removeItem("token");
    window.location.reload();
    return;
  }

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    // FastAPI sends "detail" as text, or as a list for validation errors
    const message = typeof data.detail === "string" ? data.detail : "Please check your input";
    throw new Error(message);
  }
  return data;
}
