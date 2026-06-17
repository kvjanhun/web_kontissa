import { describe, expect, it } from 'vitest'
import {
  availableAwardsFromResults,
  awardMatchesFilter,
  buildDogQuery,
  createShowBreedGroups,
  dogMatchesShowFilters,
  filterDogResults,
  getShowResultAvailability,
  gradeMatchesFilter,
  groupResultsByAwardFilter,
  parseShowDateRange,
  showStatItems,
  showStatsLabel,
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
      { name: 'A', awards: 'BIS-1, ROP, SERT, JUN-SERT, VET-SERT, VARA-SERT, NORD-SERT, NORD VET-SERT, NORD JUN-SERT, NORD VARA-SERT, SA' },
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
})

describe('show date result availability', () => {
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
