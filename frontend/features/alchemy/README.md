# Alchemy (`/alchemy`)

Kingdom Come: Deliverance II alchemy reference. Two views on one route:

- **Recipes** — every recipe, searchable by name or ingredient, filterable by base liquid.
- **What can I brew?** — tick the ingredients you are carrying and it lists what they
  complete, plus what you are one ingredient away from.

Agent-facing rules live in [CLAUDE.md](CLAUDE.md).

## Dataset

`data/recipes.json` and `data/ingredients.json` are hand-authored and bundled into
the route chunk: **31 recipes (27 base game + 4 DLC), 28 ingredients**. 25 recipes
carry an `effect`; the six that do not are the two gunpowders, Soap, Moonshine,
Mandrake Decoction and Essential Oil.

A recipe carries `verified: true` only when **two independent sources agree** on its
base, ingredients, quantities **and** brewing steps. Anything else stays
`verified: false` and renders a visible "unverified" marker, because a wrong boil
count costs the player ingredients and makes the page worse than no page at all.

`verified` does **not** cover `effect` text, which is sourced separately (F below).

### Sources

| Key | Source | Covers |
|---|---|---|
| **A** | [KCD2 alchemy recipe list (gist)](https://gist.github.com/nickheyer/fa24767640bd508be66507f51b6f2c6d) | 28 recipes with steps |
| **B** | [PowerPyx](https://www.powerpyx.com/kingdom-come-deliverance-2-all-potions-alchemy-recipes/) | 26 potions with steps |
| **C** | [game-checklists.com, all 31 potions](https://game-checklists.com/kcd2/potions-checklist/) | the complete 31-recipe roster and ingredients; no steps |
| **D** | [Steam guide: all alchemy recipes](https://steamcommunity.com/sharedfiles/filedetails/?id=3421800409) | steps, including the DLC recipes |
| **F** | [Fextralife KCD2 wiki, Potions](https://kingdomcomedeliverance2.wiki.fextralife.com/Potions) | effect text only |

28 of 31 recipes are corroborated by at least two of A/B/C/D. The remaining three
have their **ingredients** confirmed by two sources but their **steps** by only one:

| Recipe | Steps from | Note |
|---|---|---|
| Decoction of St. Roch | A only | The fiddliest recipe in the set — raise/lower the cauldron without flipping the timer, then two bellows pulls. |
| Anti-Inflammatory Potion | D only | |
| Essential Oil | D only | D's ingredient header says 2× chamomile but its own step 1 says 3, and C says 3. The dataset uses 3. |

### Where the sources disagree

| Recipe | Disagreement | Which the dataset follows |
|---|---|---|
| Bowman's Brew | A ends "boil 3 turns, let cool"; B and D end "boil 1 turn with the bellows" | B + D win; A's "let cool" is dropped |
| Lion Perfume | A decants; B and D pour | B + D win — it pours |
| Soap | A says 1 thistle; B, C and D say 2 | 2 thistle |
| Fox (effect) | A claims +50% XP; F says Speech +3 and faster reading | F wins — A's remark looks like a different potion |
| Buck's Blood (effect) | A per-potion search summary said "sleep heals faster"; F says "+30% Stamina for 20 minutes" | F wins. "Sleep heals faster" is **Chamomile Decoction's** effect. |

**Counts in source headings are unreliable.** A's heading claims 31 recipes but it
enumerates 28. C's heading claims 28 base-game potions but lists 27. The real roster
is 27 base + 4 DLC = 31, which C's actual entries and D between them confirm.

Recipe **names** vary between sources without that counting as a conflict — B and D
write "Lion", "Mintha", "Bane"; C writes "Aesop Potion", "Scattershot Gunpowder",
"St. Roch's Potion". Verification is about the brewing data; the fuller names are
used here.

### Known gaps

- **Potion quality is not modelled.** KCD2 has weak / regular / strong (and Henry's,
  via the Secret of Secrets perk); regular needs all steps correct with dried
  ingredients, strong needs at least one fresh one. The `effect` field holds the
  standard-quality description only.
- Decoction of St. Roch calls specifically for **dried** chamomile in source C.
  Dried-vs-fresh drives that quality system, which the dataset does not track.
- The six recipes without an `effect` are absent from F. They are mostly crafting
  products (gunpowder, soap) rather than potions.

## Adding a recipe

1. Add any new ingredient to `data/ingredients.json` first — `id` kebab-case, a
   `category` from `herb | fungus | mineral | animal | other`, and `aliases` for
   names players actually type.
2. Add the recipe to `data/recipes.json`. Every ingredient must appear in at least
   one step's `uses`, each step's `uses` ids must be **named exactly once** in that
   step's prose (the inline highlighter counts on it), and the last step needs a
   `finish`. Set `dlc` to the DLC name if it is not base-game content.
3. `npm run test -- alchemy` — `validateDataset` will name anything inconsistent,
   and a whole-dataset test checks every step highlights what it declares.
4. Record the sources in the tables above.
