import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { trackPageView } from '~/composables/usePageView.js'

describe('trackPageView', () => {
  let fetchMock

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue({})
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('calls POST /api/pageview', async () => {
    trackPageView('/about')
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/pageview')
    expect(options.method).toBe('POST')
  })

  it('sends the path as JSON in the request body', async () => {
    trackPageView('/sanakenno')
    const [, options] = fetchMock.mock.calls[0]
    expect(options.body).toBe(JSON.stringify({ path: '/sanakenno' }))
  })

  it('sets Content-Type to application/json', () => {
    trackPageView('/contact')
    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers['Content-Type']).toBe('application/json')
  })

  it('does not throw when fetch rejects (fire-and-forget)', async () => {
    fetchMock.mockRejectedValue(new Error('network error'))
    // Should not throw synchronously or propagate a rejection
    expect(() => trackPageView('/error-path')).not.toThrow()
    // Allow the rejected promise to settle without an unhandled rejection
    await new Promise((resolve) => setTimeout(resolve, 0))
  })

  it('sends different paths correctly', () => {
    trackPageView('/recipes/pancakes')
    const [, options] = fetchMock.mock.calls[0]
    expect(JSON.parse(options.body).path).toBe('/recipes/pancakes')
  })
})
