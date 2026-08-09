import { describe, it, expect } from 'vitest'
import { useLinkIcon } from '~/composables/useLinkIcon.js'

const { linkIcon, isExternal } = useLinkIcon()

describe('useLinkIcon — linkIcon()', () => {
  it('uses the letter glyph for mailto:', () => {
    expect(linkIcon('mailto:hello@erez.ac')).toBe('solar:letter-bold')
  })

  it('uses brand logos for GitHub and LinkedIn', () => {
    expect(linkIcon('https://github.com/kvjanhun')).toBe('simple-icons:github')
    expect(linkIcon('https://www.linkedin.com/in/konsta-janhunen-263832165')).toBe('simple-icons:linkedin')
  })

  it('uses the diagonal go-arrow for other external links', () => {
    expect(linkIcon('https://sanakenno.fi')).toBe('solar:arrow-right-up-bold')
  })

  it('uses a plain arrow for internal routes and anchors', () => {
    // The diagonal arrow conventionally means "leaves this site", so #stack and
    // /dog must not wear it.
    expect(linkIcon('#stack')).toBe('solar:arrow-right-bold')
    expect(linkIcon('/dog')).toBe('solar:arrow-right-bold')
    expect(linkIcon('/recipes/pancakes')).toBe('solar:arrow-right-bold')
  })

  it('does not mistake a path containing a brand name for that brand', () => {
    expect(linkIcon('/github.com-notes')).toBe('solar:arrow-right-bold')
  })

  it('handles a missing href without throwing', () => {
    expect(linkIcon()).toBe('solar:arrow-right-bold')
    expect(linkIcon('')).toBe('solar:arrow-right-bold')
  })
})

describe('useLinkIcon — isExternal()', () => {
  it('treats http, https and mailto as external', () => {
    expect(isExternal('https://sanakenno.fi')).toBe(true)
    expect(isExternal('http://example.com')).toBe(true)
    expect(isExternal('mailto:hello@erez.ac')).toBe(true)
  })

  it('treats site-relative paths and anchors as internal', () => {
    expect(isExternal('/dog')).toBe(false)
    expect(isExternal('#stack')).toBe(false)
    expect(isExternal('')).toBe(false)
    expect(isExternal()).toBe(false)
  })

  it('is case-insensitive about the scheme', () => {
    expect(isExternal('HTTPS://example.com')).toBe(true)
    expect(isExternal('MailTo:hello@erez.ac')).toBe(true)
  })
})
