import { describe, it, expect } from 'vitest'
import { useUptime } from '~/composables/useUptime.js'

const { uptimeLabel } = useUptime()

const HOUR = 3600
const DAY = 86400

describe('useUptime — uptimeLabel()', () => {
  it('reports whole days once the box has been up at least one', () => {
    expect(uptimeLabel(34 * DAY)).toEqual({ key: 'home.footer.uptimeDays', n: 34 })
  })

  it('uses the singular key at exactly one day', () => {
    expect(uptimeLabel(DAY)).toEqual({ key: 'home.footer.uptimeDay', n: 1 })
  })

  it('floors partial days rather than rounding up', () => {
    expect(uptimeLabel(2 * DAY + 23 * HOUR)).toEqual({ key: 'home.footer.uptimeDays', n: 2 })
  })

  it('falls back to hours below a day', () => {
    expect(uptimeLabel(5 * HOUR)).toEqual({ key: 'home.footer.uptimeHours', n: 5 })
  })

  it('uses the singular key at exactly one hour', () => {
    expect(uptimeLabel(HOUR)).toEqual({ key: 'home.footer.uptimeHour', n: 1 })
  })

  it('never reports zero hours — a fresh reboot reads as one', () => {
    expect(uptimeLabel(20 * 60)).toEqual({ key: 'home.footer.uptimeHour', n: 1 })
    expect(uptimeLabel(0)).toEqual({ key: 'home.footer.uptimeHour', n: 1 })
  })

  it('returns null for anything unusable, so the footer renders no figure', () => {
    // Each of these is a real shape /api/server-info can produce, or that a
    // failed fetch leaves behind.
    expect(uptimeLabel(null)).toBeNull()
    expect(uptimeLabel(undefined)).toBeNull()
    expect(uptimeLabel('34')).toBeNull()
    expect(uptimeLabel(NaN)).toBeNull()
    expect(uptimeLabel(Infinity)).toBeNull()
    expect(uptimeLabel(-1)).toBeNull()
  })
})
