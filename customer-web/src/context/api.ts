const apiBase = import.meta.env.VITE_API_BASE ?? "";
export function api(path: string) { return `${apiBase}${path}`; }
