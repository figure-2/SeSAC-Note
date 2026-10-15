import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    allowedHosts: ['sesac-note.lvh.me'],
    proxy: {
      '/api': { target: 'http://127.0.0.1:8080', changeOrigin: true },
      '/videos': { target: 'http://127.0.0.1:8080', changeOrigin: true },
      '/process': { target: 'http://127.0.0.1:8080', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8080', changeOrigin: true },
      '/stt': { target: 'http://127.0.0.1:8080', changeOrigin: true },
    },
  },
})
