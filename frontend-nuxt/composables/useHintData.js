import { computed } from 'vue'

/**
 * Derives hint panel data from puzzle hint_data and found words.
 * All computeds are pure — no side effects, no API calls.
 *
 * @param {import('vue').Ref} puzzle - puzzle ref (needs .hint_data, .center)
 * @param {import('vue').Ref<Set<string>>} foundWords - set of found word strings
 * @param {import('vue').Ref<string[]>} outerLetters - outer letters array
 * @param {import('vue').ComputedRef<string>} center - center letter
 */
export function useHintData(puzzle, foundWords, outerLetters, center) {
  const foundByLetter = computed(() => {
    const map = {}
    for (const word of foundWords.value) {
      const l = word[0]
      map[l] = (map[l] || 0) + 1
    }
    return map
  })

  const foundByLength = computed(() => {
    const map = {}
    for (const word of foundWords.value) {
      const k = String(word.length)
      map[k] = (map[k] || 0) + 1
    }
    return map
  })

  const foundByPair = computed(() => {
    const map = {}
    for (const word of foundWords.value) {
      const pair = word.slice(0, 2)
      map[pair] = (map[pair] || 0) + 1
    }
    return map
  })

  const letterMap = computed(() => {
    const hd = puzzle.value?.hint_data
    if (!hd) return []
    return Object.entries(hd.by_letter)
      .map(([letter, total]) => ({ letter, remaining: total - (foundByLetter.value[letter] || 0) }))
      .sort((a, b) => a.letter.localeCompare(b.letter))
  })

  const unfoundLengths = computed(() => {
    const hd = puzzle.value?.hint_data
    if (!hd) return null
    const remaining = hd.word_count - foundWords.value.size
    if (remaining === 0) return null
    let longest = 0
    const uniqueLengths = new Set()
    for (const [len, total] of Object.entries(hd.by_length)) {
      const found = foundByLength.value[len] || 0
      if (total - found > 0) {
        uniqueLengths.add(parseInt(len))
        if (parseInt(len) > longest) longest = parseInt(len)
      }
    }
    return { longest, uniqueLengths: uniqueLengths.size }
  })

  const pangramStats = computed(() => {
    const hd = puzzle.value?.hint_data
    if (!hd) return { total: 0, found: 0, remaining: 0 }
    const letterSet = new Set([center.value, ...outerLetters.value])
    const foundPangrams = [...foundWords.value].filter(w => [...letterSet].every(c => w.includes(c))).length
    return { total: hd.pangram_count, found: foundPangrams, remaining: hd.pangram_count - foundPangrams }
  })

  const lengthDistribution = computed(() => {
    const hd = puzzle.value?.hint_data
    if (!hd) return []
    return Object.entries(hd.by_length)
      .map(([len, total]) => ({ len: parseInt(len), total, remaining: total - (foundByLength.value[len] || 0) }))
      .sort((a, b) => a.len - b.len)
  })

  const pairMap = computed(() => {
    const hd = puzzle.value?.hint_data
    if (!hd) return []
    return Object.entries(hd.by_pair)
      .map(([pair, total]) => ({ pair, remaining: total - (foundByPair.value[pair] || 0) }))
      .sort((a, b) => a.pair.localeCompare(b.pair))
  })

  return { letterMap, unfoundLengths, pangramStats, lengthDistribution, pairMap }
}
