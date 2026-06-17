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

  const award = String(filters.award || '').toLowerCase().trim()
  if (award && !(dog.awards || '').toLowerCase().includes(award)) return false

  return true
}

export function createShowBreedGroups({
  breeds = [],
  dogs = [],
  query = '',
  allDogsLoaded = false,
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
  for (const breed of breeds) {
    const key = breedGroupKey(breed)
    const breedDogs = dogsByBreed[key] || []
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

    groups[key] = {
      key,
      breed,
      breedName: breed.name,
      count: breed.count,
      judge: breed.judge,
      has_results: breed.has_results,
      dogs: breedMatch ? breedDogs : matchingDogs,
    }
  }

  for (const dog of dogs) {
    const key = dogBreedGroupKey(dog)
    if (groups[key]) continue
    const breed = dog.breedObj || {}
    const breedDogs = dogsByBreed[key] || []
    const matchingDogs = q ? breedDogs.filter(item => dogMatchesShowSearch(item, q)) : breedDogs
    if (q && !matchingDogs.length) continue
    groups[key] = {
      key,
      breed: { ...breed, has_results: true },
      breedName: dog.breedName || breed.name,
      count: breed.count,
      judge: breed.judge,
      has_results: true,
      dogs: matchingDogs,
    }
  }

  return Object.values(groups)
}

export function splitAwards(value) {
  return (value || '').split(',').map(item => item.trim()).filter(Boolean)
}

export function availableClassesFromResults(results = []) {
  const classes = results.map(result => result.class_name).filter(Boolean)
  return [...new Set(classes)].sort()
}

export function availableAwardsFromResults(results = []) {
  const awardsSet = new Set()
  results.forEach(result => {
    splitAwards(result.awards).forEach(award => awardsSet.add(award))
  })
  return [...awardsSet].sort()
}

export function filterDogResults(results = [], filters = {}) {
  const search = String(filters.search || '').toLowerCase().trim()
  const grade = String(filters.grade || '').toLowerCase().trim()
  const className = String(filters.className || '').trim()
  const award = String(filters.award || '').trim()

  return results.filter(dog => {
    if (search) {
      const nameMatch = dog.name?.toLowerCase().includes(search)
      const numMatch = String(dog.number).includes(search)
      if (!nameMatch && !numMatch) return false
    }

    if (grade && !gradeMatchesFilter(dog.grade, grade)) return false
    if (className && dog.class_name !== className) return false
    if (award && !splitAwards(dog.awards).map(item => item.toLowerCase()).includes(award.toLowerCase())) return false

    return true
  })
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
  }
  if (typeof stats.breed_count === 'number') {
    items.push({
      key: 'breeds',
      label: `${formatStatNumber(stats.breed_count)} rotua`,
    })
  }
  if (typeof stats.entry_count === 'number') {
    if (stats.is_live && typeof stats.result_count === 'number') {
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
  if (typeof stats.breed_count === 'number') parts.push(`${formatStatNumber(stats.breed_count)} rotua`)
  if (typeof stats.entry_count === 'number') {
    if (stats.is_live && typeof stats.result_count === 'number') {
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
