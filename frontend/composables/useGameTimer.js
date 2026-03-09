import { ref, onMounted, onUnmounted } from 'vue'

/**
 * Tracks elapsed play time, pausing when the tab is hidden or blurred.
 * Call start() to begin timing (idempotent). getElapsedMs() returns
 * the active (non-paused) duration.
 */
export function useGameTimer() {
  const startedAt = ref(null)
  const totalPausedMs = ref(0)
  let hiddenAt = null

  function start() {
    if (!startedAt.value) startedAt.value = Date.now()
  }

  function getElapsedMs() {
    if (!startedAt.value) return 0
    return Date.now() - startedAt.value - totalPausedMs.value
  }

  function reset() {
    startedAt.value = null
    totalPausedMs.value = 0
    hiddenAt = null
  }

  function handleVisibilityChange() {
    if (document.hidden) {
      hiddenAt = Date.now()
    } else if (hiddenAt !== null) {
      totalPausedMs.value += Date.now() - hiddenAt
      hiddenAt = null
    }
  }

  function handlePageHide() {
    if (hiddenAt === null) hiddenAt = Date.now()
  }

  onMounted(() => {
    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('blur', handleVisibilityChange)
    window.addEventListener('pagehide', handlePageHide)
  })

  onUnmounted(() => {
    document.removeEventListener('visibilitychange', handleVisibilityChange)
    window.removeEventListener('blur', handleVisibilityChange)
    window.removeEventListener('pagehide', handlePageHide)
  })

  return { startedAt, totalPausedMs, start, getElapsedMs, reset }
}
