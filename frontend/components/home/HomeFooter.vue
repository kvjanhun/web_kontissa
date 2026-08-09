<script setup>
const i18n = useI18nStore()
const { t, tm } = i18n

const { linkIcon, isExternal } = useLinkIcon()

// Baked into the prerendered HTML at build time, then corrected on hydration if the
// year has since rolled over — so a January visitor sees the right year even if the
// site hasn't been redeployed yet.
const currentYear = new Date().getFullYear()

const connectLinks = computed(() => tm('home.footer.connectLinks') || [])
const siteLinks = computed(() => tm('home.footer.siteLinks') || [])
</script>

<template>
  <footer class="ftr">
    <div class="ftr__grid">
      <div class="ftr__about">
        <div class="ftr__brand">erez<span class="ftr__accent">.ac</span></div>
        <p class="ftr__blurb">{{ t('home.footer.blurb') }}</p>
      </div>

      <div class="ftr__col">
        <span class="ftr__col-label">{{ t('home.footer.connect') }}</span>
        <a
          v-for="l in connectLinks"
          :key="l.label"
          :href="l.href"
          class="ftr__link"
          :target="isExternal(l.href) ? '_blank' : undefined"
          :rel="isExternal(l.href) ? 'noopener noreferrer' : undefined"
        ><Icon class="ftr__link-icon" :name="linkIcon(l.href)" aria-hidden="true" />{{ l.label }}</a>
      </div>

      <div class="ftr__col">
        <span class="ftr__col-label">{{ t('home.footer.site') }}</span>
        <a
          v-for="l in siteLinks"
          :key="l.label"
          :href="l.href"
          class="ftr__link"
          :target="isExternal(l.href) ? '_blank' : undefined"
          :rel="isExternal(l.href) ? 'noopener noreferrer' : undefined"
        ><Icon class="ftr__link-icon" :name="linkIcon(l.href)" aria-hidden="true" />{{ l.label }}</a>
        <span class="ftr__nuc">{{ t('home.footer.nuc') }}</span>
      </div>
    </div>
    <!-- {year} is interpolated so the DB value never has to be edited in January.
         No-op against a value that hardcodes the year, so this ships independently
         of the admin edit that introduces the placeholder. -->
    <div class="ftr__copyright">{{ t('home.footer.copyright', { year: currentYear }) }}</div>
  </footer>
</template>

<style scoped>
.ftr {
  border-top: 1px solid var(--line);
  background: var(--bg-2);
}
.ftr__grid {
  max-width: 1180px;
  margin: 0 auto;
  padding: 54px 28px;
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr;
  gap: 30px;
}
.ftr__brand {
  font-family: var(--font-plex-mono);
  font-weight: 600;
  font-size: 16px;
}
.ftr__accent { color: var(--accent); }
.ftr__blurb {
  margin: 14px 0 0;
  max-width: 36ch;
  font-size: 14px;
  color: var(--tx-2);
  line-height: 1.6;
  font-weight: 300;
}
.ftr__col {
  display: flex;
  flex-direction: column;
  gap: 11px;
}
.ftr__col-label {
  font-family: var(--font-plex-mono);
  font-size: 11px;
  color: var(--tx-3);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.ftr__link {
  font-size: 14px;
  color: var(--tx);
  text-decoration: none;
  width: fit-content;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  transition: color 0.15s ease;
}
.ftr__link:hover { color: var(--accent); }
.ftr__link-icon {
  font-size: 15px;
  color: var(--tx-3);
  flex: none;
  transition: color 0.15s ease;
}
.ftr__link:hover .ftr__link-icon { color: var(--accent); }
.ftr__nuc {
  font-size: 13px;
  color: var(--tx-3);
  font-family: var(--font-plex-mono);
}
.ftr__copyright {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 28px 40px;
  font-family: var(--font-plex-mono);
  font-size: 11px;
  color: var(--tx-3);
}

@media (max-width: 720px) {
  .ftr__grid {
    grid-template-columns: 1fr;
    padding: 30px 18px;
    gap: 22px;
  }
  .ftr__copyright { padding: 0 18px 40px; }
}
</style>
