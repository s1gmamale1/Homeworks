/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The SPA is served by FastAPI under /app/ in production (StaticFiles mount).
// In dev, Vite proxies API + static traffic to uvicorn on :8765 (repo convention).
export default defineConfig({
  base: "/app/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8765", changeOrigin: true },
      "/static": { target: "http://127.0.0.1:8765", changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom", "zustand"],
        },
      },
    },
  },
  // Vitest config. jsdom for DOM-aware tests (store + components), node-style
  // globals so we don't need `import { describe, it } from "vitest"` everywhere.
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    css: false,
  },
});
