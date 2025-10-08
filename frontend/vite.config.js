import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    open: false,
    proxy: {
      '/translate': { target: 'http://127.0.0.1:8789', changeOrigin: true },
      '/edge':      { target: 'http://127.0.0.1:8789', changeOrigin: true }
    }
  },
  build: { outDir: 'dist', sourcemap: true }
})
