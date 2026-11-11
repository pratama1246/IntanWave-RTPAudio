import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss()
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.INTANWAVE_DEV_BACKEND || 'http://127.0.0.1:7080',
        changeOrigin: true,
      },
      '/ws': {
        target: process.env.INTANWAVE_DEV_BACKEND || 'http://127.0.0.1:7080',
        ws: true,
      }
    }
  }
})
