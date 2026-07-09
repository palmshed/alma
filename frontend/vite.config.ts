import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/terms': 'http://localhost:8000',
      '/privacy': 'http://localhost:8000',
      '/contact': 'http://localhost:8000',
      '/help': 'http://localhost:8000',
    },
  },
  test: {
    globals: true,
    environment: 'happy-dom',
  },
})
