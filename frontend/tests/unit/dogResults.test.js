import { describe, expect, it } from 'vitest'
import {
  availableAwardsFromResults,
  availableGradesFromResults,
  gradeOptionLabel,
  awardMatchesFilter,
  buildDogQuery,
  createShowBreedGroups,
  dogMatchesShowFilters,
  fciGroupLabel,
  filterDogResults,
  formatShowFullDate,
  getShowResultAvailability,
  gradeMatchesFilter,
  groupResultsByAwardFilter,
  groupShowBreedGroups,
  isOvernightResultWindow,
  parseShowDateRange,
  showAwardCritiqueKey,
  showBreedGroupCritiqueKey,
  showDateBadgeParts,
  showStatItems,
  showStatsLabel,
  sortBreedAwards,
} from '~/features/dog/dogResults.js'

describe('gradeMatchesFilter', () => {
  it('keeps HYL, EVA, and POISSA as separate filters', () => {
    expect(gradeMatchesFilter('HYL', 'hyl')).toBe(true)
    expect(gradeMatchesFilter('Hylätty', 'hyl')).toBe(true)
    expect(gradeMatchesFilter('EVA', 'hyl')).toBe(false)
    expect(gradeMatchesFilter('POISSA', 'hyl')).toBe(false)

    expect(gradeMatchesFilter('Ei voida arvostella', 'eva')).toBe(true)
    expect(gradeMatchesFilter('HYL', 'eva')).toBe(false)
    expect(gradeMatchesFilter('POISSA', 'eva')).toBe(false)

    expect(gradeMatchesFilter('POISSA', 'poissa')).toBe(true)
    expect(gradeMatchesFilter('EVA', 'poissa')).toBe(false)
  })
})

describe('availableGradesFromResults', () => {
  it('returns every grade with its count, keeping HYL/EVA/POISSA distinct and "all" first', () => {
    const options = availableGradesFromResults([
      { grade: 'ERI' },
      { grade: 'ERI' },
      { grade: 'EH' },
      { grade: 'HYL' },
      { grade: '' },
    ])
    expect(options.map(option => option.value)).toEqual([
      '', 'eri', 'eh', 'h', 't', 'kp', 'hyl', 'eva', 'poissa',
    ])
    const byValue = Object.fromEntries(options.map(option => [option.value, option.count]))
    expect(byValue['']).toBeNull()
    expect(byValue.eri).toBe(2)
    expect(byValue.eh).toBe(1)
    expect(byValue.hyl).toBe(1)
    expect(byValue.h).toBe(0)
    expect(byValue.poissa).toBe(0)
  })

  it('returns all grades with zero counts for empty results', () => {
    const options = availableGradesFromResults([])
    expect(options.map(option => option.value)).toEqual([
      '', 'eri', 'eh', 'h', 't', 'kp', 'hyl', 'eva', 'poissa',
    ])
    expect(options.filter(option => option.value).every(option => option.count === 0)).toBe(true)
  })
})

describe('gradeOptionLabel', () => {
  it('appends the count when present and leaves the "all" option bare', () => {
    expect(gradeOptionLabel({ label: 'ERI (Erinomainen)', count: 80 })).toBe('ERI (Erinomainen) — 80')
    expect(gradeOptionLabel({ label: 'Kaikki arvostelut', count: null })).toBe('Kaikki arvostelut')
  })
})

describe('award filters', () => {
  const results = [
    {
      name: 'A',
      awards: 'SA, ROP, JUN ROP, VET VSP, BIS-3, BIS JUN-2, BIS VET-4, RYP-1, RYP-4',
    },
    {
      name: 'B',
      awards: 'SERT, JUN-SERT, VET-SERT, VARA-SERT, MVA, JMVA, VMVA',
    },
  ]

  it('groups award filters and orders the menu options by show priority', () => {
    const awards = availableAwardsFromResults(results)

    expect(awards).toEqual([
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
      'SA',
    ])
    expect(awards).toEqual(expect.arrayContaining([
      'JMVA',
      'JUN-SERT',
      'MVA',
      'SERT',
      'VARA-SERT',
      'VET-SERT',
      'VMVA',
    ]))
    expect(awards).not.toEqual(expect.arrayContaining([
      'BIS JUN-2',
      'BIS VET-4',
      'JUN ROP',
      'ROP',
      'RYP-1',
      'VET VSP',
    ]))
  })

  it('orders CACIB variants after SERT variants in an international show', () => {
    const internationalResults = [
      { name: 'A', awards: 'BIS-1, ROP, SERT, JUN-SERT, VET-SERT, VARA-SERT, CACIB, CACIB-J, CACIB-V, VARA-CACIB, SA' },
    ]
    const awards = availableAwardsFromResults(internationalResults)
    expect(awards).toEqual([
      'BIS',
      'ROP/VSP',
      'SERT',
      'VET-SERT',
      'JUN-SERT',
      'VARA-SERT',
      'CACIB',
      'CACIB-J',
      'CACIB-V',
      'VARA-CACIB',
      'SA',
    ])
  })

  it('orders NORD cert variants after SERT variants in a Nordic show', () => {
    const nordicResults = [
      { name: 'A', awards: 'BIS-1, ROP, SERT, JUN-SERT, VET-SERT, VARA-SERT, NORD SERT, NORD VET-SERT, NORD JUN-SERT, NORD VARA-SERT, SA' },
    ]
    const awards = availableAwardsFromResults(nordicResults)
    expect(awards).toEqual([
      'BIS',
      'ROP/VSP',
      'SERT',
      'VET-SERT',
      'JUN-SERT',
      'VARA-SERT',
      'NORD SERT',
      'NORD VET-SERT',
      'NORD JUN-SERT',
      'NORD VARA-SERT',
      'SA',
    ])
  })

  it('matches grouped awards while keeping MVA and SERT variants exact', () => {
    expect(awardMatchesFilter('SA, BIS JUN-2', 'BIS')).toBe(true)
    expect(awardMatchesFilter('SA, BIS VET-4', 'BIS')).toBe(true)
    expect(awardMatchesFilter('SA, ROP-pentu', 'ROP/VSP')).toBe(true)
    expect(awardMatchesFilter('SA, VET VSP', 'ROP/VSP')).toBe(true)
    expect(awardMatchesFilter('SA, RYP-4', 'RYP')).toBe(true)

    expect(awardMatchesFilter('SA, JMVA', 'MVA')).toBe(false)
    expect(awardMatchesFilter('SA, SMVA', 'MVA')).toBe(false)
    expect(awardMatchesFilter('SA, MVA', 'MVA')).toBe(true)

    expect(awardMatchesFilter('SA, JUN-SERT', 'SERT')).toBe(false)
    expect(awardMatchesFilter('SA, VET-SERT', 'SERT')).toBe(false)
    expect(awardMatchesFilter('SA, VARA-SERT', 'SERT')).toBe(false)
    expect(awardMatchesFilter('SA, SERT', 'SERT')).toBe(true)
  })

  it('uses the same award matching for breed and whole-show filters', () => {
    const dogs = [
      { name: 'BIS dog', awards: 'BIS JUN-1' },
      { name: 'Champion dog', awards: 'JMVA' },
      { name: 'Certificate dog', awards: 'JUN-SERT' },
      { name: 'Plain certificate dog', awards: 'SERT' },
    ]

    expect(filterDogResults(dogs, { award: 'BIS' }).map(dog => dog.name)).toEqual(['BIS dog'])
    expect(filterDogResults(dogs, { award: 'SERT' }).map(dog => dog.name)).toEqual(['Plain certificate dog'])
    expect(dogMatchesShowFilters(dogs[1], { award: 'MVA' })).toBe(false)
    expect(dogMatchesShowFilters(dogs[2], { award: 'SERT' })).toBe(false)
  })

  it('groups award-filtered results by category and orders ranked awards by placement', () => {
    const dogs = [
      { name: 'Vet three', awards: 'BIS VET-3', number: 5 },
      { name: 'Open four', awards: 'BIS-4', number: 4 },
      { name: 'Junior two', awards: 'BIS JUN-2', number: 3 },
      { name: 'Open one', awards: 'BIS-1', number: 2 },
      { name: 'Vet one', awards: 'BIS VET-1', number: 1 },
    ]

    const groups = groupResultsByAwardFilter(dogs, 'BIS')

    expect(groups.map(group => group.label)).toEqual(['BIS', 'BIS VET', 'BIS JUN'])
    expect(groups[0].dogs.map(dog => dog.name)).toEqual(['Open one', 'Open four'])
    expect(groups[0].dogs.map(dog => dog.awardRank)).toEqual([1, 4])
    expect(groups[1].dogs.map(dog => dog.name)).toEqual(['Vet one', 'Vet three'])
    expect(groups[1].dogs.map(dog => dog.awardRank)).toEqual([1, 3])
    expect(groups[2].dogs.map(dog => dog.name)).toEqual(['Junior two'])
    expect(filterDogResults(dogs, { award: 'BIS' }).map(dog => dog.name)).toEqual([
      'Open one',
      'Open four',
      'Vet one',
      'Vet three',
      'Junior two',
    ])
  })

  it('splits BIS JUN and BIS VET into per-day groups by catalog number on a multi-day show', () => {
    const dogs = [
      // Day 1 finals carry the low catalog numbers, day 2 the high ones.
      { name: 'Jun d1 first', awards: 'BIS JUN-1', number: 18 },
      { name: 'Jun d1 second', awards: 'BIS JUN-2', number: 60 },
      { name: 'Jun d2 first', awards: 'BIS JUN-1', number: 1310 },
      { name: 'Jun d2 second', awards: 'BIS JUN-2', number: 1402 },
      { name: 'Vet d1 first', awards: 'BIS VET-1', number: 22 },
      { name: 'Vet d2 first', awards: 'BIS VET-1', number: 1290 },
      // Main BIS is left grouped (not split per day), per the chosen scope.
      { name: 'Main d1', awards: 'BIS-1', number: 18 },
      { name: 'Main d2', awards: 'BIS-1', number: 1310 },
    ]

    const groups = groupResultsByAwardFilter(dogs, 'BIS')

    expect(groups.map(group => group.label)).toEqual([
      'BIS',
      'BIS VET (1. päivä)',
      'BIS VET (2. päivä)',
      'BIS JUN (1. päivä)',
      'BIS JUN (2. päivä)',
    ])
    const byLabel = Object.fromEntries(groups.map(group => [group.label, group.dogs.map(dog => dog.name)]))
    expect(byLabel['BIS JUN (1. päivä)']).toEqual(['Jun d1 first', 'Jun d1 second'])
    expect(byLabel['BIS JUN (2. päivä)']).toEqual(['Jun d2 first', 'Jun d2 second'])
    expect(byLabel['BIS VET (1. päivä)']).toEqual(['Vet d1 first'])
    expect(byLabel['BIS VET (2. päivä)']).toEqual(['Vet d2 first'])
    expect(byLabel['BIS']).toEqual(['Main d1', 'Main d2'])
  })

  it('leaves single-day BIS JUN and BIS VET ungrouped (no per-day split)', () => {
    const dogs = [
      { name: 'Jun one', awards: 'BIS JUN-1', number: 12 },
      { name: 'Jun two', awards: 'BIS JUN-2', number: 40 },
      { name: 'Vet one', awards: 'BIS VET-1', number: 8 },
    ]

    const groups = groupResultsByAwardFilter(dogs, 'BIS')

    expect(groups.map(group => group.label)).toEqual(['BIS VET', 'BIS JUN'])
  })

  it('groups ROP and VSP results by category with winners first', () => {
    const dogs = [
      { name: 'Veteran opposite', breedName: 'Basenji', breedGroup: '6', breedId: '1', awards: 'VET VSP' },
      { name: 'Main opposite', breedName: 'Basenji', breedGroup: '6', breedId: '1', awards: 'VSP' },
      { name: 'Junior winner', breedName: 'Basenji', breedGroup: '6', breedId: '1', awards: 'JUN ROP' },
      { name: 'Main winner', breedName: 'Basenji', breedGroup: '6', breedId: '1', awards: 'ROP' },
      { name: 'Puppy winner', breedName: 'Akita', breedGroup: '5', breedId: '2', awards: 'ROP-pentu' },
      { name: 'Double winner', breedName: 'Basenji', breedGroup: '6', breedId: '1', awards: 'ROP, JUN ROP' },
    ]

    const groups = groupResultsByAwardFilter(dogs, 'ROP/VSP')

    expect(groups.map(group => group.label)).toEqual(['Akita', 'Basenji'])
    expect(groups[1].dogs.map(dog => dog.name)).toEqual([
      'Double winner',
      'Main winner',
      'Main opposite',
      'Veteran opposite',
      'Junior winner',
    ])
  })

  it('groups RYP results by breed group and orders each group by RYP rank', () => {
    const dogs = [
      { name: 'Group five second', breedGroup: '5', awards: 'RYP-2' },
      { name: 'Group one third', breedGroup: '1', awards: 'RYP-3' },
      { name: 'Group five first', breedGroup: '5', awards: 'RYP-1' },
      { name: 'Group one first', breedGroup: '1', awards: 'RYP-1' },
    ]

    const groups = groupResultsByAwardFilter(dogs, 'RYP')

    expect(groups.map(group => group.label)).toEqual(['Ryhmä 1', 'Ryhmä 5'])
    expect(groups[0].dogs.map(dog => `${dog.awardRank} ${dog.name}`)).toEqual([
      '1 Group one first',
      '3 Group one third',
    ])
    expect(groups[1].dogs.map(dog => `${dog.awardRank} ${dog.name}`)).toEqual([
      '1 Group five first',
      '2 Group five second',
    ])
  })
})

describe('showStatItems and showStatsLabel', () => {
  it('formats live show progress without exposing full entry count as a separate signup pill', () => {
    const show = {
      stats: {
        is_live: true,
        breed_count: 2,
        entry_count: 90,
        result_count: 12,
      },
    }

    expect(showStatItems(show)).toEqual([
      { key: 'live', label: 'Käynnissä', live: true },
      { key: 'breeds', label: '2 rotua' },
      {
        key: 'entries',
        label: '12/90 tulosta',
        title: '12/90 arvosteltua ilmoittautuneesta',
      },
    ])
    expect(showStatsLabel(show)).toBe('käynnissä, 2 rotua, 12/90 tulosta')
  })

  it('formats settled show entry counts as signups', () => {
    const entryCount = new Intl.NumberFormat('fi-FI').format(1200)
    const show = {
      stats: {
        breed_count: 3,
        entry_count: 1200,
      },
    }

    expect(showStatItems(show)).toEqual([
      { key: 'breeds', label: '3 rotua' },
      {
        key: 'entries',
        label: `${entryCount} koiraa`,
        title: `${entryCount} ilmoittautunutta`,
      },
    ])
    expect(showStatsLabel(show)).toBe(`3 rotua, ${entryCount} ilmoittautunutta`)
  })

  it('renders a paused multi-day show as Jatkuu while keeping today’s result count', () => {
    const show = {
      stats: {
        is_live: false,
        is_paused: true,
        breed_count: 2,
        entry_count: 90,
        result_count: 12,
      },
    }

    expect(showStatItems(show)).toEqual([
      { key: 'paused', label: 'Jatkuu', paused: true },
      { key: 'breeds', label: '2 rotua' },
      {
        key: 'entries',
        label: '12/90 tulosta',
        title: '12/90 arvosteltua ilmoittautuneesta',
      },
    ])
    expect(showStatsLabel(show)).toBe('jatkuu, 2 rotua, 12/90 tulosta')
  })
})

describe('showDateBadgeParts', () => {
  it('returns a single day for one-day shows', () => {
    expect(showDateBadgeParts({ date: '14.06.', month: 'kesäkuu 2026' })).toEqual({
      day: '14',
      month: 'kesä',
    })
  })

  it('returns a day range for same-month multi-day shows', () => {
    expect(showDateBadgeParts({ date: '13.-14.06.', month: 'kesäkuu 2026' })).toEqual({
      day: '13–14',
      month: 'kesä',
      range: true,
    })
  })

  it('falls back to the start day for cross-month ranges', () => {
    expect(showDateBadgeParts({ date: '31.01.-01.02.', month: 'helmikuu 2026' })).toEqual({
      day: '31',
      month: 'tammi',
    })
  })

  it('degrades to the raw day when the date cannot be parsed', () => {
    expect(showDateBadgeParts({ date: 'Tänään', month: 'kesäkuu 2026' })).toEqual({
      day: 'Tänään',
      month: '',
    })
  })
})

describe('isOvernightResultWindow', () => {
  const at = (hour) => new Date(2026, 5, 20, hour, 0, 0)

  it('is true before 06:00 and from 21:00 onward (default window)', () => {
    expect(isOvernightResultWindow(at(5))).toBe(true)
    expect(isOvernightResultWindow(at(23))).toBe(true)
    expect(isOvernightResultWindow(at(21))).toBe(true)
  })

  it('is false during the day', () => {
    expect(isOvernightResultWindow(at(6))).toBe(false)
    expect(isOvernightResultWindow(at(12))).toBe(false)
    expect(isOvernightResultWindow(at(20))).toBe(false)
  })

  it('honours custom hours', () => {
    expect(isOvernightResultWindow(at(19), 7, 19)).toBe(true)
    expect(isOvernightResultWindow(at(18), 7, 19)).toBe(false)
  })
})

describe('show date result availability', () => {
  it('formats full search-result dates from Showlink date labels', () => {
    expect(formatShowFullDate({ date: '14.06.', month: 'kesäkuu 2026' })).toBe('14.06.2026')
    expect(formatShowFullDate({ date: '13.-14.06.', month: 'kesäkuu 2026' })).toBe('13.–14.06.2026')
    expect(formatShowFullDate({ date: '31.01.-01.02.', month: 'helmikuu 2026' })).toBe('31.01.–01.02.2026')
  })

  it('falls back to the raw show date when the date cannot be parsed', () => {
    expect(formatShowFullDate({ date: 'Tänään', month: 'kesäkuu 2026' })).toBe('Tänään')
  })

  it('parses Showlink date labels with the year from the month heading', () => {
    const range = parseShowDateRange('20.06.', 'kesäkuu 2026')

    expect(range.start).toEqual(new Date(2026, 5, 20))
    expect(range.end).toEqual(new Date(2026, 5, 20))
  })

  it('blocks whole-show result loading until show morning', () => {
    const show = { date: '20.06.', month: 'kesäkuu 2026' }

    const future = getShowResultAvailability(show, new Date(2026, 5, 17, 12, 0))
    const earlyMorning = getShowResultAvailability(show, new Date(2026, 5, 20, 5, 59))
    const showDay = getShowResultAvailability(show, new Date(2026, 5, 20, 6, 0))

    expect(future).toMatchObject({
      canLoad: false,
      phase: 'upcoming',
      title: 'Tuloksia ei haeta vielä',
    })
    expect(earlyMorning).toMatchObject({
      canLoad: false,
      phase: 'show_morning',
      title: 'Tuloksia odotetaan',
    })
    expect(showDay).toMatchObject({
      canLoad: true,
      phase: 'show_day',
      actionLabel: 'Tarkista koirat ja tulokset',
    })
  })
})

describe('createShowBreedGroups', () => {
  const breeds = [
    {
      name: 'Basenji',
      count: 3,
      group: '6',
      breed_id: '123',
      has_results: true,
      judge: 'Paula Steele',
    },
    {
      name: 'Akita',
      count: 1,
      group: '5',
      breed_id: '10',
      has_results: false,
      judge: 'Tarja Kolkka',
    },
  ]

  const dogs = [
    {
      number: 1,
      name: 'Aamun Tähti',
      grade: 'ERI',
      class_name: 'JUN',
      breedName: 'Basenji',
      breedGroup: '6',
      breedId: '123',
      breedObj: breeds[0],
    },
    {
      number: 2,
      name: 'Iltatuuli',
      grade: 'EH',
      class_name: 'AVO',
      breedName: 'Akita',
      breedGroup: '5',
      breedId: '10',
      breedObj: {
        name: 'Akita',
        count: 1,
        group: '5',
        breed_id: '10',
        has_results: true,
        judge: 'Tarja Kolkka',
      },
    },
  ]

  it('combines indexed breed rows with whole-show cache dogs', () => {
    const groups = createShowBreedGroups({
      breeds,
      dogs,
      allDogsLoaded: true,
    })

    expect(groups).toHaveLength(2)
    expect(groups[0]).toMatchObject({
      key: '6:123',
      breedName: 'Basenji',
      judge: 'Paula Steele',
      dogs: [dogs[0]],
    })
    expect(groups[1]).toMatchObject({
      key: '5:10',
      breedName: 'Akita',
      judge: 'Tarja Kolkka',
      has_results: true,
      dogs: [dogs[1]],
    })
  })

  it('can show only breeds with available results', () => {
    const groups = createShowBreedGroups({
      breeds,
      dogs: [],
      resultsOnly: true,
    })

    expect(groups).toHaveLength(1)
    expect(groups[0].breedName).toBe('Basenji')
  })

  it('keeps cache-only result breeds when filtering to available results', () => {
    const groups = createShowBreedGroups({
      breeds,
      dogs,
      allDogsLoaded: true,
      resultsOnly: true,
    })

    expect(groups.map(group => group.breedName)).toEqual(['Basenji', 'Akita'])
  })

  it('uses live progress counts for results-only filtering and progress labels', () => {
    const groups = createShowBreedGroups({
      breeds: [
        {
          name: 'Basenji',
          count: 26,
          group: '5',
          breed_id: '3',
          has_results: true,
          result_count: 5,
          result_total_count: 26,
          result_updated_at: 200,
        },
        {
          name: 'Akita',
          count: 12,
          group: '5',
          breed_id: '10',
          has_results: true,
          result_count: 0,
          result_total_count: 12,
          result_updated_at: 250,
        },
      ],
      resultsOnly: true,
    })

    expect(groups).toHaveLength(1)
    expect(groups[0]).toMatchObject({
      breedName: 'Basenji',
      resultCount: 5,
      resultTotalCount: 26,
      resultProgressKnown: true,
      resultProgressLabel: '5/26',
    })
  })

  it('orders results-only live breeds by freshest result progress', () => {
    const groups = createShowBreedGroups({
      breeds: [
        {
          name: 'Older',
          count: 10,
          group: '5',
          breed_id: '3',
          has_results: true,
          result_count: 4,
          result_total_count: 10,
          result_updated_at: 100,
        },
        {
          name: 'Freshest',
          count: 8,
          group: '5',
          breed_id: '4',
          has_results: true,
          result_count: 1,
          result_total_count: 8,
          result_updated_at: 300,
        },
        {
          name: 'Middle',
          count: 12,
          group: '5',
          breed_id: '5',
          has_results: true,
          result_count: 6,
          result_total_count: 12,
          result_updated_at: 200,
        },
      ],
      resultsOnly: true,
    })

    expect(groups.map(group => group.breedName)).toEqual(['Freshest', 'Middle', 'Older'])
  })

  it('can filter by dog details from the whole-show cache', () => {
    const groups = createShowBreedGroups({
      breeds,
      dogs,
      query: 'iltatuuli',
      allDogsLoaded: true,
    })

    expect(groups).toHaveLength(1)
    expect(groups[0].breedName).toBe('Akita')
  })

  it('filters indexed breed judges before whole-show dogs are loaded', () => {
    const groups = createShowBreedGroups({
      breeds,
      dogs: [],
      query: 'paula',
      allDogsLoaded: false,
    })

    expect(groups).toHaveLength(1)
    expect(groups[0].breedName).toBe('Basenji')
    expect(groups[0].judge).toBe('Paula Steele')
  })
})

describe('buildDogQuery', () => {
  it('drops empty values and preserves dog route params', () => {
    expect(buildDogQuery({
      show: 14042,
      group: '6',
      breed: '123',
      ignored: '',
      nil: null,
      missing: undefined,
    })).toEqual({
      show: '14042',
      group: '6',
      breed: '123',
    })
  })
})

describe('sortBreedAwards', () => {
  it('sorts breed awards correctly according to AWARD_FILTER_ORDER and sub-orderings', () => {
    const input = [
      { type: 'KP', text: 'Dog KP' },
      { type: 'VSP Pentu', text: 'Puppy VSP' },
      { type: 'ROP', text: 'Dog ROP' },
      { type: 'SERT Narttu', text: 'Bitch SERT' },
      { type: 'VSP Veteraani', text: 'Vet VSP' },
      { type: 'CACIB Uros', text: 'Dog CACIB' },
      { type: 'ROP Pentu', text: 'Puppy ROP' },
      { type: 'VSP', text: 'Dog VSP' },
      { type: 'ROP Juniori', text: 'Jun ROP' },
      { type: 'MVA Narttu', text: 'Bitch MVA' },
      { type: 'SERT Uros', text: 'Dog SERT' },
      { type: 'SA Uros', text: 'Dog SA' },
      { type: 'ROP Kasvattaja', text: 'Breeder ROP' },
    ]

    const sorted = sortBreedAwards(input)
    
    expect(sorted.map(a => a.type)).toEqual([
      // 1. ROP/VSP variations sorted first (plain -> VET -> JUN -> PEN -> KASVATTAJA, and ROP before VSP)
      'ROP',
      'VSP',
      'VSP Veteraani',
      'ROP Juniori',
      'ROP Pentu',
      'VSP Pentu',
      'ROP Kasvattaja',
      // 2. MVA
      'MVA Narttu',
      // 3. SERT (Uros before Narttu)
      'SERT Uros',
      'SERT Narttu',
      // 4. CACIB
      'CACIB Uros',
      // 5. SA
      'SA Uros',
      // 6. KP
      'KP',
    ])
  })
})

describe('fciGroupLabel', () => {
  it('maps known FCI groups to their Finnish names', () => {
    expect(fciGroupLabel('3')).toBe('Ryhmä 3 – Terrierit')
    expect(fciGroupLabel('10')).toBe('Ryhmä 10 – Vinttikoirat')
  })

  it('labels unknown numeric groups generically and non-numeric as "Muu ryhmä"', () => {
    expect(fciGroupLabel('11')).toBe('Ryhmä 11')
    expect(fciGroupLabel('')).toBe('Muu ryhmä')
    expect(fciGroupLabel(null)).toBe('Muu ryhmä')
    expect(fciGroupLabel('pentu')).toBe('Muu ryhmä')
  })
})

describe('groupShowBreedGroups', () => {
  const makeBreedGroup = (overrides = {}) => ({
    key: overrides.key || `${overrides.group || '0'}:${overrides.breedName || 'x'}`,
    breedName: overrides.breedName || 'Rotu',
    judge: overrides.judge ?? '',
    breed: { group: overrides.group ?? '', judge: overrides.judge ?? '' },
  })

  const breedGroups = [
    makeBreedGroup({ breedName: 'Basenji', group: '6', judge: 'Kaarina Koski' }),
    makeBreedGroup({ breedName: 'Akita', group: '5', judge: 'Antti Aalto' }),
    makeBreedGroup({ breedName: 'Beagle', group: '6', judge: 'Antti Aalto' }),
    makeBreedGroup({ breedName: 'Tuntematon', group: '', judge: '' }),
  ]

  it('returns a single unlabelled section in alpha mode preserving incoming order', () => {
    const sections = groupShowBreedGroups(breedGroups, 'alpha')
    expect(sections).toHaveLength(1)
    expect(sections[0].label).toBe('')
    expect(sections[0].breeds.map(b => b.breedName)).toEqual([
      'Basenji', 'Akita', 'Beagle', 'Tuntematon',
    ])
  })

  it('groups by FCI group, orders sections numerically, and puts unknown last', () => {
    const sections = groupShowBreedGroups(breedGroups, 'fci')
    expect(sections.map(s => s.label)).toEqual([
      'Ryhmä 5 – Pystykorvat ja alkukantaiset koirat',
      'Ryhmä 6 – Ajavat ja jäljestävät koirat',
      'Muu ryhmä',
    ])
    // Order within a section is preserved (Basenji indexed before Beagle).
    expect(sections[1].breeds.map(b => b.breedName)).toEqual(['Basenji', 'Beagle'])
  })

  it('groups by judge alphabetically and collects judge-less breeds at the end', () => {
    const sections = groupShowBreedGroups(breedGroups, 'judge')
    expect(sections.map(s => s.label)).toEqual([
      'Antti Aalto',
      'Kaarina Koski',
      'Tuomari ei tiedossa',
    ])
    expect(sections[0].breeds.map(b => b.breedName)).toEqual(['Akita', 'Beagle'])
  })

  it('returns no sections for an empty breed list', () => {
    expect(groupShowBreedGroups([], 'fci')).toEqual([])
  })
})

describe('show-detail critique keys', () => {
  it('builds the breed-group key from the group key and dog number', () => {
    const group = { key: '6:Basenji' }
    expect(showBreedGroupCritiqueKey(group, { number: 1, name: 'Aamun Tähti' }))
      .toBe('all-6:Basenji-1')
  })

  it('falls back to the dog name when there is no catalog number', () => {
    const group = { key: '6:Basenji' }
    expect(showBreedGroupCritiqueKey(group, { number: '', name: 'Aamun Tähti' }))
      .toBe('all-6:Basenji-Aamun Tähti')
  })

  it('builds the award key including the dogs breed identity', () => {
    const group = { key: 'BIS' }
    expect(showAwardCritiqueKey(group, { number: 2, breedGroup: '6', breedName: 'Basenji', name: 'Iltatähti' }))
      .toBe('show-award-BIS-6-2')
  })

  it('award key falls back to breed name then dog name', () => {
    const group = { key: 'ROP/VSP' }
    expect(showAwardCritiqueKey(group, { breedName: 'Basenji', name: 'Iltatähti' }))
      .toBe('show-award-ROP/VSP-Basenji-Iltatähti')
  })
})

