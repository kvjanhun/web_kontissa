import tailwindcss from '@tailwindcss/vite'

const apiBaseUrl = (process.env.API_BASE_URL || 'http://localhost:5001').replace(/\/$/, '')

export default defineNuxtConfig({
  compatibilityDate: '2025-06-01',

  // Use a separate build directory during testing to prevent E2E runs from corrupting/clashing with local dev server (.nuxt)
  buildDir: process.env.TESTING ? '.nuxt-e2e' : '.nuxt',
  ...(process.env.TESTING ? { sourcemap: false } : {}),

  experimental: {
    payloadExtraction: false,
    appManifest: false,
  },

  // Static site generation
  ssr: true,
  nitro: {
    prerender: {
      routes: ['/', '/login', '/dog', '/200.html'],
    },
  },

  routeRules: {
    '/api/**': { proxy: `${apiBaseUrl}/api/**` },
    '/sitemap.xml': { proxy: `${apiBaseUrl}/sitemap.xml` },
    '/about': { redirect: '/' },
    '/contact': { redirect: '/' },
  },

  // Modules
  modules: ['@pinia/nuxt'],

  // Tailwind CSS 4 via Vite plugin
  vite: {
    plugins: [tailwindcss()],
    server: {
      watch: {
        ignored: ['**/.nuxt-e2e/**'],
      },
    },
  },

  // Global CSS
  css: ['~/assets/style.css'],

  // Default app head
  app: {
    head: {
      htmlAttrs: { lang: 'en', 'data-allow-mismatch': 'class' },
      charset: 'utf-8',
      viewport: 'width=device-width, initial-scale=1.0, viewport-fit=cover',
      title: 'erez.ac - Konsta Janhunen',
      meta: [
        { name: 'description', content: 'Konsta Janhunen — Developer, tinkerer, technology enthusiast.' },
        { property: 'og:title', content: 'erez.ac — Konsta Janhunen' },
        { property: 'og:description', content: 'Developer & tinkerer. Full-stack developer, and technology enthusiast.' },
        { property: 'og:url', content: 'https://erez.ac' },
        { property: 'og:type', content: 'website' },
        { property: 'og:image', content: 'https://erez.ac/og-image.png' },
        { property: 'og:image:width', content: '1200' },
        { property: 'og:image:height', content: '630' },
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:image', content: 'https://erez.ac/og-image.png' },
      ],
      link: [],
      script: [
        // Dark mode flash prevention — runs before Vue hydrates
        {
          innerHTML: `(function(){var t=localStorage.getItem('theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark')}})()`,
          tagPosition: 'head',
        },
        // Schema.org JSON-LD
        {
          type: 'application/ld+json',
          innerHTML: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'Person',
            name: 'Konsta Janhunen',
            url: 'https://erez.ac',
          }),
        },
      ],
    },
  },

  // Auto-import directories
  imports: {
    dirs: ['stores', 'composables'],
  },

  // Disable Nuxt devtools in production
  devtools: { enabled: !process.env.TESTING },
})
