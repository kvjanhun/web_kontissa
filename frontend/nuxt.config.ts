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
      routes: ['/', '/login', '/dog', '/dog/about-crawler', '/200.html'],
    },
  },

  routeRules: {
    '/api/**': { proxy: `${apiBaseUrl}/api/**` },
    '/sitemap.xml': { proxy: `${apiBaseUrl}/sitemap.xml` },
    '/about': { redirect: '/' },
    '/contact': { redirect: '/' },
  },

  // Modules
  modules: ['@pinia/nuxt', '@nuxt/icon'],

  // Iconify icons (Solar for UI chrome, Flat Color Icons reserved for the admin panel).
  // Bundled at build time with no runtime fallback to api.iconify.design — keeps the
  // SSG output fully self-hosted (no external requests from visitors' browsers).
  icon: {
    // CSS mode (mask + background-color: currentColor) renders reliably under SSG
    // hydration; svg mode dropped the inlined paths on the client, leaving the icon
    // stuck black/invisible regardless of the theme's text color.
    mode: 'css',
    fallbackToApi: false,
    clientBundle: {
      scan: true,
      icons: [
        'solar:sun-2-bold',
        'solar:moon-bold',
        'solar:hamburger-menu-bold',
        'solar:close-square-bold',
        'solar:alt-arrow-down-bold',
        // Link-type icons resolved dynamically by useLinkIcon() (scan can't see them)
        'solar:letter-bold',
        'solar:arrow-right-up-bold',
        'simple-icons:github',
        'simple-icons:linkedin',
        // Admin panel (Flat Color Icons). The nav/stat icons are bound dynamically
        // (`:name="n.icon"` from JS arrays), so `scan` can't see them — list them here.
        // The client-bundle resolver needs the canonical collection name
        // (`flat-color-icons:`), not the `fc:` runtime alias used in components.
        'flat-color-icons:home',
        'flat-color-icons:document',
        'flat-color-icons:gallery',
        'flat-color-icons:news',
        'flat-color-icons:combo-chart',
        'flat-color-icons:services',
        'flat-color-icons:export',
        'flat-color-icons:globe',
        'flat-color-icons:database',
        'flat-color-icons:ok',
        'flat-color-icons:no-idea',
        'flat-color-icons:plus',
        'flat-color-icons:edit-image',
        'flat-color-icons:full-trash',
      ],
    },
  },

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
