const BASE = "/api";

async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    credentials: "include",
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: "Request failed" } }));
    throw new Error(err.error?.message || `HTTP ${res.status}`);
  }
  return res.json();
}

export interface UserResponse {
  id: string;
  phone?: string;
  name?: string;
  email?: string;
  role: string;
}

export interface TokenResponse {
  user: UserResponse;
}

export interface DashboardResponse {
  data: {
    total_customers: number;
    active_campaigns: number;
    total_signups: number;
    total_rewards: number;
    issued_rewards: number;
    redeemed_rewards: number;
  };
}

// Auth
export function adminLogin(email: string, password: string) {
  return request<TokenResponse>("POST", "/admin/auth/login", { email, password });
}

// Dashboard
export function getDashboard() {
  return request<DashboardResponse>("GET", "/admin/dashboard");
}
