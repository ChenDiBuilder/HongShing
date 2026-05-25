const apiBase = import.meta.env.DEV ? "" : "/product-demo/hongshing";
export function api(path: string) { return `${apiBase}${path}`; }
