<script setup>
definePageMeta({
  layout: 'standalone',
})

const userAgent = 'erez.ac-dog-show-browser/1.0 (+https://erez.ac/dog/about-crawler)'

useHead({
  title: 'Dog show crawler | erez.ac',
  meta: [
    {
      name: 'description',
      content: 'Plain-language information in Finnish and English about the erez.ac dog show crawler.',
    },
    { property: 'og:title', content: 'Dog show crawler | erez.ac' },
    {
      property: 'og:description',
      content: 'Why the erez.ac dog show crawler exists, what it reads, and how its request volume is limited.',
    },
    { property: 'og:url', content: 'https://erez.ac/dog/about-crawler' },
  ],
})
</script>

<template>
  <main class="crawler-page">
    <header class="crawler-header">
      <nav class="crawler-nav" aria-label="Page links">
        <NuxtLink to="/">erez.ac</NuxtLink>
        <NuxtLink to="/dog">/dog</NuxtLink>
      </nav>

      <p class="crawler-kicker">erez.ac / dog</p>
      <h1>Dog show crawler</h1>
      <p class="crawler-lead">
        Sivu selittää miten erez.ac:n näyttelytulosten hakuohjelma toimii. This page explains how the erez.ac dog show browser gets its public Showlink data.
      </p>

      <dl class="crawler-agent">
        <div>
          <dt>User-Agent</dt>
          <dd>{{ userAgent }}</dd>
        </div>
      </dl>
    </header>

    <div class="crawler-languages">
      <section class="crawler-section" lang="fi" aria-labelledby="crawler-fi-title">
        <p class="crawler-language-label">Suomeksi</p>
        <h2 id="crawler-fi-title">Näyttelytulosten hakuohjelma</h2>

        <h3>Miksi se on olemassa</h3>
        <p>
          <NuxtLink to="/dog">erez.ac/dog</NuxtLink>-sivun idea on tarjota parempi käyttöliittymä
          ja monipuolisemmat hakujen suodatusmahdollisuudet Kennelliiton näyttelytuloksiin. Jotta
          suodatusta voidaan tarjota tehokkaasti, täytyy tiedot hakea etukäteen välimuistiin.
          Botti hoitaa juuri tämän. Kun botti on rauhalliseen tahtiin käynyt datan hakemassa,
          ei kävijöiden haut ja suodatukset aiheuta enää pyyntöjä Showlinkin tulospalveluun, vaan
          data tarjoillaan suoraan erez.ac:n palvelimelta.
        </p>

        <h3>Mitä botti tekee?</h3>
        <ul>
          <li>Hakee julkisen näyttelylistan.</li>
          <li>Hakee näyttelyiden julkiset rotulistat ja koiramäärät.</li>
          <li>Hakee julkiset rotukohtaiset tulossivut, jotta /dog voi näyttää ja suodattaa tuloksia.</li>
          <li>Tekee pyynnöt rauhallisessa rytmissä, mahdollisuuksien mukaan ennakkoon.</li>
        </ul>

        <h3>Mitä botti ei tee?</h3>
        <ul>
          <li>Se ei kirjaudu sisään eikä hae ei-julkista tietoa.</li>
          <li>Se ei yritä kiertää sivuston rajoituksia.</li>
          <li>Se ei tee jatkuvaa massahakua, vaan rajoitetun määrän pyyntöjä tietyllä aikavälillä.</li>
          <li>Sen tarkoitus ei ole aiheuttaa haittaa Showlinkin palvelimille tai käyttäjille.</li>
        </ul>

        <h3>Miten pyyntöjen määrä on rajattu?</h3>
        <p>
          Suurin yksittäinen työ on kokonaisen näyttelyn tulosten tallentaminen välimuistiin. Se
          tarkoittaa yhtä sivupyyntöä jokaista rotua kohti. Jos suuressa näyttelyssä olisi 300 rotua,
          haku olisi noin 300 sivupyyntöä. Niin paljoa ei haeta kerralla, sillä se voisi aiheuttaa
          hetkellistä hitautta sivuston muille käyttäjille. Pyyntöjä Showlinkin palvelimelle tehdäänkin
          enintään 3 rinnakkain, pitäen vähintään 0,4 sekunnin väli pyynnöille. Kun näyttely on
          kertaalleen haettu ja tallennettu erez.ac:n välimuistiin, tieto tarjoillaan /dog-sivun
          käyttäjille erez.ac:n välimuistista. Käynnissä olevien näyttelyiden välimuistia tarkistetaan
          kuitenkin uudelleen, jotta päivän aikana päivittyvät tulokset näkyvät sivulla.
        </p>
        <ul>
          <li>Kävijä haluaa välimuistista löytymättömän näyttelyn tulostiedot: Haku suoritetaan enintään
            yksi näyttely kerrallaan, yllä mainituin ryppäin.</li>
          <li>Automaattinen tuoreiden näyttelyiden välimuisti: Hakuja suoritetaan enintään 2 näyttelyn 
            tietoihin yhden ajon aikana; uusi ajo alkaa aikaisintaan 2 minuutin välein ja vain, jos
            kukaan kävijä ei odota tulostietoja ennestään. Käynnissä olevien näyttelyiden tulosvälimuisti
            vanhenee oletuksena 2 minuutissa.</li>
          <li>Rotulistat: Enintään 6 näyttelyn tiedot haetaan noin 15 minuutin välein.</li>
          <li>Näyttelylista: Haetaan uudelleen aikaisintaan 30 minuutin välein.</li>
          <li>Tulevista näyttelyistä haetaan rotulistat. Tuloslistoja aletaan kysellä näyttelypäivänä
            klo 6:00 aamulla alkaen.
          </li>
        </ul>

        <h3>Kuka on vastuussa?</h3>
        <p>
          Hakusivustoa ylläpitää Konsta Janhunen. Lisätiedot ja yhteystiedot löytyvät
          <NuxtLink to="/">erez.ac</NuxtLink>-pääsivulta. Mikäli mitään kysyttävää herää, älä epäröi
          ottaa yhteyttä!
        </p>
      </section>

      <section class="crawler-section" lang="en" aria-labelledby="crawler-en-title">
        <p class="crawler-language-label">English</p>
        <h2 id="crawler-en-title">Dog show result crawler</h2>

        <h3>Why it exists</h3>
        <p>
          The idea behind <NuxtLink to="/dog">erez.ac/dog</NuxtLink> is to offer a better interface
          and more flexible search filters for Kennelliitto dog show results. To make that filtering
          work efficiently, the data needs to be fetched into a cache in advance. That is exactly
          what this bot does. Once the bot has collected the data at a calm pace, visitor searches
          and filters no longer create requests to Showlink's result service; the data is served
          directly from the erez.ac server.
        </p>

        <h3>What the bot does</h3>
        <ul>
          <li>Fetches the public show list.</li>
          <li>Fetches public breed lists and dog counts for shows.</li>
          <li>Fetches public breed-level result pages, so /dog can show and filter results.</li>
          <li>Makes requests at a calm pace, in advance where possible.</li>
        </ul>

        <h3>What the bot does not do</h3>
        <ul>
          <li>It does not log in or fetch non-public information.</li>
          <li>It does not try to bypass the site's limits.</li>
          <li>It does not run a continuous mass crawl; it makes a limited number of requests within a fixed time window.</li>
          <li>It is not intended to cause trouble for Showlink's servers or users.</li>
        </ul>

        <h3>How request volume is limited</h3>
        <p>
          The largest single job is saving all results for one show into the cache. That means one
          page request for each breed. If a large show had 300 breeds, that would mean about 300 page
          requests. They are not all fetched at once, because that could briefly slow the site down
          for other users. Requests to Showlink are therefore limited to at most 3 in parallel, with
          at least 0.4 seconds between request starts. Once a show has been fetched once and saved in
          the erez.ac cache, /dog users receive the data from the erez.ac cache. For currently ongoing
          shows, the cache is checked again so results that arrive during the day can appear on the page.
        </p>
        <ul>
          <li>A visitor wants result data for a show that is not yet cached: The fetch is run for at most one show at a time, in the batches described above.</li>
          <li>Automatic cache for recent shows: Data is fetched for at most 2 shows during one run; a new run starts no sooner than every 2 minutes and only if no visitor is already waiting for result data. Result caches for currently ongoing shows expire after 2 minutes by default.</li>
          <li>Breed lists: Data for at most 6 shows is fetched about every 15 minutes.</li>
          <li>Show list: Fetched again no sooner than every 30 minutes.</li>
          <li>For upcoming shows, breed lists are fetched. Result lists are first checked on the show day, starting at 6:00 in the morning.</li>
        </ul>

        <h3>Who is responsible?</h3>
        <p>
          The search page is maintained by Konsta Janhunen. More information and contact details are
          available on the <NuxtLink to="/">erez.ac</NuxtLink> main page. If you have any questions,
          please do not hesitate to get in touch!
        </p>
      </section>
    </div>
  </main>
</template>

<style scoped>
.crawler-page {
  --crawler-bg: #edf5ef;
  --crawler-surface: #fffdfb;
  --crawler-surface-strong: #dfece5;
  --crawler-text: #16231f;
  --crawler-muted: #5d6a64;
  --crawler-accent: #11624f;
  --crawler-accent-2: #9b365d;
  --crawler-border: #c9d8d0;
  --crawler-code-bg: #16231f;
  --crawler-code-text: #f8fff9;

  min-height: 100dvh;
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--crawler-bg) 82%, var(--crawler-accent) 18%) 0, var(--crawler-bg) 18rem),
    var(--crawler-bg);
  color: var(--crawler-text);
  font-family: 'DM Sans', sans-serif;
  padding: 1rem;
}

:where(.dark) .crawler-page {
  --crawler-bg: #0f1714;
  --crawler-surface: #16211d;
  --crawler-surface-strong: #22342d;
  --crawler-text: #eff7f3;
  --crawler-muted: #a7b9b0;
  --crawler-accent: #73e0c0;
  --crawler-accent-2: #ff9abd;
  --crawler-border: #314b42;
  --crawler-code-bg: #08110e;
  --crawler-code-text: #dffcf1;
}

.crawler-header,
.crawler-languages {
  width: min(100%, 1040px);
  margin: 0 auto;
}

.crawler-header {
  padding: 1rem 0 1.25rem;
}

.crawler-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 2.5rem;
}

.crawler-nav a,
.crawler-section a {
  color: var(--crawler-accent);
  font-weight: 700;
  text-decoration-thickness: 0.08em;
  text-underline-offset: 0.18em;
}

.crawler-nav a:hover,
.crawler-section a:hover {
  color: var(--crawler-accent-2);
}

.crawler-kicker,
.crawler-language-label {
  margin: 0 0 0.55rem;
  color: var(--crawler-accent-2);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.crawler-header h1 {
  margin: 0;
  color: var(--crawler-accent);
  font-size: clamp(2.2rem, 7vw, 4.8rem);
  line-height: 0.95;
  letter-spacing: 0;
}

.crawler-lead {
  max-width: 42rem;
  margin: 1rem 0 0;
  color: var(--crawler-muted);
  font-size: 1.05rem;
  line-height: 1.6;
}

.crawler-agent {
  margin: 1.25rem 0 0;
}

.crawler-agent div {
  display: grid;
  gap: 0.4rem;
  max-width: 46rem;
  padding: 0.85rem 1rem;
  background: var(--crawler-code-bg);
  color: var(--crawler-code-text);
  border-radius: 0.5rem;
}

.crawler-agent dt {
  color: color-mix(in srgb, var(--crawler-code-text) 70%, transparent);
  font-size: 0.75rem;
  font-weight: 800;
  text-transform: uppercase;
}

.crawler-agent dd {
  margin: 0;
  font-family: 'Commit Mono', monospace;
  font-size: 0.9rem;
  overflow-wrap: anywhere;
}

.crawler-languages {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1rem;
  padding-bottom: 3rem;
}

.crawler-section {
  background: var(--crawler-surface);
  border: 1px solid var(--crawler-border);
  border-radius: 0.5rem;
  padding: 1.15rem;
  box-shadow: 0 10px 28px -22px rgba(19, 55, 47, 0.34);
}

.crawler-section h2 {
  margin: 0 0 1.25rem;
  color: var(--crawler-accent);
  font-size: 1.65rem;
  line-height: 1.15;
  letter-spacing: 0;
}

.crawler-section h3 {
  margin: 1.4rem 0 0.45rem;
  color: var(--crawler-text);
  font-size: 1rem;
  font-weight: 800;
  letter-spacing: 0;
}

.crawler-section p,
.crawler-section li {
  color: var(--crawler-muted);
  line-height: 1.65;
}

.crawler-section p {
  margin: 0.65rem 0 0;
}

.crawler-section ul {
  display: grid;
  gap: 0.45rem;
  list-style: disc;
  margin: 0.65rem 0 0;
  padding-left: 1.35rem;
}

.crawler-section li::marker {
  color: var(--crawler-accent-2);
}

@media (min-width: 860px) {
  .crawler-page {
    padding: 1.5rem;
  }

  .crawler-header {
    padding-top: 1.5rem;
    padding-bottom: 1.75rem;
  }

  .crawler-languages {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1.25rem;
  }

  .crawler-section {
    padding: 1.35rem;
  }
}
</style>
