import { computed } from 'vue'
import { useI18nStore } from '~/stores/i18n.js'

// Bands an admin can hide, in page order. Mirrors HOME_SECTIONS in
// app/home_content.py. The keys are the `<section id>` anchors the page already
// uses, so `work` is the Projects band. The hero and footer are page chrome and
// are not hideable.
export const HIDEABLE_SECTIONS = ['work', 'stack', 'terminal']

export function useHomeSections() {
  const { tm } = useI18nStore()

  // `home.hiddenSections` rides the home-content overlay, so it is already in the
  // build snapshot and a hidden band never paints before being removed. A build
  // snapshot predating the feature has no such key — read that as "nothing hidden"
  // rather than letting the page render as its raw key would elsewhere.
  const hiddenSections = computed(() => {
    const raw = tm('home.hiddenSections')
    return new Set(Array.isArray(raw) ? raw : [])
  })

  function isVisible(key) {
    return !hiddenSections.value.has(key)
  }

  return { hiddenSections, isVisible }
}
