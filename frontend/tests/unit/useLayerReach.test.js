import { describe, it, expect } from 'vitest'
import { useLayerReach } from '~/composables/useLayerReach.js'

const { reachRanges } = useLayerReach()

describe('useLayerReach — reachRanges()', () => {
  it('collapses a contiguous run into one range', () => {
    expect(reachRanges(['L2', 'L3', 'L4', 'L5', 'L6', 'L7'])).toEqual(['L2–L7'])
  })

  it('renders the full stack as a single range', () => {
    expect(reachRanges(['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7'])).toEqual(['L1–L7'])
  })

  it('renders a lone layer without a dash', () => {
    expect(reachRanges(['L6'])).toEqual(['L6'])
  })

  it('splits a gap into separate ranges rather than one dishonest one', () => {
    expect(reachRanges(['L1', 'L2', 'L6', 'L7'])).toEqual(['L1–L2', 'L6–L7'])
  })

  it('keeps a lone layer separate from an adjacent run', () => {
    expect(reachRanges(['L1', 'L4', 'L5'])).toEqual(['L1', 'L4–L5'])
  })

  it('sorts and deduplicates before collapsing', () => {
    // The API already sorts, but the snapshot and hand-edited rows need not.
    expect(reachRanges(['L7', 'L6', 'L7'])).toEqual(['L6–L7'])
  })

  it('returns nothing for an empty or missing selection', () => {
    expect(reachRanges([])).toEqual([])
    expect(reachRanges(null)).toEqual([])
    expect(reachRanges(undefined)).toEqual([])
  })

  it('ignores tokens outside L1–L7', () => {
    expect(reachRanges(['L0', 'L8', 'nonsense', 'L6'])).toEqual(['L6'])
  })
})
