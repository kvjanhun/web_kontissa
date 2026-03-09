/**
 * Pure Sanakenno game logic — no Vue reactivity, no DOM access.
 * Extracted for unit testing and reuse.
 */

export const RANKS = [
  { pct: 100, name: 'Täysi kenno' },
  { pct: 70,  name: 'Ällistyttävä' },
  { pct: 40,  name: 'Sanavalmis' },
  { pct: 20,  name: 'Onnistuja' },
  { pct: 10,  name: 'Nyt mennään!' },
  { pct: 2,   name: 'Hyvä alku' },
  { pct: 0,   name: 'Etsi sanoja!' },
]

export function scoreWord(word, allLetters) {
  const pts = word.length === 4 ? 1 : word.length
  const isPangram = [...allLetters].every(c => word.includes(c))
  return pts + (isPangram ? 7 : 0)
}

export function recalcScore(words, allLetters) {
  let total = 0
  for (const w of words) {
    total += scoreWord(w, allLetters)
  }
  return total
}

export function rankForScore(score, maxScore) {
  if (maxScore === 0) return RANKS[RANKS.length - 1].name
  const pct = (score / maxScore) * 100
  for (const r of RANKS) {
    if (pct >= r.pct) return r.name
  }
  return RANKS[RANKS.length - 1].name
}

export function rankThresholds(currentRank, maxScore) {
  const visible = currentRank === 'Täysi kenno'
    ? RANKS
    : RANKS.filter(r => r.name !== 'Täysi kenno')
  return [...visible].reverse().map(r => ({
    name: r.name,
    points: Math.ceil(r.pct / 100 * maxScore),
    isCurrent: currentRank === r.name,
  }))
}

export function progressToNextRank(score, maxScore) {
  if (maxScore === 0) return 0
  const scorePct = (score / maxScore) * 100
  const currentIdx = RANKS.findIndex(r => scorePct >= r.pct)
  if (currentIdx === -1) return 0
  if (currentIdx === 0) return 100
  const currentRankPts = Math.ceil(RANKS[currentIdx].pct / 100 * maxScore)
  const nextRankPts = Math.ceil(RANKS[currentIdx - 1].pct / 100 * maxScore)
  if (nextRankPts <= currentRankPts) return 100
  return Math.min(100, ((score - currentRankPts) / (nextRankPts - currentRankPts)) * 100)
}

export function colorizeWord(word, center, allLetters) {
  return [...word].map(char => {
    if (char === '-')              return { char, color: 'tertiary' }
    if (char === center)           return { char, color: 'accent' }
    if (allLetters.has(char))      return { char, color: 'primary' }
    return { char, color: 'tertiary' }
  })
}

export function toColumns(words, perColumn = 10) {
  const cols = []
  for (let i = 0; i < words.length; i += perColumn) {
    cols.push(words.slice(i, i + perColumn))
  }
  return cols
}
