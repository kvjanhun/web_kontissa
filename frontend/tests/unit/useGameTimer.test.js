import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createApp } from 'vue'
import { useGameTimer } from '~/composables/useGameTimer.js'

// Mount a composable inside a real Vue app so lifecycle hooks (onMounted/onUnmounted) fire.
function withSetup(composable) {
  let result
  const app = createApp({
    setup() {
      result = composable()
      return () => {}
    },
  })
  const div = document.createElement('div')
  document.body.appendChild(div)
  app.mount(div)
  return { result, app, div }
}

function teardown({ app, div }) {
  app.unmount()
  div.parentNode?.removeChild(div)
}

function setDocumentHidden(hidden) {
  Object.defineProperty(document, 'hidden', { get: () => hidden, configurable: true })
}

describe('useGameTimer', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    setDocumentHidden(false)
  })

  afterEach(() => {
    vi.useRealTimers()
    setDocumentHidden(false)
  })

  // ---------------------------------------------------------------------------
  // Basic timer — no lifecycle needed
  // ---------------------------------------------------------------------------

  describe('start and getElapsedMs', () => {
    it('returns 0 before start', () => {
      const { getElapsedMs } = useGameTimer()
      expect(getElapsedMs()).toBe(0)
    })

    it('returns elapsed time after start', () => {
      const { start, getElapsedMs } = useGameTimer()
      start()
      vi.advanceTimersByTime(1000)
      expect(getElapsedMs()).toBe(1000)
    })

    it('tracks elapsed across multiple advances', () => {
      const { start, getElapsedMs } = useGameTimer()
      start()
      vi.advanceTimersByTime(500)
      vi.advanceTimersByTime(250)
      expect(getElapsedMs()).toBe(750)
    })

    it('start() is idempotent — second call does not reset the clock', () => {
      const { start, getElapsedMs } = useGameTimer()
      start()
      vi.advanceTimersByTime(500)
      start() // should be a no-op
      vi.advanceTimersByTime(500)
      expect(getElapsedMs()).toBe(1000)
    })

    it('startedAt ref is null before start', () => {
      const { startedAt } = useGameTimer()
      expect(startedAt.value).toBeNull()
    })

    it('startedAt ref is set to current timestamp after start', () => {
      const { start, startedAt } = useGameTimer()
      vi.setSystemTime(new Date('2026-01-01T12:00:00.000Z'))
      start()
      expect(startedAt.value).toBe(new Date('2026-01-01T12:00:00.000Z').getTime())
    })

    it('totalPausedMs starts at 0', () => {
      const { totalPausedMs } = useGameTimer()
      expect(totalPausedMs.value).toBe(0)
    })
  })

  // ---------------------------------------------------------------------------
  // reset
  // ---------------------------------------------------------------------------

  describe('reset', () => {
    it('clears startedAt, totalPausedMs, and elapsed', () => {
      const { start, reset, getElapsedMs, startedAt, totalPausedMs } = useGameTimer()
      start()
      vi.advanceTimersByTime(1000)
      reset()
      expect(startedAt.value).toBeNull()
      expect(totalPausedMs.value).toBe(0)
      expect(getElapsedMs()).toBe(0)
    })

    it('allows the timer to be restarted cleanly after reset', () => {
      const { start, reset, getElapsedMs } = useGameTimer()
      start()
      vi.advanceTimersByTime(1000)
      reset()
      start()
      vi.advanceTimersByTime(300)
      expect(getElapsedMs()).toBe(300)
    })
  })

  // ---------------------------------------------------------------------------
  // Pause / resume via visibility — require mounted lifecycle
  // ---------------------------------------------------------------------------

  describe('pause and resume via visibilitychange', () => {
    it('pauses when document becomes hidden', () => {
      const setup = withSetup(() => useGameTimer())
      const { start, getElapsedMs } = setup.result
      try {
        start()
        vi.advanceTimersByTime(1000) // 1 s active

        setDocumentHidden(true)
        document.dispatchEvent(new Event('visibilitychange'))
        vi.advanceTimersByTime(500) // 500 ms paused — should not count

        setDocumentHidden(false)
        document.dispatchEvent(new Event('visibilitychange'))
        vi.advanceTimersByTime(500) // 500 ms more active

        expect(getElapsedMs()).toBe(1500)
      } finally {
        teardown(setup)
      }
    })

    it('does not accumulate pause time when visibilitychange fires but tab is visible', () => {
      const setup = withSetup(() => useGameTimer())
      const { start, getElapsedMs } = setup.result
      try {
        start()
        vi.advanceTimersByTime(1000)

        setDocumentHidden(false)
        document.dispatchEvent(new Event('visibilitychange')) // visible — no-op (hiddenAt is null)
        vi.advanceTimersByTime(1000)

        expect(getElapsedMs()).toBe(2000)
      } finally {
        teardown(setup)
      }
    })

    it('accumulates multiple pause intervals correctly', () => {
      const setup = withSetup(() => useGameTimer())
      const { start, getElapsedMs } = setup.result
      try {
        start()
        vi.advanceTimersByTime(1000) // active: 1000

        setDocumentHidden(true)
        document.dispatchEvent(new Event('visibilitychange'))
        vi.advanceTimersByTime(300) // paused

        setDocumentHidden(false)
        document.dispatchEvent(new Event('visibilitychange'))
        vi.advanceTimersByTime(500) // active: 1500

        setDocumentHidden(true)
        document.dispatchEvent(new Event('visibilitychange'))
        vi.advanceTimersByTime(200) // paused

        setDocumentHidden(false)
        document.dispatchEvent(new Event('visibilitychange'))
        vi.advanceTimersByTime(500) // active: 2000

        expect(getElapsedMs()).toBe(2000)
      } finally {
        teardown(setup)
      }
    })

    it('totalPausedMs ref reflects accumulated pause duration', () => {
      const setup = withSetup(() => useGameTimer())
      const { start, totalPausedMs } = setup.result
      try {
        start()
        setDocumentHidden(true)
        document.dispatchEvent(new Event('visibilitychange'))
        vi.advanceTimersByTime(400)
        setDocumentHidden(false)
        document.dispatchEvent(new Event('visibilitychange'))
        expect(totalPausedMs.value).toBe(400)
      } finally {
        teardown(setup)
      }
    })
  })

  // ---------------------------------------------------------------------------
  // pagehide
  // ---------------------------------------------------------------------------

  describe('pagehide', () => {
    it('marks pause start when not already paused', () => {
      const setup = withSetup(() => useGameTimer())
      const { start, getElapsedMs } = setup.result
      try {
        start()
        vi.advanceTimersByTime(1000) // active: 1000

        window.dispatchEvent(new Event('pagehide')) // sets hiddenAt
        vi.advanceTimersByTime(400) // paused

        // Resume via visibilitychange (hidden → visible)
        setDocumentHidden(false)
        document.dispatchEvent(new Event('visibilitychange'))
        vi.advanceTimersByTime(200) // active: 1200

        expect(getElapsedMs()).toBe(1200)
      } finally {
        teardown(setup)
      }
    })

    it('is a no-op if already paused by visibilitychange', () => {
      const setup = withSetup(() => useGameTimer())
      const { start, getElapsedMs } = setup.result
      try {
        start()
        vi.advanceTimersByTime(1000) // active: 1000

        setDocumentHidden(true)
        document.dispatchEvent(new Event('visibilitychange')) // hiddenAt = 1000
        vi.advanceTimersByTime(200)

        window.dispatchEvent(new Event('pagehide')) // should not overwrite hiddenAt
        vi.advanceTimersByTime(200)

        setDocumentHidden(false)
        document.dispatchEvent(new Event('visibilitychange')) // resumes, totalPaused = 400
        // No advance after resume — elapsed should still be the initial 1000
        expect(getElapsedMs()).toBe(1000)
      } finally {
        teardown(setup)
      }
    })
  })

  // ---------------------------------------------------------------------------
  // blur (also calls handleVisibilityChange)
  // ---------------------------------------------------------------------------

  describe('blur event', () => {
    it('starts pause when blur fires and document is hidden', () => {
      const setup = withSetup(() => useGameTimer())
      const { start, getElapsedMs } = setup.result
      try {
        start()
        vi.advanceTimersByTime(500)

        setDocumentHidden(true)
        window.dispatchEvent(new Event('blur')) // calls handleVisibilityChange → pause
        vi.advanceTimersByTime(300) // paused

        setDocumentHidden(false)
        document.dispatchEvent(new Event('visibilitychange')) // resume
        vi.advanceTimersByTime(500) // active: 1000

        expect(getElapsedMs()).toBe(1000)
      } finally {
        teardown(setup)
      }
    })

    it('is a no-op when blur fires and document is not hidden', () => {
      const setup = withSetup(() => useGameTimer())
      const { start, getElapsedMs } = setup.result
      try {
        start()
        vi.advanceTimersByTime(1000)

        setDocumentHidden(false)
        window.dispatchEvent(new Event('blur')) // no-op (not hidden, hiddenAt is null)
        vi.advanceTimersByTime(1000)

        expect(getElapsedMs()).toBe(2000)
      } finally {
        teardown(setup)
      }
    })
  })

  // ---------------------------------------------------------------------------
  // Cleanup — listeners removed on unmount
  // ---------------------------------------------------------------------------

  describe('cleanup on unmount', () => {
    it('stops responding to visibility events after unmount', () => {
      const setup = withSetup(() => useGameTimer())
      const { start, getElapsedMs } = setup.result

      start()
      vi.advanceTimersByTime(500)

      teardown(setup) // unmounts — removes event listeners

      // These events should no longer affect the timer
      setDocumentHidden(true)
      document.dispatchEvent(new Event('visibilitychange'))
      vi.advanceTimersByTime(500)

      // If listeners were removed, elapsed should be the original 500ms
      // (no pause accumulated after unmount)
      // Note: getElapsedMs still works because startedAt was set
      // The elapsed will be 1000ms (500 + 500) with no pause deducted
      expect(getElapsedMs()).toBe(1000)
    })
  })
})
