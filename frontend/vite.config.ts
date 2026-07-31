import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    proxy: {
      // Proxy /api → FastAPI backend so we avoid CORS issues in dev
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
})
