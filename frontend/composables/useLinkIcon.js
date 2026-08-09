// Answers the two questions every rendered link needs: which leading icon it gets,
// and whether it leaves the site.
//
// Icons: brand logos (monochrome Simple Icons) for GitHub/LinkedIn, a letter glyph
// for mailto:, a diagonal go-arrow for other external destinations, and a plain
// right arrow for internal routes/anchors — the diagonal arrow conventionally means
// "leaves this site", so #stack and /dog shouldn't wear it.
//
// Names are dynamic, so every value here must also be listed in the
// `icon.clientBundle.icons` array in nuxt.config.ts to be bundled offline —
// `fallbackToApi` is false, so an unlisted icon silently renders nothing.
export function useLinkIcon() {
  // Shared by HomeFooter and HomeWork so admin-authored links get the same
  // target/rel treatment wherever they're rendered.
  function isExternal(href = '') {
    return /^(https?:|mailto:)/i.test(href)
  }

  function linkIcon(href = '') {
    if (/^mailto:/i.test(href)) return 'solar:letter-bold'
    if (/(^|\/\/|\.)github\.com/i.test(href)) return 'simple-icons:github'
    if (/(^|\/\/|\.)linkedin\.com/i.test(href)) return 'simple-icons:linkedin'
    return isExternal(href) ? 'solar:arrow-right-up-bold' : 'solar:arrow-right-bold'
  }

  return { linkIcon, isExternal }
}
