import { marked } from 'marked'
import { escapeHtml, isExternalHref, safeHref, sanitizeHtml } from './useSafeHtml.js'

const renderer = new marked.Renderer()

renderer.link = ({ href, text }) => {
  const cleanHref = safeHref(href)
  if (!cleanHref) return text

  const isExternal = isExternalHref(cleanHref)
  const attrs = isExternal ? ' target="_blank" rel="noopener noreferrer"' : ''
  return `<a href="${escapeHtml(cleanHref)}"${attrs}>${text}</a>`
}

marked.use({
  renderer,
  breaks: true,
  gfm: true,
})

const ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'a', 'ul', 'ol', 'li', 'code', 'pre', 'blockquote']
const ALLOWED_ATTR = ['href', 'title', 'target', 'rel']
const ALLOWED_URI_REGEXP = /^(?:(?:https?|mailto):|\/(?!\/)|#)/i

function addExternalLinkAttrs(html) {
  return html.replace(/<a href="(https?:\/\/[^"]+)">/gi, (_, href) => (
    `<a href="${href}" target="_blank" rel="noopener noreferrer">`
  ))
}

export function renderMarkdown(source) {
  if (!source) return ''
  const html = marked.parse(source)
  const clean = sanitizeHtml(html, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOWED_URI_REGEXP,
    ADD_ATTR: ['target', 'rel'],
  })
  return addExternalLinkAttrs(clean)
}
