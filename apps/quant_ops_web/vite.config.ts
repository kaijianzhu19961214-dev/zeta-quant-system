import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const opsApiTarget = env.QUANT_OPS_API_INTERNAL_URL || "http://quant_ops_api:8000";

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/ops-api": {
          target: opsApiTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/ops-api/, ""),
        },
      },
    },
  };
});
