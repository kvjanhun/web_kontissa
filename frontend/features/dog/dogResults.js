export const DOG_GRADE_OPTIONS = [
  { value: '', label: 'Kaikki arvostelut' },
  { value: 'eri', label: 'ERI (Erinomainen)' },
  { value: 'eh', label: 'EH (Erittäin hyvä)' },
  { value: 'h', label: 'H (Hyvä)' },
  { value: 't', label: 'T (Tyydyttävä)' },
  { value: 'kp', label: 'KP (Kunniapalkinto)' },
  { value: 'hyl', label: 'HYL (Hylätty)' },
  { value: 'eva', label: 'EVA (Ei voida arvostella)' },
  { value: 'poissa', label: 'POISSA' },
]

export function firstQueryValue(value) {
  return Array.isArray(value) ? value[0] : value
}

export function buildDogQuery(query) {
  const clean = {}
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') clean[key] = String(value)
  }
  return clean
}

export function sameId(left, right) {
  return String(left) === String(right)
}

export function breedGroupKeyFromParts(group, breedId, fallback = '') {
  if (group && breedId) return `${group}:${breedId}`
  return fallback
}

export function breedGroupKey(breed) {
  return breedGroupKeyFromParts(breed?.group, breed?.breed_id, breed?.name || '')
}

export function dogBreedGroupKey(dog) {
  const breedObj = dog?.breedObj || {}
  return breedGroupKeyFromParts(
    dog?.breedGroup || breedObj.group,
    dog?.breedId || breedObj.breed_id,
    dog?.breedName || breedObj.name || '',
  )
}

export function isNumericString(value) {
  return /^\d+$/.test(String(value))
}

export function normalizeGrade(grade) {
  return (grade || '').toLowerCase().trim()
}

export function gradeMatchesFilter(dogGrade, filter) {
  const grade = normalizeGrade(dogGrade)
  if (!filter) return true
  if (filter === 'hyl') return grade === 'hyl' || grade === 'hylätty'
  if (filter === 'eva') return grade === 'eva' || grade === 'ei voida arvostella'
  if (filter === 'poissa') return grade === 'poissa'
  return grade === filter
}

export function searchTextMatches(value, query) {
  return String(value || '').toLowerCase().includes(query)
}

export function breedMatchesSearch(breed, query) {
  if (!query) return true
  return searchTextMatches(breed?.name, query) || searchTextMatches(breed?.judge, query)
}

export function dogMatchesShowSearch(dog, query) {
  if (!query) return true
  return (
    searchTextMatches(dog?.name, query) ||
    searchTextMatches(dog?.number, query) ||
    searchTextMatches(dog?.breedName, query) ||
    searchTextMatches(dog?.class_name, query) ||
    searchTextMatches(dog?.awards, query) ||
    searchTextMatches(dog?.breedObj?.judge, query)
  )
}

export function dogMatchesShowFilters(dog, filters = {}) {
  const grade = String(filters.grade || '').toLowerCase().trim()
  if (grade && !gradeMatchesFilter(dog.grade, grade)) return false

  const className = String(filters.className || '').toLowerCase().trim()
  if (className && (dog.class_name || '').toLowerCase() !== className) return false

  const award = String(filters.award || '').trim()
  if (award && !awardMatchesFilter(dog.awards, award)) return false

  return true
}

function optionalNumber(value) {
  if (value === undefined || value === null || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function timestampValue(value) {
  const numeric = optionalNumber(value)
  if (numeric !== null) return numeric
  if (!value) return 0
  const parsed = Date.parse(value)
  return Number.isNaN(parsed) ? 0 : parsed
}

function breedResultProgress(breed, breedDogs = []) {
  const progress = breed?.result_progress || {}
  const explicitCount = optionalNumber(breed?.result_count ?? progress.rated_count)
  const explicitTotal = optionalNumber(breed?.result_total_count ?? progress.total_count ?? breed?.count)
  const totalCount = explicitTotal === null ? null : Math.max(0, explicitTotal)
  let resultCount = explicitCount === null ? breedDogs.length : Math.max(0, explicitCount)
  if (totalCount !== null) resultCount = Math.min(resultCount, totalCount)

  const updatedAt = breed?.result_updated_at ?? progress.updated_at ?? null
  const known = explicitCount !== null || Boolean(breed?.result_progress)
  return {
    known,
    resultCount,
    totalCount,
    updatedAt,
    updatedTime: timestampValue(updatedAt),
    label: known && totalCount !== null ? `${resultCount}/${totalCount}` : '',
  }
}

export function createShowBreedGroups({
  breeds = [],
  dogs = [],
  query = '',
  allDogsLoaded = false,
  resultsOnly = false,
  allowUncheckedResults = false,
  filters = {},
} = {}) {
  const q = query.toLowerCase().trim()
  const dogsByBreed = {}

  for (const dog of dogs) {
    const key = dogBreedGroupKey(dog)
    if (!dogsByBreed[key]) dogsByBreed[key] = []
    dogsByBreed[key].push(dog)
  }

  const groups = {}
  let order = 0
  for (const breed of breeds) {
    const key = breedGroupKey(breed)
    const breedDogs = dogsByBreed[key] || []
    const progress = breedResultProgress(breed, breedDogs)
    const hasRatedResults = progress.known
      ? progress.resultCount > 0
      : Boolean(breed.has_results || breedDogs.length)
    if (resultsOnly && !hasRatedResults) continue

    const breedMatch = breedMatchesSearch(breed, q)
    const matchingDogs = q ? breedDogs.filter(dog => dogMatchesShowSearch(dog, q)) : breedDogs
    const hasResultFilters = Boolean(filters.grade || filters.className || filters.award)

    if (q || hasResultFilters) {
      if (allDogsLoaded) {
        if (!breedMatch && !matchingDogs.length) continue
        if (hasResultFilters && !breedDogs.length) continue
      } else if (!breedMatch) {
        continue
      }
    }

    const hasOpenableResults = Boolean(
      breed.has_results || hasRatedResults || breedDogs.length || allowUncheckedResults
    )
    groups[key] = {
      key,
      breed: {
        ...breed,
        has_results: breed.has_results || hasRatedResults || Boolean(breedDogs.length),
        can_fetch_results: hasOpenableResults,
      },
      breedName: breed.name,
      count: breed.count,
      judge: breed.judge,
      has_results: breed.has_results || hasRatedResults || Boolean(breedDogs.length),
      canOpenResults: hasOpenableResults,
      hasRatedResults,
      resultCount: progress.resultCount,
      resultTotalCount: progress.totalCount,
      resultUpdatedAt: progress.updatedAt,
      resultUpdatedTime: progress.updatedTime,
      resultProgressKnown: progress.known,
      resultProgressLabel: progress.label,
      sortIndex: order,
      dogs: breedMatch ? breedDogs : matchingDogs,
    }
    order += 1
  }

  for (const dog of dogs) {
    const key = dogBreedGroupKey(dog)
    if (groups[key]) continue
    const breed = dog.breedObj || {}
    const breedDogs = dogsByBreed[key] || []
    const matchingDogs = q ? breedDogs.filter(item => dogMatchesShowSearch(item, q)) : breedDogs
    if (q && !matchingDogs.length) continue
    const progress = breedResultProgress(breed, breedDogs)
    groups[key] = {
      key,
      breed: { ...breed, has_results: true, can_fetch_results: true },
      breedName: dog.breedName || breed.name,
      count: breed.count,
      judge: breed.judge,
      has_results: true,
      canOpenResults: true,
      hasRatedResults: true,
      resultCount: progress.resultCount,
      resultTotalCount: progress.totalCount,
      resultUpdatedAt: progress.updatedAt,
      resultUpdatedTime: progress.updatedTime,
      resultProgressKnown: progress.known,
      resultProgressLabel: progress.label,
      sortIndex: order,
      dogs: matchingDogs,
    }
    order += 1
  }

  const values = Object.values(groups)
  if (resultsOnly) {
    values.sort((a, b) => {
      if (a.resultUpdatedTime !== b.resultUpdatedTime) {
        return b.resultUpdatedTime - a.resultUpdatedTime
      }
      return a.sortIndex - b.sortIndex
    })
  }
  return values
}

// FCI ryhmä names as used by the Finnish Kennel Club. The show index stores the
// group only as its number; the detail page maps it to a readable heading.
export const FCI_GROUP_NAMES = {
  '1': 'Lammas- ja karjakoirat',
  '2': 'Pinserit, snautserit, molossityyppiset ja sveitsinpaimenkoirat',
  '3': 'Terrierit',
  '4': 'Mäyräkoirat',
  '5': 'Pystykorvat ja alkukantaiset koirat',
  '6': 'Ajavat ja jäljestävät koirat',
  '7': 'Kanakoirat',
  '8': 'Noutajat, ylösajavat koirat ja vesikoirat',
  '9': 'Seura- ja kääpiökoirat',
  '10': 'Vinttikoirat',
}

export const SHOW_GROUP_MODES = ['fci', 'judge', 'alpha']

export function fciGroupLabel(group) {
  const key = String(group ?? '').trim()
  if (FCI_GROUP_NAMES[key]) return `Ryhmä ${key} – ${FCI_GROUP_NAMES[key]}`
  if (/^\d+$/.test(key)) return `Ryhmä ${key}`
  return 'Muu ryhmä'
}

function breedGroupFciKey(item) {
  return String(item?.breed?.group ?? '').trim()
}

function breedGroupJudge(item) {
  return String(item?.judge || item?.breed?.judge || '').trim()
}

function partitionBreedGroups(breedGroups, { keyOf, labelOf, missingLabel, compare }) {
  const sections = new Map()
  for (const item of breedGroups) {
    const key = keyOf(item)
    if (!sections.has(key)) {
      sections.set(key, {
        key: `section:${key || 'unknown'}`,
        rawKey: key,
        label: key ? labelOf(key) : missingLabel,
        missing: !key,
        breeds: [],
      })
    }
    sections.get(key).breeds.push(item)
  }

  return [...sections.values()]
    .sort((a, b) => {
      if (a.missing !== b.missing) return a.missing ? 1 : -1
      return compare(a, b)
    })
    .map(({ key, label, breeds }) => ({ key, label, breeds }))
}

function compareFciSections(a, b) {
  const an = Number(a.rawKey)
  const bn = Number(b.rawKey)
  const aNumeric = Number.isFinite(an)
  const bNumeric = Number.isFinite(bn)
  if (aNumeric && bNumeric) return an - bn
  if (aNumeric !== bNumeric) return aNumeric ? -1 : 1
  return String(a.rawKey).localeCompare(String(b.rawKey), 'fi')
}

// Wrap the flat breed-group list from createShowBreedGroups() into ordered
// sections for the show detail page. Breed order within a section is preserved
// (so the live "Tuloksia saaneet" recency sort still holds); only the section
// ordering is imposed. 'alpha' keeps the current single flat list.
export function groupShowBreedGroups(breedGroups = [], mode = 'fci') {
  if (!breedGroups.length) return []

  if (mode === 'alpha') {
    return [{ key: 'all', label: '', breeds: breedGroups }]
  }

  if (mode === 'judge') {
    return partitionBreedGroups(breedGroups, {
      keyOf: breedGroupJudge,
      labelOf: judge => judge,
      missingLabel: 'Tuomari ei tiedossa',
      compare: (a, b) => String(a.label).localeCompare(String(b.label), 'fi'),
    })
  }

  return partitionBreedGroups(breedGroups, {
    keyOf: breedGroupFciKey,
    labelOf: fciGroupLabel,
    missingLabel: 'Muu ryhmä',
    compare: compareFciSections,
  })
}

// Critique-expansion keys for the show-detail view. Kept here (not inlined in
// the components) so the rendered toggle and the "expand all" computation agree
// on the same key and can never drift apart.
export function showBreedGroupCritiqueKey(group, dog) {
  return `all-${group.key}-${dog.number || dog.name}`
}

export function showAwardCritiqueKey(group, dog) {
  return `show-award-${group.key}-${dog.breedGroup || dog.breedName || ''}-${dog.number || dog.name}`
}

export function splitAwards(value) {
  return (value || '').split(',').map(item => item.trim()).filter(Boolean)
}

const AWARD_GROUPS = [
  {
    value: 'BIS',
    matches: award => Boolean(parseBisAward(award)),
  },
  {
    value: 'RYP',
    matches: award => Boolean(parseRypAward(award)),
  },
  {
    value: 'ROP/VSP',
    matches: award => Boolean(parseRopVspAward(award)),
  },
]

const AWARD_FILTER_ORDER = [
  'BIS',
  'RYP',
  'ROP/VSP',
  'MVA',
  'VMVA',
  'JMVA',
  'SERT',
  'VET-SERT',
  'JUN-SERT',
  'VARA-SERT',
  'CACIB',
  'CACIB-J',
  'CACIB-V',
  'VARA-CACIB',
  'NORD SERT',
  'NORD VET-SERT',
  'NORD JUN-SERT',
  'NORD VARA-SERT',
  'SA',
  'KP',
]

const AWARD_QUALIFIER_ORDER = new Map([
  ['', 0],
  ['VET', 1],
  ['JUN', 2],
  ['PEN', 3],
])

function normalizeAward(award) {
  return String(award || '').replace(/\s+/g, ' ').trim().toUpperCase()
}

function qualifierOrder(qualifier) {
  return AWARD_QUALIFIER_ORDER.get(qualifier || '') ?? 99
}

function numericOrder(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number : 999
}

function categoryLabel(base, qualifier) {
  return qualifier ? `${base} ${qualifier}` : base
}

function parseRankedAward(award, base) {
  const match = normalizeAward(award).match(new RegExp(`^${base}(?:\\s+(JUN|VET|PEN))?-(\\d+)$`))
  if (!match) return null
  const rank = Number(match[2])
  if (!Number.isInteger(rank) || rank < 1 || rank > 4) return null
  const qualifier = match[1] || ''
  return {
    qualifier,
    rank,
    categoryOrder: qualifierOrder(qualifier),
    categoryLabel: categoryLabel(base, qualifier),
  }
}

function parseBisAward(award) {
  return parseRankedAward(award, 'BIS')
}

function parseRypAward(award) {
  return parseRankedAward(award, 'RYP')
}

function parseRopVspAward(award) {
  const normalized = normalizeAward(award)
  const prefixed = normalized.match(/^(JUN|VET|PEN)\s+(ROP|VSP)$/)
  if (prefixed) {
    const qualifier = prefixed[1]
    const result = prefixed[2]
    return {
      qualifier,
      result,
      categoryOrder: qualifierOrder(qualifier),
      categoryLabel: `${qualifier} ROP/VSP`,
      qualifierOrder: qualifierOrder(qualifier),
      resultOrder: result === 'ROP' ? 1 : 2,
    }
  }

  const plain = normalized.match(/^(ROP|VSP)(-PENTU)?$/)
  if (!plain) return null
  const qualifier = plain[2] ? 'PEN' : ''
  const result = plain[1]
  return {
    qualifier,
    result,
    categoryOrder: qualifierOrder(qualifier),
    categoryLabel: qualifier ? `${qualifier} ROP/VSP` : 'ROP/VSP',
    qualifierOrder: qualifierOrder(qualifier),
    resultOrder: result === 'ROP' ? 1 : 2,
  }
}

function awardGroupFor(award) {
  const normalized = normalizeAward(award)
  return AWARD_GROUPS.find(group => group.matches(normalized))?.value || ''
}

function awardDetailsForFilter(award, filter) {
  const normalizedFilter = normalizeAward(filter)
  const normalizedAward = normalizeAward(award)

  if (normalizedFilter === 'BIS') {
    const parsed = parseBisAward(normalizedAward)
    if (!parsed) return null
    return {
      categoryKey: `BIS:${parsed.qualifier || 'ALL'}`,
      categoryLabel: parsed.categoryLabel,
      categoryOrder: parsed.categoryOrder,
      categorySort: parsed.categoryLabel,
      sortRank: parsed.rank,
      subOrder: 0,
      displayRank: parsed.rank,
      resultOrder: 0,
      award: normalizedAward,
    }
  }

  if (normalizedFilter === 'ROP/VSP') {
    const parsed = parseRopVspAward(normalizedAward)
    if (!parsed) return null
    return {
      categoryKey: `ROP/VSP:${parsed.qualifier || 'ALL'}`,
      categoryLabel: parsed.categoryLabel,
      categoryOrder: parsed.categoryOrder,
      categorySort: parsed.categoryLabel,
      sortRank: parsed.qualifierOrder,
      subOrder: parsed.resultOrder,
      displayRank: null,
      resultOrder: parsed.resultOrder,
      award: normalizedAward,
    }
  }

  if (normalizedFilter === 'RYP') {
    const parsed = parseRypAward(normalizedAward)
    if (!parsed) return null
    return {
      categoryKey: `RYP:${parsed.qualifier || 'ALL'}`,
      categoryLabel: parsed.categoryLabel,
      categoryOrder: parsed.categoryOrder,
      categorySort: parsed.categoryLabel,
      sortRank: parsed.rank,
      subOrder: 0,
      displayRank: parsed.rank,
      resultOrder: 0,
      award: normalizedAward,
    }
  }

  if (normalizedAward !== normalizedFilter) return null
  return {
    categoryKey: normalizedFilter,
    categoryLabel: filter,
    categoryOrder: 0,
    categorySort: normalizedFilter,
    sortRank: null,
    subOrder: 0,
    displayRank: null,
    resultOrder: 0,
    award: normalizedAward,
  }
}

function awardDetailsForDog(details, dog, filter) {
  const normalizedFilter = normalizeAward(filter)
  if (normalizedFilter === 'RYP') {
    const group = String(dog?.breedGroup || dog?.breedObj?.group || '').trim()
    return {
      ...details,
      categoryKey: `RYP:${group || 'UNKNOWN'}`,
      categoryLabel: group ? `Ryhmä ${group}` : 'Ryhmä',
      categoryOrder: numericOrder(group),
      categorySort: group.padStart(3, '0'),
    }
  }

  if (normalizedFilter === 'ROP/VSP') {
    const breedName = dog?.breedName || dog?.breedObj?.name || 'Rotu'
    const group = String(dog?.breedGroup || dog?.breedObj?.group || '').trim()
    const key = dogBreedGroupKey(dog) || breedName
    return {
      ...details,
      categoryKey: `ROP/VSP:${key}`,
      categoryLabel: breedName,
      categoryOrder: numericOrder(group),
      categorySort: `${group.padStart(3, '0')}:${breedName.toLocaleLowerCase('fi')}`,
    }
  }

  return details
}

function compareAwardDetails(left, right) {
  if (!left && !right) return 0
  if (!left) return 1
  if (!right) return -1
  return (
    left.categoryOrder - right.categoryOrder
    || String(left.categorySort || '').localeCompare(String(right.categorySort || ''), 'fi')
    || (left.sortRank ?? 999) - (right.sortRank ?? 999)
    || (left.subOrder ?? 0) - (right.subOrder ?? 0)
    || left.resultOrder - right.resultOrder
    || left.award.localeCompare(right.award, 'fi')
  )
}

export function awardSortDetailsList(awards, filter) {
  if (!filter) return []
  return splitAwards(awards)
    .map(award => awardDetailsForFilter(award, filter))
    .filter(Boolean)
    .sort(compareAwardDetails)
}

export function awardSortDetails(awards, filter) {
  return awardSortDetailsList(awards, filter)?.[0] || null
}

export function awardMatchesFilter(awards, filter) {
  return Boolean(awardSortDetails(awards, filter))
}

function compareDogsByFallback(left, right) {
  const leftNumber = Number(left?.number)
  const rightNumber = Number(right?.number)
  return (
    String(left?.breedName || '').localeCompare(String(right?.breedName || ''), 'fi')
    || String(left?.class_name || '').localeCompare(String(right?.class_name || ''), 'fi')
    || String(left?.gender || '').localeCompare(String(right?.gender || ''), 'fi')
    || (Number.isFinite(leftNumber) ? leftNumber : 99999) - (Number.isFinite(rightNumber) ? rightNumber : 99999)
    || String(left?.name || '').localeCompare(String(right?.name || ''), 'fi')
  )
}

export function sortDogsByAwardFilter(results = [], filter = '') {
  if (!filter) return [...results]
  return [...results].sort((left, right) => (
    compareAwardDetails(awardSortDetails(left.awards, filter), awardSortDetails(right.awards, filter))
    || compareDogsByFallback(left, right)
  ))
}

// BIS JUN and BIS VET (junior / veteran Best in Show) are judged once per show day
// on a multi-day event, out of that day's breed groups — so a two-day show crowns
// two BIS JUN-1s, two BIS VET-1s, and so on. Showlink carries no per-result date,
// but catalog numbers run in ascending day-blocks (day 1 low, day 2 high), so each
// of those categories is split into per-day buckets by clustering catalog numbers.
// The day count comes from how many times the top placement repeats (two "rank 1"s
// ⇒ two rings ⇒ two days), which is steadier than guessing a gap threshold. Main
// BIS and group RYP are intentionally left grouped.
const PER_DAY_FINALS_CATEGORY_KEYS = new Set(['BIS:JUN', 'BIS:VET'])

function clusterFinalsEntriesByDay(entries) {
  const rankCounts = new Map()
  entries.forEach((entry) => {
    const rank = entry.details.displayRank
    if (rank != null) rankCounts.set(rank, (rankCounts.get(rank) || 0) + 1)
  })
  const dayCount = Math.max(1, ...rankCounts.values())
  if (dayCount <= 1) return [entries]

  const numberOf = (entry) => {
    const value = Number(entry.dog?.number)
    return Number.isFinite(value) ? value : Infinity
  }
  const sorted = [...entries].sort((left, right) => numberOf(left) - numberOf(right))

  // Cut at the largest (dayCount - 1) gaps between consecutive catalog numbers.
  const gaps = []
  for (let i = 1; i < sorted.length; i += 1) {
    const prev = numberOf(sorted[i - 1])
    const cur = numberOf(sorted[i])
    if (Number.isFinite(prev) && Number.isFinite(cur)) {
      gaps.push({ index: i, size: cur - prev })
    }
  }
  gaps.sort((left, right) => right.size - left.size || left.index - right.index)
  const cutIndices = new Set(gaps.slice(0, dayCount - 1).map((gap) => gap.index))

  const clusters = [[]]
  sorted.forEach((entry, index) => {
    if (cutIndices.has(index)) clusters.push([])
    clusters[clusters.length - 1].push(entry)
  })
  return clusters
}

function splitPerDayFinals(entries) {
  const byCategory = new Map()
  entries.forEach((entry) => {
    const key = entry.details.categoryKey
    if (!PER_DAY_FINALS_CATEGORY_KEYS.has(key)) return
    if (!byCategory.has(key)) byCategory.set(key, [])
    byCategory.get(key).push(entry)
  })

  byCategory.forEach((categoryEntries) => {
    const days = clusterFinalsEntriesByDay(categoryEntries)
    if (days.length <= 1) return
    days.forEach((dayEntries, dayIndex) => {
      const day = dayIndex + 1
      dayEntries.forEach((entry) => {
        entry.details = {
          ...entry.details,
          categoryKey: `${entry.details.categoryKey}:day${day}`,
          categoryLabel: `${entry.details.categoryLabel} (${day}. päivä)`,
          categorySort: `${entry.details.categorySort}:${String(day).padStart(2, '0')}`,
        }
      })
    })
  })
}

export function groupResultsByAwardFilter(results = [], filter = '') {
  if (!filter) return []
  const groups = new Map()
  const entries = []
  results.forEach((dog) => {
    const seenCategories = new Set()
    awardSortDetailsList(dog.awards, filter).forEach((details) => {
      const dogDetails = awardDetailsForDog(details, dog, filter)
      if (seenCategories.has(dogDetails.categoryKey)) return
      seenCategories.add(dogDetails.categoryKey)
      entries.push({ dog, details: dogDetails })
    })
  })

  if (normalizeAward(filter) === 'BIS') splitPerDayFinals(entries)

  entries.sort((left, right) => (
    compareAwardDetails(left.details, right.details)
    || compareDogsByFallback(left.dog, right.dog)
  ))

  entries.forEach(({ dog, details }) => {
    if (!groups.has(details.categoryKey)) {
      groups.set(details.categoryKey, {
        key: details.categoryKey,
        label: details.categoryLabel,
        order: details.categoryOrder,
        dogs: [],
      })
    }
    groups.get(details.categoryKey).dogs.push({
      ...dog,
      awardRank: details.displayRank,
      awardSortAward: details.award,
    })
  })
  return [...groups.values()]
}

const CLASS_ORDER = [
  'Pentuluokka',
  'Junioriluokka',
  'Nuorten luokka',
  'Avoin luokka',
  'Käyttöluokka',
  'Valioluokka',
  'Veteraaniluokka',
  'Kasvattajaluokka',
]

function classOrderIndex(className) {
  const idx = CLASS_ORDER.findIndex(prefix => className.startsWith(prefix))
  return idx === -1 ? CLASS_ORDER.length : idx
}

export function availableClassesFromResults(results = []) {
  const classes = results.map(result => result.class_name).filter(Boolean)
  return [...new Set(classes)].sort((a, b) => {
    const aOrder = classOrderIndex(a)
    const bOrder = classOrderIndex(b)
    return aOrder !== bOrder
      ? aOrder - bOrder
      : a.localeCompare(b, 'fi')
  })
}

export function availableGradesFromResults(results = []) {
  const counts = new Map()
  for (const dog of results) {
    if (!normalizeGrade(dog.grade)) continue
    for (const option of DOG_GRADE_OPTIONS) {
      if (option.value && gradeMatchesFilter(dog.grade, option.value)) {
        counts.set(option.value, (counts.get(option.value) || 0) + 1)
      }
    }
  }
  // Always expose every grade, annotated with how many dogs received it. The "all"
  // option carries no count; zero-count grades stay listed (greyed out in the UI).
  return DOG_GRADE_OPTIONS.map(option => ({
    ...option,
    count: option.value ? (counts.get(option.value) || 0) : null,
  }))
}

export function gradeOptionLabel(option) {
  if (!option || option.count == null) return option?.label || ''
  return `${option.label} — ${option.count}`
}

export function availableAwardsFromResults(results = []) {
  const awardsSet = new Set()
  results.forEach(result => {
    splitAwards(result.awards).forEach((award) => {
      awardsSet.add(awardGroupFor(award) || award)
    })
  })
  const awardOrder = new Map(AWARD_FILTER_ORDER.map((award, index) => [award, index]))
  return [...awardsSet].sort((left, right) => {
    const leftOrder = awardOrder.get(left)
    const rightOrder = awardOrder.get(right)
    if (leftOrder !== undefined || rightOrder !== undefined) {
      if (leftOrder === undefined) return 1
      if (rightOrder === undefined) return -1
      return leftOrder - rightOrder
    }
    return left.localeCompare(right, 'fi')
  })
}

export function filterDogResults(results = [], filters = {}) {
  const search = String(filters.search || '').toLowerCase().trim()
  const grade = String(filters.grade || '').toLowerCase().trim()
  const className = String(filters.className || '').trim()
  const award = String(filters.award || '').trim()

  const filtered = results.filter(dog => {
    if (search) {
      const nameMatch = dog.name?.toLowerCase().includes(search)
      const numMatch = String(dog.number).includes(search)
      if (!nameMatch && !numMatch) return false
    }

    if (grade && !gradeMatchesFilter(dog.grade, grade)) return false
    if (className && dog.class_name !== className) return false
    if (award && !awardMatchesFilter(dog.awards, award)) return false

    return true
  })
  return sortDogsByAwardFilter(filtered, award)
}

export function groupResultsByGenderAndClass(results = []) {
  const groups = {}
  for (const result of results) {
    const gender = result.gender || 'Muu'
    const className = result.class_name || 'Luokka'
    if (!groups[gender]) groups[gender] = {}
    if (!groups[gender][className]) groups[gender][className] = []
    groups[gender][className].push(result)
  }
  return groups
}

export function gradeClasses(grade) {
  if (!grade) return 'dog-badge-default'
  const value = normalizeGrade(grade)
  if (value === 'eri' || value === 'erinomainen') return 'dog-badge-gold'
  if (value === 'eh' || value === 'erittäin hyvä') return 'dog-badge-silver'
  if (value === 'h' || value === 'hyvä') return 'dog-badge-bronze'
  if (value === 'kp') return 'dog-badge-info'
  if (value === 'poissa' || value === 'hyl' || value === 'hylätty' || value === 'eva' || value === 'ei voida arvostella') return 'dog-badge-muted'
  return 'dog-badge-default'
}

export function gradeBorderClass(grade) {
  if (!grade) return 'dog-border-default'
  const value = normalizeGrade(grade)
  if (value === 'eri' || value === 'erinomainen') return 'dog-border-gold'
  if (value === 'eh' || value === 'erittäin hyvä') return 'dog-border-silver'
  if (value === 'h' || value === 'hyvä') return 'dog-border-bronze'
  if (value === 'kp') return 'dog-border-info'
  if (value === 'poissa' || value === 'hyl' || value === 'hylätty' || value === 'eva' || value === 'ei voida arvostella') return 'dog-border-muted'
  return 'dog-border-default'
}

export function formatStatNumber(value) {
  if (typeof value !== 'number') return ''
  return new Intl.NumberFormat('fi-FI').format(value)
}

export function showStatItems(show) {
  const stats = show?.stats || {}
  const items = []
  if (stats.is_live) {
    items.push({
      key: 'live',
      label: 'Käynnissä',
      live: true,
    })
  } else if (stats.is_paused) {
    items.push({
      key: 'paused',
      label: 'Jatkuu',
      paused: true,
    })
  }
  if (typeof stats.breed_count === 'number') {
    items.push({
      key: 'breeds',
      label: `${formatStatNumber(stats.breed_count)} rotua`,
    })
  }
  if (typeof stats.entry_count === 'number') {
    if ((stats.is_live || stats.is_paused) && typeof stats.result_count === 'number') {
      items.push({
        key: 'entries',
        label: `${formatStatNumber(stats.result_count)}/${formatStatNumber(stats.entry_count)} tulosta`,
        title: `${formatStatNumber(stats.result_count)}/${formatStatNumber(stats.entry_count)} arvosteltua ilmoittautuneesta`,
      })
      return items
    }
    items.push({
      key: 'entries',
      label: `${formatStatNumber(stats.entry_count)} koiraa`,
      title: `${formatStatNumber(stats.entry_count)} ilmoittautunutta`,
    })
  }
  return items
}

export function hasShowStats(show) {
  return showStatItems(show).length > 0
}

export function showStatsLabel(show) {
  const stats = show?.stats || {}
  const parts = []
  if (stats.is_live) parts.push('käynnissä')
  else if (stats.is_paused) parts.push('jatkuu')
  if (typeof stats.breed_count === 'number') parts.push(`${formatStatNumber(stats.breed_count)} rotua`)
  if (typeof stats.entry_count === 'number') {
    if ((stats.is_live || stats.is_paused) && typeof stats.result_count === 'number') {
      parts.push(`${formatStatNumber(stats.result_count)}/${formatStatNumber(stats.entry_count)} tulosta`)
    } else {
      parts.push(`${formatStatNumber(stats.entry_count)} ilmoittautunutta`)
    }
  }
  return parts.join(', ')
}

export function formatShowDay(dateStr) {
  const match = String(dateStr || '').match(/\d{1,2}/)
  if (!match) return dateStr || ''
  return String(parseInt(match[0], 10))
}

const FINNISH_MONTHS_SHORT = [
  'tammi', 'helmi', 'maalis', 'huhti', 'touko', 'kesä',
  'heinä', 'elo', 'syys', 'loka', 'marras', 'joulu',
]

// Calendar-box parts for a list row: a single day ("13") or a same-month range
// ("13–14"). Cross-month ranges (a rare month-boundary weekend) fall back to the
// start day so the small square stays readable.
export function showDateBadgeParts(show) {
  const dateStr = show?.date || ''
  const range = parseShowDateRange(dateStr, show?.month)
  if (!range?.start) {
    return { day: formatShowDay(dateStr), month: '' }
  }

  const { start, end } = range
  const startMonth = FINNISH_MONTHS_SHORT[start.getMonth()] || ''
  if (!end || datesAreSameDay(start, end)) {
    return { day: String(start.getDate()), month: startMonth }
  }
  if (start.getMonth() === end.getMonth()) {
    return { day: `${start.getDate()}–${end.getDate()}`, month: startMonth, range: true }
  }
  return { day: String(start.getDate()), month: startMonth }
}

function formatDatePart(date, includeYear = false) {
  const day = String(date.getDate()).padStart(2, '0')
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const year = date.getFullYear()
  return includeYear ? `${day}.${month}.${year}` : `${day}.${month}.`
}

function datesAreSameDay(left, right) {
  return (
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate()
  )
}

export function formatShowFullDate(show) {
  const rawDate = show?.date || ''
  const range = parseShowDateRange(rawDate, show?.month)
  if (!range?.start || !range?.end) return rawDate

  if (datesAreSameDay(range.start, range.end)) {
    return formatDatePart(range.end, true)
  }

  if (range.start.getFullYear() !== range.end.getFullYear()) {
    return `${formatDatePart(range.start, true)}–${formatDatePart(range.end, true)}`
  }

  if (range.start.getMonth() === range.end.getMonth()) {
    return `${String(range.start.getDate()).padStart(2, '0')}.–${formatDatePart(range.end, true)}`
  }

  return `${formatDatePart(range.start)}–${formatDatePart(range.end, true)}`
}

export function isThisWeekLeft(showDate, now = new Date()) {
  if (!showDate) return false
  const today = new Date(now)
  today.setHours(0, 0, 0, 0)
  const currentDayOfWeek = today.getDay()
  const daysToSunday = currentDayOfWeek === 0 ? 0 : 7 - currentDayOfWeek
  const sunday = new Date(today)
  sunday.setDate(today.getDate() + daysToSunday)
  sunday.setHours(23, 59, 59, 999)
  return showDate >= today && showDate <= sunday
}

const FINNISH_MONTHS = [
  'tammikuu', 'helmikuu', 'maaliskuu', 'huhtikuu', 'toukokuu', 'kesäkuu',
  'heinäkuu', 'elokuu', 'syyskuu', 'lokakuu', 'marraskuu', 'joulukuu',
]

function yearFromMonthLabel(monthLabel) {
  const match = String(monthLabel || '').match(/\b(\d{4})\b/)
  return match ? parseInt(match[1], 10) : null
}

function dateFromParts(year, month, day) {
  if (!year || !month || !day) return null
  const date = new Date(year, month - 1, day)
  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day
  ) {
    return null
  }
  date.setHours(0, 0, 0, 0)
  return date
}

export function parseShowDateRange(dateStr, monthLabel = '', fallbackYear = new Date().getFullYear()) {
  const value = String(dateStr || '').trim()
  if (!value) return null

  let match = value.match(/(\d{1,2})\.(\d{1,2})\.\s*-\s*(\d{1,2})\.(\d{1,2})\.?(?:(\d{4}))?/)
  if (match) {
    const [, startDay, startMonth, endDay, endMonth, explicitYear] = match
    const year = parseInt(explicitYear, 10) || yearFromMonthLabel(monthLabel) || fallbackYear
    const startYear = parseInt(startMonth, 10) > parseInt(endMonth, 10) ? year - 1 : year
    return {
      start: dateFromParts(startYear, parseInt(startMonth, 10), parseInt(startDay, 10)),
      end: dateFromParts(year, parseInt(endMonth, 10), parseInt(endDay, 10)),
    }
  }

  match = value.match(/(\d{1,2})\.\s*-\s*(\d{1,2})\.(\d{1,2})\.?(?:(\d{4}))?/)
  if (match) {
    const [, startDay, endDay, month, explicitYear] = match
    const year = parseInt(explicitYear, 10) || yearFromMonthLabel(monthLabel) || fallbackYear
    return {
      start: dateFromParts(year, parseInt(month, 10), parseInt(startDay, 10)),
      end: dateFromParts(year, parseInt(month, 10), parseInt(endDay, 10)),
    }
  }

  match = value.match(/(\d{1,2})\.(\d{1,2})\.?(?:(\d{4}))?/)
  if (!match) return null

  const [, day, month, explicitYear] = match
  const year = parseInt(explicitYear, 10) || yearFromMonthLabel(monthLabel) || fallbackYear
  const date = dateFromParts(year, parseInt(month, 10), parseInt(day, 10))
  return date ? { start: date, end: date } : null
}

export function parseShowDate(dateStr, monthLabel = '') {
  return parseShowDateRange(dateStr, monthLabel)?.end || null
}

function endOfDay(date) {
  if (!date) return null
  const copy = new Date(date)
  copy.setHours(23, 59, 59, 999)
  return copy
}

export const RESULT_MORNING_HOUR = 6
export const RESULT_EVENING_HOUR = 21

// True during the overnight quiet window (default 21:00–06:00 local) when a
// live show is not producing results, so the frontend can pause periodic
// live polling. Mirrors the backend fetch gate in app/dog_show/utils.py.
export function isOvernightResultWindow(
  now = new Date(),
  morningHour = RESULT_MORNING_HOUR,
  eveningHour = RESULT_EVENING_HOUR,
) {
  const hour = now.getHours()
  return hour < morningHour || hour >= eveningHour
}

export function getShowResultAvailability(show, now = new Date(), morningHour = 6) {
  const range = parseShowDateRange(show?.date, show?.month, now.getFullYear())
  if (!range?.start || !range?.end) {
    return {
      canLoad: true,
      phase: 'unknown',
      actionLabel: 'Suodata koko näyttelyä',
      loadingNote: 'Ensimmäinen haku voi kestää, koska rotujen tulossivut haetaan taustalla rauhallisesti.',
    }
  }

  const availableFrom = new Date(range.start)
  availableFrom.setHours(morningHour, 0, 0, 0)
  const end = endOfDay(range.end)

  if (now < availableFrom) {
    const sameDate = now.toDateString() === range.start.toDateString()
    return {
      canLoad: false,
      phase: sameDate ? 'show_morning' : 'upcoming',
      title: sameDate ? 'Tuloksia odotetaan' : 'Tuloksia ei haeta vielä',
      message: sameDate
        ? `Koko näyttelyn tuloksia tarkistetaan klo ${morningHour} jälkeen. Rotuluettelo on jo selattavissa.`
        : `Koko näyttelyn tuloksia tarkistetaan aikaisintaan näyttelypäivänä klo ${morningHour}. Rotuluettelo on jo selattavissa.`,
      availableFrom,
    }
  }

  if (now <= end) {
    return {
      canLoad: true,
      phase: 'show_day',
      actionLabel: 'Tarkista koirat ja tulokset',
      note: 'Näyttelypäivänä luokat ja tulokset voivat täydentyä vaiheittain päivän edetessä.',
      loadingNote: 'Näyttelypäivänä välimuisti voi täydentyä vaiheittain sitä mukaa kun Showlink julkaisee tietoja.',
    }
  }

  return {
    canLoad: true,
    phase: 'past',
    actionLabel: 'Suodata koko näyttelyä',
    loadingNote: 'Ensimmäinen haku voi kestää, koska rotujen tulossivut haetaan taustalla rauhallisesti.',
  }
}

export function getCurrentMonthLabel(now = new Date()) {
  return `${FINNISH_MONTHS[now.getMonth()]} ${now.getFullYear()}`
}

export function shouldCollapseMonth(monthLabel, now = new Date()) {
  if (!monthLabel) return false
  const month = monthLabel.toLowerCase().trim()
  if (month === 'tänään' || month === 'tällä viikolla') return false
  return month !== getCurrentMonthLabel(now).toLowerCase().trim()
}

export function formatTimestamp(value) {
  if (!value) return ''
  const date = typeof value === 'number' ? new Date(value * 1000) : new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat('fi-FI', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date)
}

export function sourceForShow(show) {
  return show?.source_url || (show?.id ? `https://tulospalvelu.kennelliitto.fi/nayttelyt/Tulokset?Id=${show.id}` : '')
}

export function getAllDogsProgressPercent(progress) {
  const percent = progress?.percent
  return typeof percent === 'number' ? Math.max(0, Math.min(100, percent)) : null
}

export function getAllDogsProgressText(progress) {
  if (!progress) return 'Tarkistetaan välimuistia...'
  const fetched = progress.fetched_breeds ?? 0
  const total = progress.total_breeds
  const dogs = progress.total_dogs ?? 0
  const state = progress.state === 'running' ? 'Haetaan tuloksia' : 'Tulokset jonossa'
  if (total) {
    return `${state}: ${fetched}/${total} rotua, ${dogs} koiraa välimuistissa.`
  }
  return `${state}. Taustaprosessi hakee tiedot rauhallisesti.`
}

function getAwardFilterKey(norm) {
  if (norm.includes('BIS')) return 'BIS'
  if (norm.includes('RYP')) return 'RYP'
  
  if (norm.includes('ROP') || norm.includes('VSP')) {
    return 'ROP/VSP'
  }

  if (norm.includes('JMVA')) return 'JMVA'
  if (norm.includes('VMVA')) return 'VMVA'
  if (norm.includes('MVA')) return 'MVA'

  if (norm.includes('SERT')) {
    if (norm.includes('VET')) {
      if (norm.includes('NORD')) return 'NORD VET-SERT'
      return 'VET-SERT'
    }
    if (norm.includes('JUN')) {
      if (norm.includes('NORD')) return 'NORD JUN-SERT'
      return 'JUN-SERT'
    }
    if (norm.includes('VARA')) {
      if (norm.includes('NORD')) return 'NORD VARA-SERT'
      return 'VARA-SERT'
    }
    if (norm.includes('NORD')) return 'NORD SERT'
    return 'SERT'
  }

  if (norm.includes('CACIB')) {
    if (norm.includes('CACIB-J') || norm.includes('CACIB J') || norm.includes('JUN')) return 'CACIB-J'
    if (norm.includes('CACIB-V') || norm.includes('CACIB V') || norm.includes('VET')) return 'CACIB-V'
    if (norm.includes('VARA')) return 'VARA-CACIB'
    return 'CACIB'
  }

  if (norm.includes('NORD')) {
    if (norm.includes('VET')) return 'NORD VET-SERT'
    if (norm.includes('JUN')) return 'NORD JUN-SERT'
    if (norm.includes('VARA')) return 'NORD VARA-SERT'
    return 'NORD SERT'
  }

  const tokens = norm.split(/[\s-]+/)
  if (tokens.includes('SA')) return 'SA'
  if (tokens.includes('KP')) return 'KP'

  return null
}

function parseBreedAwardForSort(type) {
  const norm = String(type || '').trim().toUpperCase()
  const genderSort = norm.includes('NARTTU') ? 2 : 1

  const filterKey = getAwardFilterKey(norm)
  const groupOrder = filterKey ? AWARD_FILTER_ORDER.indexOf(filterKey) : 99

  // For ROP/VSP variations, we apply specific sub-orderings
  const isRop = norm.includes('ROP')
  const isVsp = norm.includes('VSP')
  if (isRop || isVsp) {
    const resultOrder = isRop ? 1 : 2
    let qualifierOrder = 0

    if (norm.includes('KASVATTAJA')) {
      qualifierOrder = 4
    } else if (norm.includes('JÄLKELÄIS') || norm.includes('JALKELAIS')) {
      qualifierOrder = 5
    } else if (norm.includes('VETERAANI') || norm.includes('VET')) {
      qualifierOrder = 1
    } else if (norm.includes('JUNIORI') || norm.includes('JUN')) {
      qualifierOrder = 2
    } else if (norm.includes('PENTU') || norm.includes('PEN')) {
      qualifierOrder = 3
    }

    return { groupOrder, qualifierOrder, subOrder: resultOrder }
  }

  // BIS and RYP should parse rank as subOrder
  if (filterKey === 'BIS') {
    const match = norm.match(/BIS\s*-?\s*(\d+)/)
    const rank = match ? parseInt(match[1], 10) : 99
    return { groupOrder, qualifierOrder: 0, subOrder: rank }
  }
  if (filterKey === 'RYP') {
    const match = norm.match(/RYP\s*-?\s*(\d+)/)
    const rank = match ? parseInt(match[1], 10) : 99
    return { groupOrder, qualifierOrder: 0, subOrder: rank }
  }

  // Other awards sort by genderSort as subOrder
  return { groupOrder, qualifierOrder: 0, subOrder: genderSort }
}

export function sortBreedAwards(awards) {
  if (!Array.isArray(awards)) return []
  return [...awards].sort((left, right) => {
    const l = parseBreedAwardForSort(left.type)
    const r = parseBreedAwardForSort(right.type)
    
    return (
      l.groupOrder - r.groupOrder
      || l.qualifierOrder - r.qualifierOrder
      || l.subOrder - r.subOrder
      || String(left.type || '').localeCompare(String(right.type || ''), 'fi')
    )
  })
}
