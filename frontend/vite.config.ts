import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3051,
    proxy: {
      '/api': {
        target: 'http://localhost:8009',
        changeOrigin: true
      }
    }
  }
})
