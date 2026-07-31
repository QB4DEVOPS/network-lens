import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiPortFile = path.resolve(__dirname, "../backend/.api_port");
  const filePort = fs.existsSync(apiPortFile) ? fs.readFileSync(apiPortFile, "utf8").trim() : "";
  const apiPort = env.VITE_API_PORT || filePort || "8000";
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/sync": {
          target: `http://127.0.0.1:${apiPort}`,
          changeOrigin: true,
        },
        "/health": {
          target: `http://127.0.0.1:${apiPort}`,
          changeOrigin: true,
        },
      },
    },
  };
});
