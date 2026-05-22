import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 前端开发服务器：/api 与 /images 反代到本地后端
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5180,
    strictPort: true,
    proxy: {
      '/api': 'http://localhost:8000',
      '/images': 'http://localhost:8000',
    },
  },
})
