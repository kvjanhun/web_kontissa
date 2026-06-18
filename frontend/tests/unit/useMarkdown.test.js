import { describe, it, expect } from 'vitest'
import { renderMarkdown } from '~/composables/useMarkdown'
import { renderSafeInlineLinks, safeHref } from '~/composables/useSafeHtml'

describe('renderMarkdown', () => {
  it('returns empty string for empty input', () => {
    expect(renderMarkdown('')).toBe('')
    expect(renderMarkdown(null)).toBe('')
    expect(renderMarkdown(undefined)).toBe('')
  })

  it('renders paragraphs', () => {
    expect(renderMarkdown('Hello world')).toContain('Hello world')
  })

  it('renders bold and italic', () => {
    expect(renderMarkdown('**bold**')).toContain('<strong>bold</strong>')
    expect(renderMarkdown('*italic*')).toContain('<em>italic</em>')
  })

  it('renders internal links without target', () => {
    const result = renderMarkdown('[About](/about)')
    expect(result).toContain('href="/about"')
    expect(result).not.toContain('target="_blank"')
  })

  it('renders external links with target and rel', () => {
    const result = renderMarkdown('[Example](https://example.com)')
    expect(result).toContain('target="_blank"')
    expect(result).toContain('rel="noopener noreferrer"')
  })

  it('renders single newlines as <br> (breaks: true)', () => {
    const result = renderMarkdown('line one\nline two')
    expect(result).toContain('<br>')
  })

  it('strips <script> tags', () => {
    const result = renderMarkdown('<script>alert(1)</script>')
    expect(result).not.toContain('<script>')
    expect(result).not.toContain('alert(1)')
  })

  it('strips javascript: hrefs', () => {
    const result = renderMarkdown('[click](javascript:alert(1))')
    expect(result).not.toContain('javascript:')
  })

  it('strips unsafe hrefs from raw HTML links', () => {
    const result = renderMarkdown('<a href="ftp://example.com">ftp</a>')
    expect(result).not.toContain('ftp://')
  })

  it('drops link titles before sanitizing', () => {
    const result = renderMarkdown('[Example](https://example.com "bad&quot; onclick=&quot;alert(1)")')
    expect(result).toContain('href="https://example.com"')
    expect(result).not.toContain('title=')
    expect(result).not.toContain('onclick')
  })

  it('strips disallowed tags like <img>', () => {
    const result = renderMarkdown('<img src="x" onerror="alert(1)">')
    expect(result).not.toContain('<img')
  })

  it('strips heading tags', () => {
    const result = renderMarkdown('## Heading')
    expect(result).not.toMatch(/<h[1-6]/)
  })
})

describe('safe link helpers', () => {
  it('allows only explicit safe URL forms', () => {
    expect(safeHref('https://example.com')).toBe('https://example.com')
    expect(safeHref('http://example.com')).toBe('http://example.com')
    expect(safeHref('mailto:hello@example.com')).toBe('mailto:hello@example.com')
    expect(safeHref('/about')).toBe('/about')
    expect(safeHref('#contact')).toBe('#contact')
    expect(safeHref('javascript:alert(1)')).toBe('')
    expect(safeHref('data:text/html,evil')).toBe('')
    expect(safeHref('//example.com/path')).toBe('')
    expect(safeHref('relative/path')).toBe('')
  })

  it('renders safe inline links while escaping surrounding text', () => {
    const html = renderSafeInlineLinks('Ping <me> [GitHub](https://github.com/kvjanhun)', {
      className: 'contact-link',
      externalIcon: '<svg aria-hidden="true"></svg>',
    })

    expect(html).toContain('Ping &lt;me&gt;')
    expect(html).toContain('href="https://github.com/kvjanhun"')
    expect(html).toContain('class="contact-link"')
    expect(html).toContain('target="_blank"')
  })

  it('renders unsafe inline links as escaped text', () => {
    expect(renderSafeInlineLinks('[Click](javascript:alert(1))')).toBe('Click')
    expect(renderSafeInlineLinks('[<bad>](data:text/html,evil)')).toBe('&lt;bad&gt;')
  })
})
