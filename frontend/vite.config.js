import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  // 部署到 https://st.kahvia.wang/ 根路径，保持默认即可
  base: '/',
  // 仅影响本地 vite dev / preview，不影响线上静态资源
  server: {
    allowedHosts: ['st.kahvia.wang', 'xhs.waite.wang'],
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    allowedHosts: ['st.kahvia.wang', 'xhs.waite.wang'],
  },
})
