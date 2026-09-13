<script setup>
// Show/hide the landing page's content bands. Separate from the copy editor it
// sits above because visibility is language-independent — there is no EN/FI split
// here — and because each toggle saves on its own rather than joining the copy
// editor's batched draft/save flow.
//
// The set of sections is fixed server-side (HOME_SECTIONS in app/home_content.py);
// this panel renders whatever that endpoint lists, labels included.
const sections = ref([])
const loaded = ref(false)
const error = ref('')
const busy = ref('')

onMounted(load)

async function load() {
  error.value = ''
  try {
    const res = await fetch('/api/admin/sections')
    if (!res.ok) { error.value = 'Failed to load sections'; return }
    sections.value = await res.json()
    loaded.value = true
  } catch {
    error.value = 'Failed to load sections'
  }
}

async function toggle(section) {
  error.value = ''
  busy.value = section.key
  const next = !section.hidden
  try {
    const res = await fetch('/api/admin/sections', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: section.key, hidden: next }),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      error.value = `${section.label}: ${data.error || 'save failed'}`
      return
    }
    // Take the state from the response, not from `next` — the row the server wrote
    // is the one the page will render.
    section.hidden = (await res.json()).hidden
  } catch {
    error.value = `${section.label}: save failed`
  } finally {
    busy.value = ''
  }
}
</script>

<template>
  <div class="card sec">
    <div class="sec__head">
      <h2 class="sec__title">Sections</h2>
      <p class="sec__sub">
        Hide a band of the landing page without taking its content away — hiding a
        section leaves its text and projects untouched, and its links in the top
        navigation disappear with it. Changes are live immediately.
      </p>
    </div>

    <div v-if="error" class="sec__err" role="alert">{{ error }}</div>
    <div v-if="!loaded && !error" class="sec__loading">Loading…</div>

    <ul v-else class="sec__list">
      <li v-for="s in sections" :key="s.key" class="sec__row">
        <div class="sec__meta">
          <span class="sec__label">{{ s.label }}</span>
          <span class="sec__state" :class="{ 'sec__state--off': s.hidden }">
            {{ s.hidden ? 'Hidden' : 'Visible' }}
          </span>
        </div>
        <button
          type="button"
          class="sec__switch"
          role="switch"
          :aria-checked="!s.hidden"
          :aria-label="`Show ${s.label} section`"
          :disabled="busy === s.key"
          :class="{ 'sec__switch--on': !s.hidden }"
          @click="toggle(s)"
        >
          <span class="sec__knob" />
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.sec__head { margin-bottom: 16px; padding-bottom: 14px; border-bottom: 1px solid var(--as-line-2); }
.sec__title { margin: 0 0 6px; font-size: 16px; font-weight: 600; }
.sec__sub { margin: 0; max-width: 62ch; font-size: 13px; line-height: 1.55; color: var(--as-tx-2); }

.sec__err { padding: 10px 14px; border-radius: 9px; font-size: 13px; margin-bottom: 12px; background: #fdece5; color: #c0392b; }
.sec__loading { padding: 14px 0; color: var(--as-tx-3); font-size: 13.5px; }

.sec__list { list-style: none; margin: 0; padding: 0; }
.sec__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 11px 0;
  border-bottom: 1px solid var(--as-line-2);
}
.sec__row:last-child { border-bottom: none; padding-bottom: 0; }

.sec__meta { display: flex; align-items: baseline; gap: 10px; min-width: 0; }
.sec__label { font-size: 14px; font-weight: 500; }
.sec__state {
  font-family: var(--font-mono, monospace);
  font-size: 10.5px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--as-tx-3);
}
.sec__state--off { color: var(--as-accent); }

.sec__switch {
  flex: none;
  width: 42px;
  height: 24px;
  padding: 3px;
  border: none;
  border-radius: 999px;
  background: #d8d8d2;
  cursor: pointer;
  transition: background 0.15s ease;
}
.sec__switch--on { background: var(--as-accent); }
.sec__switch:disabled { opacity: 0.55; cursor: progress; }
.sec__switch:focus-visible { outline: 2px solid var(--as-tx); outline-offset: 2px; }
.sec__knob {
  display: block;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.15s ease;
}
.sec__switch--on .sec__knob { transform: translateX(18px); }

/* The knob slide is decoration; the label beside it carries the state. */
@media (prefers-reduced-motion: reduce) {
  .sec__switch, .sec__knob { transition: none; }
}
</style>
