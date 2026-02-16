import { resolve } from 'path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:5000',
      '/sitemap.xml': 'http://localhost:5000',
    }
  },
  build: {
    outDir: resolve(__dirname, '../app/static/dist'),
    emptyDirBeforeWrite: true,
  }
})
