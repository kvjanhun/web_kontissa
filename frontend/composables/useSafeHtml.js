import DOMPurify from 'isomorphic-dompurify'

const ALLOWED_URL_PROTOCOLS = new Set(['http:', 'https:', 'mailto:'])

export function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export function safeHref(value) {
  const href = String(value ?? '').trim()
  if (!href) return ''

  if (href.startsWith('#')) return href
  if (href.startsWith('/') && !href.startsWith('//')) return href

  try {
    const url = new URL(href)
    return ALLOWED_URL_PROTOCOLS.has(url.protocol) ? href : ''
  } catch {
    return ''
  }
}

export function isExternalHref(href) {
  const safe = safeHref(href)
  return /^https?:\/\//i.test(safe)
}

export function sanitizeHtml(html, options) {
  return DOMPurify.sanitize(html, options)
}

export function renderSafeInlineLinks(text, { className = '', externalIcon = '' } = {}) {
  if (!text) return ''

  const linkPattern = /\[([^\]]+)\]\(([^()]*(?:\([^)]*\)[^()]*)*)\)/g
  let output = ''
  let lastIndex = 0

  for (const match of text.matchAll(linkPattern)) {
    output += escapeHtml(text.slice(lastIndex, match.index))

    const label = match[1]
    const href = safeHref(match[2])
    if (href) {
      const external = isExternalHref(href)
      const classAttr = className ? ` class="${escapeHtml(className)}"` : ''
      const externalAttrs = external ? ' target="_blank" rel="noopener noreferrer"' : ''
      const icon = external ? externalIcon : ''
      output += `<a href="${escapeHtml(href)}"${classAttr}${externalAttrs}>${escapeHtml(label)}${icon}</a>`
    } else {
      output += escapeHtml(label)
    }

    lastIndex = match.index + match[0].length
  }

  output += escapeHtml(text.slice(lastIndex))
  return output
}
