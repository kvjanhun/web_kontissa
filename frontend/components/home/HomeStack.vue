<script setup>
const i18n = useI18nStore()
const { t, tm } = i18n
const vReveal = useScrollReveal()

const layers = computed(() => tm('home.stack.layers') || [])

// The intro is optional: clearing the field in the admin should drop the
// paragraph rather than leave an empty <p> holding its margin.
const intro = computed(() => (t('home.stack.intro') || '').trim())
</script>

<template>
  <section id="stack" class="stack">
    <h2 class="sec-head home-plate">{{ t('home.stack.label') }}</h2>
    <p v-if="intro" class="stack__intro home-plate">{{ intro }}</p>

    <div class="stack__table" v-reveal>
      <div v-for="layer in layers" :key="layer.z" class="layer">
        <div class="layer__z"><span class="layer-tag">{{ layer.z }}</span></div>
        <div class="layer__name">
          <span class="layer__kicker">{{ layer.layer }}</span>
          <span class="layer__title">{{ layer.title }}</span>
        </div>
        <div class="layer__detail">{{ layer.detail }}</div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.stack { padding: 56px 0; }

.sec-head {
  margin: 0 0 14px;
  font-size: 13px;
  font-family: var(--font-plex-mono);
  color: var(--accent);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.stack__intro {
  margin: 0 0 26px;
  max-width: 60ch;
  font-size: 16px;
  line-height: 1.6;
  color: var(--tx-2);
  font-weight: 300;
}

.stack__table {
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  background: var(--panel);
}
.layer {
  display: grid;
  grid-template-columns: 64px 200px 1fr;
  border-bottom: 1px solid var(--line-2);
  align-items: stretch;
  transition: background 0.15s ease;
}
.layer:last-child { border-bottom: none; }
.layer:hover { background: var(--accent-dim); }
.layer__z {
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid var(--line-2);
}
/* Same chip as the reach ranges in HomeWork, so the token a project links here
   with and the token it lands on read as the same object. */
.layer-tag {
  font-family: var(--font-plex-mono);
  font-size: 11px;
  color: var(--accent);
  border: 1px solid var(--accent-dim);
  background: var(--accent-dim);
  padding: 4px 10px;
  border-radius: 5px;
  transition: border-color 0.15s ease;
}
/* The row hover fills to --accent-dim, which is the chip's own background, so
   without this the chip dissolves into the row exactly when it is pointed at. */
.layer:hover .layer-tag { border-color: var(--accent); }
.layer__name {
  padding: 13px 20px;
  border-right: 1px solid var(--line-2);
  display: flex;
  flex-direction: column;
  gap: 4px;
  justify-content: center;
}
.layer__kicker {
  font-family: var(--font-plex-mono);
  font-size: 10px;
  color: var(--accent);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.layer__title {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.layer__detail {
  padding: 13px 22px;
  display: flex;
  align-items: center;
  font-size: 14px;
  color: var(--tx-2);
  line-height: 1.5;
}

@media (max-width: 720px) {
  .stack { padding: 32px 0; }
  .stack__intro { margin-bottom: 18px; font-size: 14px; }
  /* Two columns rather than three stacked rows: the chip shares its line with
     the layer name instead of holding one of its own, and the detail spans
     underneath. */
  .layer {
    grid-template-columns: auto 1fr;
    padding: 14px 15px;
    column-gap: 12px;
    row-gap: 6px;
    align-items: center;
  }
  .layer__z {
    grid-area: 1 / 1;
    justify-content: flex-start;
    border-right: none;
  }
  .layer__name {
    grid-area: 1 / 2;
    flex-direction: row;
    flex-wrap: wrap;
    align-items: baseline;
    justify-content: flex-start;
    gap: 4px 10px;
    padding: 0;
    border-right: none;
  }
  .layer__detail {
    grid-area: 2 / 1 / auto / span 2;
    padding: 0;
    font-size: 12.5px;
  }
}
</style>
