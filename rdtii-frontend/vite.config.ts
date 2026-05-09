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
  },
});
