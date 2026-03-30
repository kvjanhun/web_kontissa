import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  compatibilityDate: '2025-06-01',

  experimental: {
    payloadExtraction: false,
  },

  // Static site generation
  ssr: true,
  nitro: {
    prerender: {
      routes: ['/', '/about', '/contact', '/login', '/sanakenno', '/200.html'],
    },
  },

  routeRules: {
    '/api/**': { proxy: 'http://localhost:5001/api/**' },
    '/sitemap.xml': { proxy: 'http://localhost:5001/sitemap.xml' },
  },

  // Modules
  modules: ['@pinia/nuxt'],

  // Tailwind CSS 4 via Vite plugin
  vite: {
    plugins: [tailwindcss()],
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
