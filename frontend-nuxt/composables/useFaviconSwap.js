import { onMounted, onUnmounted } from 'vue'

/**
 * Swaps the page favicon on mount and restores it on unmount.
 * Uses a real URL (not a data URI) because Safari ignores dynamically
 * set data-URI / blob-URL favicons entirely.
 */
export function useFaviconSwap(href) {
  let originalEl = null
  let swappedEl = null

  onMounted(() => {
    originalEl = document.querySelector("link[rel='icon']")
    if (originalEl) originalEl.remove()

    swappedEl = document.createElement('link')
    swappedEl.rel = 'icon'
    swappedEl.type = 'image/png'
    swappedEl.href = href
    document.head.appendChild(swappedEl)
  })

  onUnmounted(() => {
    if (swappedEl) swappedEl.remove()
    if (originalEl) document.head.appendChild(originalEl)
  })
}
