import { resolve } from 'path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  test: {
    exclude: ['e2e/**', 'node_modules/**'],
  },
  server: {
    proxy: {
      '/api': 'http://localhost:5001',
      '/sitemap.xml': 'http://localhost:5001',
    }
  },
  build: {
    outDir: resolve(__dirname, '../app/static/dist'),
    emptyDirBeforeWrite: true,
  },
  ssgOptions: {
    script: 'async',
    formatting: 'minify',
    dirStyle: 'nested',
    includedRoutes: () => ['/', '/about', '/contact', '/login']
  }
})
