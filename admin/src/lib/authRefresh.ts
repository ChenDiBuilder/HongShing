// Silent session refresh (SCRUM-235).
//
// The backend issues a rotating, DB-backed 12h refresh token
// (admin_refresh_token, path=/api/admin/auth) but the SPA never used it, so
// the effective session was just the access-token lifetime. This installs a
// global fetch interceptor: the first 401 from an admin API call triggers one
// POST /api/admin/auth/refresh, then retries the original request once.
//
// Loop guards: auth endpoints themselves are never intercepted, the retry is
// never re-intercepted (a second 401 falls through to onSessionExpired), and
// concurrent 401s share a single in-flight refresh.

const apiBase = import.meta.env.VITE_API_BASE ?? "";

let refreshing: Promise<boolean> | null = null;
// After a failed refresh, don't re-hit the endpoint for a beat: a screen that
// fires several fetches (or StrictMode double-mounts) would otherwise burst
// N attempts against a dead refresh token before the login redirect settles.
let failedCooldownUntil = 0;

function refreshOnce(originalFetch: typeof fetch): Promise<boolean> {
  if (Date.now() < failedCooldownUntil) return Promise.resolve(false);
  if (!refreshing) {
    refreshing = originalFetch(`${apiBase}/api/admin/auth/refresh`, {
      method: "POST",
      credentials: "include",
    })
      .then((r) => {
        if (!r.ok) failedCooldownUntil = Date.now() + 10_000;
        return r.ok;
      })
      .catch(() => {
        failedCooldownUntil = Date.now() + 10_000;
        return false;
      })
      .finally(() => {
        refreshing = null;
      }) as Promise<boolean>;
  }
  return refreshing;
}

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.href;
  return input.url;
}

export function installAuthRefresh(onSessionExpired: () => void) {
  // StrictMode double-mounts effects in dev; never wrap twice.
  if ((window.fetch as { __authRefresh?: boolean }).__authRefresh) return;

  const originalFetch = window.fetch.bind(window);
  const wrapped: typeof fetch = async (input, init) => {
    const res = await originalFetch(input, init);
    const url = requestUrl(input);
    const isAdminApi = url.includes("/api/admin/");
    const isAuthEndpoint = url.includes("/api/admin/auth/");
    if (res.status !== 401 || !isAdminApi || isAuthEndpoint) return res;

    if (await refreshOnce(originalFetch)) {
      const retried = await originalFetch(input, init);
      if (retried.status !== 401) return retried;
    }
    onSessionExpired();
    return res;
  };
  (wrapped as unknown as { __authRefresh: boolean }).__authRefresh = true;
  window.fetch = wrapped;
}
