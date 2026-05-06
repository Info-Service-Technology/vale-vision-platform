import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

const proxyTarget = process.env.VITE_DEV_PROXY_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html")
      },
    },
  },
  server: {
    host: true,
    port: 5174,
    strictPort: true,
    proxy: {
      "/api": {
        target: proxyTarget,
        changeOrigin: true,
      },
      "/static": {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
});
