<script setup>
const i18n = useI18nStore()
const { t, tm } = i18n
const vReveal = useScrollReveal()

const layers = computed(() => tm('home.stack.layers') || [])
</script>

<template>
  <section id="stack" class="stack">
    <div class="sec-head">
      <h2 class="sec-head__label home-plate">02 — {{ t('home.stack.label') }}</h2>
      <span class="sec-head__aside home-plate">{{ t('home.stack.tag') }}</span>
    </div>
    <p class="stack__intro home-plate">{{ t('home.stack.intro') }}</p>

    <div class="stack__table" v-reveal>
      <div v-for="layer in layers" :key="layer.z" class="layer">
        <div class="layer__z">{{ layer.z }}</div>
        <div class="layer__name">
          <span class="layer__kicker">{{ layer.layer }}</span>
          <span class="layer__title">{{ layer.title }}</span>
        </div>
        <div class="layer__detail">{{ layer.detail }}</div>
      </div>
    </div>

    <p class="stack__footnote home-plate">{{ t('home.stack.footnote') }}</p>
  </section>
</template>

<style scoped>
.stack { padding: 84px 0; }

.sec-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 14px;
}
.sec-head__label {
  margin: 0;
  font-size: 13px;
  font-family: var(--font-plex-mono);
  color: var(--accent);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.sec-head__aside {
  font-family: var(--font-plex-mono);
  font-size: 12px;
  color: var(--tx-3);
}

.stack__intro {
  margin: 0 0 40px;
  max-width: 60ch;
  font-size: 17px;
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
  font-family: var(--font-plex-mono);
  font-size: 12px;
  color: var(--tx-3);
  border-right: 1px solid var(--line-2);
  background: var(--panel-2);
}
.layer__name {
  padding: 18px 20px;
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
  padding: 18px 22px;
  display: flex;
  align-items: center;
  font-size: 14px;
  color: var(--tx-2);
  line-height: 1.5;
}

.stack__footnote {
  margin: 20px 2px 0;
  font-family: var(--font-plex-mono);
  font-size: 12px;
  color: var(--tx-3);
  line-height: 1.6;
}

@media (max-width: 720px) {
  .stack { padding: 36px 0; }
  .stack__intro { margin-bottom: 22px; font-size: 14px; }
  .layer {
    grid-template-columns: 1fr;
    padding: 14px 15px;
    gap: 5px;
  }
  .layer__z {
    justify-content: flex-start;
    border-right: none;
    background: transparent;
    font-size: 11px;
  }
  .layer__name {
    flex-direction: row;
    align-items: baseline;
    gap: 10px;
    padding: 0;
    border-right: none;
  }
  .layer__detail { padding: 0; font-size: 12.5px; }
}
</style>
