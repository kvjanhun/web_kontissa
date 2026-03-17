import { describe, it, expect } from 'vitest'
import { renderMarkdown } from '~/composables/useMarkdown'

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

  it('strips disallowed tags like <img>', () => {
    const result = renderMarkdown('<img src="x" onerror="alert(1)">')
    expect(result).not.toContain('<img')
  })

  it('strips heading tags', () => {
    const result = renderMarkdown('## Heading')
    expect(result).not.toMatch(/<h[1-6]/)
  })
})
