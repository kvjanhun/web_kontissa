// Reveal-on-scroll for the homepage redesign. Returns a Vue directive object
// (use as `const vReveal = useScrollReveal()` in <script setup>, then `v-reveal`).
//
// Progressive enhancement: with no JS, no IntersectionObserver, or when the user
// prefers reduced motion, elements stay fully visible — the fade-up is purely
// additive. The pre-reveal state is set in JS (not SSR markup) so there is no
// hydration mismatch.
export function useScrollReveal() {
  return {
    mounted(el) {
      if (typeof window === 'undefined') return
      const prefersReduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
      if (prefersReduced || !('IntersectionObserver' in window)) return

      el.style.opacity = '0'
      el.style.transform = 'translateY(18px)'
      el.style.transition = 'opacity 0.6s ease, transform 0.6s ease'

      const io = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.style.opacity = '1'
              entry.target.style.transform = 'none'
              io.unobserve(entry.target)
            }
          })
        },
        { threshold: 0.12 }
      )
      io.observe(el)
      el._revealObserver = io
    },
    unmounted(el) {
      el._revealObserver?.disconnect()
    },
  }
}
