import { describe, expect, it } from 'vitest'
import {
  buildDogQuery,
  createShowBreedGroups,
  getShowResultAvailability,
  gradeMatchesFilter,
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
