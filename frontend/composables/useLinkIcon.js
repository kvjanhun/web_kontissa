// Maps a link's href to a leading icon name. Brand logos (monochrome Simple
// Icons) for GitHub/LinkedIn, a letter glyph for mailto:, and a diagonal
// go-arrow for everything else — replacing the old plain "→" suffix.
// Names are dynamic, so every value here must also be listed in the
// `icon.clientBundle.icons` array in nuxt.config.ts to be bundled offline.
export function useLinkIcon() {
  function linkIcon(href = '') {
    if (href.startsWith('mailto:')) return 'solar:letter-bold'
    if (/(^|\/\/|\.)github\.com/i.test(href)) return 'simple-icons:github'
    if (/(^|\/\/|\.)linkedin\.com/i.test(href)) return 'simple-icons:linkedin'
    return 'solar:arrow-right-up-bold'
  }
  return { linkIcon }
}
