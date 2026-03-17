import { marked } from 'marked'
import DOMPurify from 'dompurify'

const renderer = new marked.Renderer()

renderer.link = ({ href, title, text }) => {
  const isExternal = href && !href.startsWith('/') && !href.startsWith('#')
  const attrs = isExternal ? ' target="_blank" rel="noopener noreferrer"' : ''
  const titleAttr = title ? ` title="${title}"` : ''
  return `<a href="${href}"${titleAttr}${attrs}>${text}</a>`
}

marked.use({
  renderer,
  breaks: true,
  gfm: true,
})

const ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'a', 'ul', 'ol', 'li', 'code', 'pre', 'blockquote']
const ALLOWED_ATTR = ['href', 'title', 'target', 'rel']

export function renderMarkdown(source) {
  if (!source) return ''
  const html = marked.parse(source)
  // DOMPurify requires a browser DOM — skip sanitization during SSR.
  // In production (SSG) section content is always loaded client-side, so
  // DOMPurify always runs before any rendered HTML reaches the user.
  if (import.meta.server) return html
  return DOMPurify.sanitize(html, { ALLOWED_TAGS, ALLOWED_ATTR })
}
