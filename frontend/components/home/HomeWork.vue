<script setup>
const i18n = useI18nStore()
const { t, tm } = i18n
const vReveal = useScrollReveal()

const projects = computed(() => tm('home.projects') || [])
const openIndex = ref(0)

function toggle(i) {
  openIndex.value = openIndex.value === i ? -1 : i
}
function projNum(i) {
  return String(i + 1).padStart(3, '0')
}
</script>

<template>
  <section id="work" class="work">
    <div class="sec-head">
      <h2 class="sec-head__label home-plate">01 — {{ t('home.work.label') }}</h2>
      <span class="sec-head__aside home-plate">{{ t('home.work.count', { count: projects.length }) }}</span>
    </div>

    <div class="proj-list" v-reveal>
      <div v-for="(p, i) in projects" :key="p.name" class="proj">
        <button
          class="proj__btn"
          type="button"
          :aria-expanded="openIndex === i"
          :aria-controls="`proj-panel-${i}`"
          @click="toggle(i)"
        >
          <span class="proj__num">{{ projNum(i) }}</span>
          <span class="proj__head home-plate">
            <span class="proj__title-row">
              <span class="proj__name">{{ p.name }}</span>
              <span class="proj__kind">{{ p.kind }}</span>
            </span>
            <span class="proj__tagline">{{ p.tagline }}</span>
          </span>
          <span class="proj__caret" :class="{ 'proj__caret--open': openIndex === i }" aria-hidden="true">+</span>
        </button>

        <div :id="`proj-panel-${i}`" class="proj__panel" :class="{ 'proj__panel--open': openIndex === i }">
          <div class="proj__panel-inner">
            <span class="proj__spacer" aria-hidden="true"></span>
            <div class="proj__detail home-plate">
              <p class="proj__desc">{{ p.description }}</p>
              <div class="proj__tech">
                <span v-for="tech in p.tech" :key="tech" class="tech-tag">{{ tech }}</span>
              </div>
              <div class="proj__links">
                <a v-for="l in p.links" :key="l.label" :href="l.href" class="proj__link">
                  {{ l.label }} <span class="proj__link-arrow" aria-hidden="true">→</span>
                </a>
              </div>
            </div>
            <div class="proj__shot" :class="{ 'proj__shot--filled': p.image }">
              <img
                v-if="p.image"
                class="proj__shot-img"
                :src="p.image"
                :alt="p.shot"
                loading="lazy"
                decoding="async"
              />
              <span class="proj__shot-cap">{{ p.shot }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.work { padding: 80px 0 40px; }

.sec-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 38px;
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

.proj-list {
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--line);
}
.proj { border-bottom: 1px solid var(--line); }

.proj__btn {
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  cursor: pointer;
  padding: 26px 4px;
  display: grid;
  grid-template-columns: 54px 1fr auto;
  gap: 24px;
  align-items: center;
  color: var(--tx);
}
.proj__num {
  font-family: var(--font-plex-mono);
  font-size: 12px;
  color: var(--tx-3);
}
.proj__head {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}
.proj__title-row {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.proj__name {
  font-size: clamp(22px, 2.6vw, 30px);
  font-weight: 600;
  letter-spacing: -0.02em;
}
.proj__kind {
  font-family: var(--font-plex-mono);
  font-size: 11px;
  color: var(--accent);
  border: 1px solid var(--accent-dim);
  background: var(--accent-dim);
  padding: 3px 9px;
  border-radius: 20px;
}
.proj__tagline {
  font-size: 15px;
  color: var(--tx-2);
  font-weight: 300;
}
.proj__caret {
  font-family: var(--font-plex-mono);
  font-size: 22px;
  color: var(--tx-3);
  transition: transform 0.25s ease;
  justify-self: end;
}
.proj__caret--open { transform: rotate(45deg); }

/* Accessible auto-height accordion via grid-template-rows */
.proj__panel {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.32s cubic-bezier(0.4, 0, 0.2, 1);
}
.proj__panel--open { grid-template-rows: 1fr; }
.proj__panel-inner {
  overflow: hidden;
  min-height: 0;
  display: grid;
  grid-template-columns: 54px 1.1fr 1fr;
  gap: 24px;
}
.proj__detail {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 34px;
}
.proj__desc {
  margin: 0;
  font-size: 15px;
  line-height: 1.65;
  color: var(--tx-2);
}
.proj__tech {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tech-tag {
  font-family: var(--font-plex-mono);
  font-size: 11px;
  color: var(--tx-2);
  border: 1px solid var(--line);
  padding: 4px 10px;
  border-radius: 5px;
}
.proj__links {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
}
.proj__link {
  font-family: var(--font-plex-mono);
  font-size: 13px;
  color: var(--tx);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border-bottom: 1px solid var(--accent);
  padding-bottom: 2px;
}
.proj__link-arrow { color: var(--accent); transition: transform 0.15s ease; }
.proj__link:hover .proj__link-arrow { transform: translateX(2px); }
.proj__shot {
  position: relative;
  aspect-ratio: 16 / 10;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
  background: repeating-linear-gradient(135deg, var(--panel), var(--panel) 9px, var(--panel-2) 9px, var(--panel-2) 18px);
  display: flex;
  align-items: flex-end;
  padding: 14px;
  margin-bottom: 34px;
}
/* When a real screenshot is present the stripe placeholder is replaced by a
   solid panel (shown only while the image decodes); the image fills the box. */
.proj__shot--filled { background: var(--panel-2); }
.proj__shot-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
}
.proj__shot-cap {
  position: relative;
  z-index: 1;
  font-family: var(--font-plex-mono);
  font-size: 11px;
  color: var(--tx-3);
  background: var(--bg);
  padding: 5px 9px;
  border-radius: 5px;
  border: 1px solid var(--line);
}

@media (max-width: 720px) {
  .work { padding: 34px 0 8px; }
  .sec-head { margin-bottom: 18px; }
  .proj__btn {
    grid-template-columns: auto 1fr auto;
    gap: 12px;
    padding: 18px 2px;
    align-items: start;
  }
  .proj__name { font-size: 21px; }
  .proj__panel-inner {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  .proj__spacer { display: none; }
  .proj__shot { order: -1; margin-bottom: 0; }
  .proj__detail { padding-bottom: 22px; }
}
</style>
