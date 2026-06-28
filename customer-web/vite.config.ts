import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Per-box routing (PRD-12 / SCRUM-77): the customer SPA is served at the host
  // root by per-clone nginx. Overridable at build time via VITE_BASE for a future
  // path-prefixed host; defaults to "/".
  base: process.env.VITE_BASE ?? "/",
  server: {
    port: 3500,
    proxy: {
      "/api": "http://localhost:8001",
    },
  },
});
