import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/product-demo/hongshing-admin/",
  server: {
    port: 3501,
    proxy: {
      "/api": "http://localhost:8001",
    },
  },
});
