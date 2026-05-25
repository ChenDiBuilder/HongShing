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

export interface LandingConfigResponse {
  restaurant_name: string;
  primary_color: string;
  secondary_color?: string;
  logo_url?: string;
  campaign?: {
    id: string;
    source_code: string;
    landing_headline?: string;
    landing_subtitle?: string;
  };
  allow_order_without_signup: boolean;
  external_ordering_url?: string;
}

export interface UserResponse {
  id: string;
  phone?: string;
  name?: string;
  email?: string;
  role: string;
}

export interface TokenResponse {
  access_token?: string;
  token_type: string;
  user: UserResponse;
}

export interface RewardResponse {
  id: string;
  code: string;
  status: string;
  issued_at: string;
  expires_at?: string;
}

// Auth
export function sendOTP(phone: string, sourceCode?: string) {
  return request<{ ok: boolean }>("POST", "/auth/send-otp", {
    phone,
    source_code: sourceCode,
  });
}

export function verifyOTP(phone: string, code: string, sourceCode?: string) {
  return request<TokenResponse>("POST", "/auth/verify-otp", { phone, code, source_code: sourceCode });
}

// Public
export function getLandingConfig(source?: string) {
  const params = source ? `?source=${source}` : "";
  return request<LandingConfigResponse>("GET", `/public/landing-config${params}`);
}

// Rewards
export function claimReward(sourceCode?: string) {
  return request<{ reward: RewardResponse }>("POST", "/rewards/claim", {
    source_code: sourceCode,
  });
}

export function getMyRewards() {
  return request<{ rewards: RewardResponse[] }>("GET", "/rewards/me");
}
