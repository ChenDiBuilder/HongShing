import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/product-demo/hongshing-storefront/",
  server: {
    port: 3502,
    proxy: {
      "/api": "http://localhost:8001",
    },
  },
});
