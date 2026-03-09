<script setup>
defineProps({
  show: { type: Boolean, required: true },
})

const emit = defineEmits(['close'])
</script>

<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      style="background: rgba(0,0,0,0.6);"
      @click.self="emit('close')"
    >
      <div
        class="w-full max-w-sm rounded-xl p-6 overflow-y-auto max-h-[90vh]"
        style="background: var(--color-bg-primary); border: 1px solid var(--color-border);"
        role="dialog"
        aria-modal="true"
        aria-label="Säännöt"
      >
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-semibold" style="color: var(--color-text-primary);">Ohjeet</h2>
          <button
            @click="emit('close')"
            class="p-1 rounded hover:bg-white/10 text-xl leading-none"
            style="color: var(--color-text-tertiary);"
            aria-label="Sulje"
          >✕</button>
        </div>

        <div class="text-sm space-y-4" style="color: var(--color-text-secondary);">
          <p>Löydä mahdollisimman monta sanaa seitsemästä annetusta kirjaimesta.</p>

          <div>
            <p class="font-medium mb-1" style="color: var(--color-text-primary);">Jokaisen sanan täytyy:</p>
            <ul class="space-y-1 list-none pl-0">
              <li>✦ Sisältää <span style="color: var(--color-accent);">oranssin keskikirjaimen</span></li>
              <li>✦ Olla vähintään 4 kirjainta pitkä</li>
              <li>✦ Koostua vain annetuista kirjaimista — samaa kirjainta voi käyttää useasti</li>
              <li>✦ Löytyä suomen kielen sanakirjasta (<a href="https://kaino.kotus.fi/sanat/nykysuomi/" target="_blank" rel="noopener" style="color: var(--color-accent); text-decoration: underline;">Kotus</a>)</li>
            </ul>
          </div>

          <div>
            <p class="font-medium mb-1" style="color: var(--color-text-primary);">Pisteytys:</p>
            <ul class="space-y-1 list-none pl-0">
              <li>✦ 4-kirjaiminen sana = 1 piste</li>
              <li>✦ Pidempi sana = pisteitä sanan pituuden verran</li>
              <li>✦ Pangrammi (kaikki 7 kirjainta käytetty) = +7 lisäpistettä</li>
            </ul>
          </div>

          <div>
            <p class="font-medium mb-1" style="color: var(--color-text-primary);">Yhdyssanat:</p>
            <p>Yhdysviivallisen sanan voi kirjoittaa myös ilman viivaa — esim. <span style="font-family: var(--font-mono);">palo-ovi</span> tai <span style="font-family: var(--font-mono);">paloovi</span>.</p>
          </div>

          <div>
            <p class="font-medium mb-1" style="color: var(--color-text-primary);">Tasot:</p>
            <p>Pisteesi määrittävät tason. Tavoittele tasoa <span style="color: var(--color-accent);">Ällistyttävä</span>!</p>
          </div>

          <div>
            <p class="font-medium mb-1" style="color: var(--color-text-primary);">💡 Avut:</p>
            <p>Neljä vihjettä, jotka jäävät auki koko pelin ajaksi.</p>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
