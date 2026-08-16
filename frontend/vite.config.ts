import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Matches the origin already allowed by backend/main.py's CORS config.
    port: 3000,
    proxy: {
      // Lets the frontend call same-origin `/api/...` (and `/health`) in
      // dev without hardcoding the backend's host:port or relying on CORS
      // at all. The FastAPI CORS config in backend/main.py stays as a
      // fallback for anyone calling the API directly (not through this
      // dev server). `/health` lives outside `/api` in main.py (a
      // deliberate top-level convention for health checks), so it needs
      // its own proxy entry — a single "/api" entry doesn't cover it.
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
