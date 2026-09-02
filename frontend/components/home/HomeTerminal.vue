<script setup>
const { t } = useI18nStore()
</script>

<template>
  <section id="terminal" class="terminal">
    <h2 class="sec-head home-plate">{{ t('home.terminal.label') }}</h2>

    <div class="term-frame">
      <div class="term-frame__bar">
        <span class="term-frame__dot term-frame__dot--red" aria-hidden="true"></span>
        <span class="term-frame__dot term-frame__dot--yellow" aria-hidden="true"></span>
        <span class="term-frame__dot term-frame__dot--green" aria-hidden="true"></span>
        <span class="term-frame__title">konsta@erez.ac: ~</span>
      </div>
      <div class="term-frame__body">
        <TerminalWindow :fill="true" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.terminal { padding: 40px 0 72px; }

.sec-head {
  margin: 0 0 20px;
  font-size: 13px;
  font-family: var(--font-plex-mono);
  color: var(--accent);
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.term-frame {
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  background: #0a0b0d;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.4);
}
.term-frame__bar {
  height: 40px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  background: #0e1013;
}
.term-frame__dot {
  width: 11px;
  height: 11px;
  border-radius: 50%;
}
.term-frame__dot--red { background: #ff5f57; }
.term-frame__dot--yellow { background: #febc2e; }
.term-frame__dot--green { background: #28c840; }
.term-frame__title {
  font-family: var(--font-plex-mono);
  font-size: 11px;
  color: #5a5d63;
  margin-left: 12px;
}
.term-frame__body {
  height: 320px;
  display: flex;
}
.term-frame__body > * { flex: 1; min-width: 0; }

@media (max-width: 720px) {
  .terminal { padding: 8px 0 40px; }
  .term-frame__body { height: 280px; }
}
</style>
