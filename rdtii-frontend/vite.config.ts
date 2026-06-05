import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  define: {
    __BUNDLED_DEV__: JSON.stringify(process.env.NODE_ENV !== "production"),
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      "/api": {
        target: process.env.VITE_BACKEND_URL ?? "http://localhost:8000",
        changeOrigin: true,
        proxyTimeout: 300_000,
        timeout: 300_000,
      },
      "/auth": {
        target: process.env.VITE_BACKEND_URL ?? "http://localhost:8000",
        changeOrigin: true,
        proxyTimeout: 30_000,
        timeout: 30_000,
      },
      "/health": {
        target: process.env.VITE_BACKEND_URL ?? "http://localhost:8000",
        changeOrigin: true,
        proxyTimeout: 10_000,
        timeout: 10_000,
      },
    },
  },
});
