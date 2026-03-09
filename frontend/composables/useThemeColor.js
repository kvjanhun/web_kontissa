import { onMounted, onUnmounted } from 'vue'

/**
 * Manages the <meta name="theme-color"> tag and html background color
 * to match --color-bg-primary. Observes dark/light class changes on <html>.
 * Restores original values on unmount.
 */
export function useThemeColor() {
  let meta = null
  let originalContent = null
  let originalHtmlBg = null
  let observer = null

  function readColor() {
    return getComputedStyle(document.documentElement)
      .getPropertyValue('--color-bg-primary').trim()
  }

  function apply() {
    const color = readColor()
    meta.content = color
    document.documentElement.style.backgroundColor = color
  }

  onMounted(() => {
    meta = document.querySelector('meta[name="theme-color"]')
    if (!meta) {
      meta = document.createElement('meta')
      meta.name = 'theme-color'
      document.head.appendChild(meta)
      originalContent = null
    } else {
      originalContent = meta.content
    }

    originalHtmlBg = document.documentElement.style.backgroundColor
    apply()

    observer = new MutationObserver(apply)
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    })
  })

  onUnmounted(() => {
    if (observer) { observer.disconnect(); observer = null }
    if (!meta) return

    if (originalContent != null) {
      meta.content = originalContent
    } else {
      meta.remove()
    }
    document.documentElement.style.backgroundColor = originalHtmlBg
  })
}
