import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  root: "ui",
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:3177",
      "/data": "http://localhost:3177"
    }
  },
  build: {
    outDir: "../ui-dist",
    emptyOutDir: true
  }
});

