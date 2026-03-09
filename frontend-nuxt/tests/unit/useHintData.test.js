import { describe, it, expect } from 'vitest'
import { ref, computed } from 'vue'
import { useHintData } from '~/composables/useHintData.js'

function setup(hintData, found = [], outerArr = ['b', 'c', 'd', 'e', 'f', 'g'], centerChar = 'a') {
  const puzzle = ref({
    hint_data: hintData,
    center: centerChar,
  })
  const foundWords = ref(new Set(found))
  const outerLetters = ref(outerArr)
  const center = computed(() => puzzle.value?.center ?? '')
  return useHintData(puzzle, foundWords, outerLetters, center)
}

const HINT_DATA = {
  word_count: 10,
  pangram_count: 2,
  by_letter: { a: 4, b: 3, c: 3 },
  by_length: { '4': 5, '5': 3, '7': 2 },
  by_pair: { ab: 2, ac: 2, ba: 3, ca: 3 },
}

describe('letterMap', () => {
  it('returns remaining count per starting letter', () => {
    const { letterMap } = setup(HINT_DATA)
    expect(letterMap.value).toEqual([
      { letter: 'a', remaining: 4 },
      { letter: 'b', remaining: 3 },
      { letter: 'c', remaining: 3 },
    ])
  })

  it('decrements remaining when words are found', () => {
    const { letterMap } = setup(HINT_DATA, ['abcd', 'abce'])
    const a = letterMap.value.find(l => l.letter === 'a')
    expect(a.remaining).toBe(2)
  })

  it('shows 0 remaining when all words for a letter are found', () => {
    const { letterMap } = setup(HINT_DATA, ['abcd', 'abce', 'abcf', 'abcg'])
    const a = letterMap.value.find(l => l.letter === 'a')
    expect(a.remaining).toBe(0)
  })

  it('returns empty array when no hint data', () => {
    const { letterMap } = setup(null)
    expect(letterMap.value).toEqual([])
  })

  it('is sorted alphabetically', () => {
    const { letterMap } = setup(HINT_DATA)
    const letters = letterMap.value.map(l => l.letter)
    expect(letters).toEqual([...letters].sort())
  })
})

describe('unfoundLengths', () => {
  it('returns longest word length and unique length count', () => {
    const { unfoundLengths } = setup(HINT_DATA)
    expect(unfoundLengths.value).toEqual({ longest: 7, uniqueLengths: 3 })
  })

  it('excludes fully found lengths', () => {
    // Find all 5 4-letter words → only 5 and 7 remain
    const found = ['abca', 'abcb', 'abcc', 'abcd', 'abce']
    const { unfoundLengths } = setup(HINT_DATA, found)
    expect(unfoundLengths.value.uniqueLengths).toBe(2) // 5 and 7
  })

  it('returns null when all words found', () => {
    const found = Array.from({ length: 10 }, (_, i) => `word${i}`)
    const { unfoundLengths } = setup(HINT_DATA, found)
    expect(unfoundLengths.value).toBeNull()
  })

  it('returns null when no hint data', () => {
    const { unfoundLengths } = setup(null)
    expect(unfoundLengths.value).toBeNull()
  })
})

describe('pangramStats', () => {
  it('returns total pangrams from hint data', () => {
    const { pangramStats } = setup(HINT_DATA)
    expect(pangramStats.value.total).toBe(2)
  })

  it('counts found pangrams correctly', () => {
    // A pangram contains all 7 letters (a,b,c,d,e,f,g)
    const { pangramStats } = setup(HINT_DATA, ['abcdefg'])
    expect(pangramStats.value.found).toBe(1)
    expect(pangramStats.value.remaining).toBe(1)
  })

  it('does not count non-pangrams', () => {
    const { pangramStats } = setup(HINT_DATA, ['abcd'])
    expect(pangramStats.value.found).toBe(0)
  })

  it('handles no hint data', () => {
    const { pangramStats } = setup(null)
    expect(pangramStats.value).toEqual({ total: 0, found: 0, remaining: 0 })
  })
})

describe('lengthDistribution', () => {
  it('returns distribution sorted by length', () => {
    const { lengthDistribution } = setup(HINT_DATA)
    const lens = lengthDistribution.value.map(d => d.len)
    expect(lens).toEqual([4, 5, 7])
  })

  it('calculates remaining per length', () => {
    const { lengthDistribution } = setup(HINT_DATA, ['abcd']) // 1 four-letter word found
    const four = lengthDistribution.value.find(d => d.len === 4)
    expect(four.total).toBe(5)
    expect(four.remaining).toBe(4)
  })

  it('returns empty array when no hint data', () => {
    const { lengthDistribution } = setup(null)
    expect(lengthDistribution.value).toEqual([])
  })
})

describe('pairMap', () => {
  it('returns remaining count per letter pair', () => {
    const { pairMap } = setup(HINT_DATA)
    expect(pairMap.value.find(p => p.pair === 'ab').remaining).toBe(2)
    expect(pairMap.value.find(p => p.pair === 'ba').remaining).toBe(3)
  })

  it('decrements remaining when matching words found', () => {
    const { pairMap } = setup(HINT_DATA, ['abcd'])
    expect(pairMap.value.find(p => p.pair === 'ab').remaining).toBe(1)
  })

  it('is sorted alphabetically', () => {
    const { pairMap } = setup(HINT_DATA)
    const pairs = pairMap.value.map(p => p.pair)
    expect(pairs).toEqual([...pairs].sort())
  })

  it('returns empty array when no hint data', () => {
    const { pairMap } = setup(null)
    expect(pairMap.value).toEqual([])
  })
})
