// Pure boundary for the /alchemy feature: search, matching, and dataset
// validation. Nothing here touches Vue, the router, or the network, so it is
// all directly testable — see ../../tests/unit/alchemyRecipes.test.js.

export const BASE_LIQUIDS = [
  { id: 'water', label: 'Water' },
  { id: 'wine', label: 'Wine' },
  { id: 'oil', label: 'Oil' },
  { id: 'spiritus', label: 'Spiritus' },
]

export const BASE_IDS = BASE_LIQUIDS.map((base) => base.id)

export const INGREDIENT_CATEGORIES = ['herb', 'fungus', 'mineral', 'animal', 'other']

// Finishing moves at the end of a brew. `grind` is the odd one out: gunpowder
// is poured into the mortar rather than a phial.
export const FINISH_METHODS = ['pour', 'distil', 'decant', 'grind']

const KEBAB_ID = /^[a-z0-9]+(-[a-z0-9]+)*$/

// Punctuation is stripped rather than escaped so that a typed "st johns wort"
// finds "St. John's Wort" without the user reproducing the apostrophe.
//
// Apostrophes are deleted outright, before the pass that turns punctuation into
// spaces: letting "john's" become "john s" would split a word in two and make
// that exact search miss.
export function normalizeText(value) {
  return String(value ?? '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/['\u2019\u02bc]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

export function baseLabel(baseId) {
  return BASE_LIQUIDS.find((base) => base.id === baseId)?.label || baseId || ''
}

/* Colour axes. Each returns a class that sets one CSS custom property, so the
   markup names the *meaning* and alchemy.css owns the palette. Three separate
   axes on purpose: an ingredient's category, a recipe's base liquid, and a
   brewing operation are unrelated things and must not share a scale. */

export function categoryClass(category) {
  return `al-cat-${INGREDIENT_CATEGORIES.includes(category) ? category : 'other'}`
}

export function baseClass(baseId) {
  return BASE_IDS.includes(baseId) ? `al-base-${baseId}` : ''
}

export function itemCategoryClass(item) {
  return categoryClass(item?.ingredient?.category)
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * Split a step's prose into plain-text and ingredient-name segments, so the
 * template can bold and colour the ingredient inline instead of leaving it to
 * blend into the sentence.
 *
 * Driven by the step's own `uses` ids rather than scanning every ingredient in
 * the recipe: a step that only grinds belladonna should not also highlight
 * nettle because the recipe happens to use it in a different step.
 *
 * Returns an array of `{ text }` (plain) and `{ text, category }` (matched)
 * segments. `items` is a decorated recipe's `items` (see decorateRecipes).
 */
export function highlightStepText(step, items) {
  const uses = step?.uses || []
  if (uses.length === 0) return [{ text: step?.text || '' }]

  // Longest name first, so "Boar's Tusk" is not pre-empted by a shorter partial
  // match before the alternation reaches it.
  const named = uses
    .map((id) => items.find((item) => item.id === id))
    .filter(Boolean)
    .sort((a, b) => b.name.length - a.name.length)
  if (named.length === 0) return [{ text: step?.text || '' }]

  const pattern = named.map((item) => escapeRegExp(item.name)).join('|')
  const re = new RegExp(`\\b(${pattern})\\b`, 'gi')
  const byLowerName = new Map(named.map((item) => [item.name.toLowerCase(), item]))

  return (step.text || '')
    .split(re)
    .filter((part) => part !== undefined && part !== '')
    .map((part) => {
      const item = byLowerName.get(part.toLowerCase())
      return item ? { text: part, category: item.ingredient?.category } : { text: part }
    })
}

export function indexIngredients(ingredients) {
  return new Map(ingredients.map((ingredient) => [ingredient.id, ingredient]))
}

export function sortIngredients(ingredients) {
  return [...ingredients].sort((left, right) => left.name.localeCompare(right.name))
}

/**
 * Resolve each recipe's ingredient ids to full ingredient objects and pre-build
 * the string the search box matches against. Done once at module load so
 * neither searching nor matching has to walk the ingredient list again.
 */
export function decorateRecipes(recipes, ingredients) {
  const byId = indexIngredients(ingredients)
  return recipes.map((recipe) => {
    const items = recipe.ingredients.map((entry) => ({
      ...entry,
      ingredient: byId.get(entry.id) || null,
      name: byId.get(entry.id)?.name || entry.id,
    }))
    const searchable = [recipe.name, baseLabel(recipe.base), ...items.map((item) => item.name)]
    return { ...recipe, items, searchText: normalizeText(searchable.join(' ')) }
  })
}

/**
 * `bases`, when given, is the set of base liquids to include — not a single
 * value to match. The base chip row is a toggle group (see useAlchemyBrowser's
 * `baseFilter`): every base starts included, and dropping one out of the set
 * narrows the list without ever collapsing to "show only this one".
 */
export function searchRecipes(recipes, query, { bases } = {}) {
  const needle = normalizeText(query)
  const included = bases instanceof Set ? bases : bases ? new Set(bases) : null
  return recipes.filter((recipe) => {
    if (included && !included.has(recipe.base)) return false
    return !needle || recipe.searchText.includes(needle)
  })
}

export function searchIngredients(ingredients, query) {
  const needle = normalizeText(query)
  if (!needle) return ingredients
  return ingredients.filter((ingredient) => {
    const haystack = normalizeText([ingredient.name, ...(ingredient.aliases || [])].join(' '))
    return haystack.includes(needle)
  })
}

export function findRecipe(recipes, id) {
  if (!id) return null
  return recipes.find((recipe) => recipe.id === id) || null
}

/**
 * Split the recipe list by what `heldIds` covers.
 *
 * Presence only — holding nettle at all satisfies a recipe calling for two of
 * them. The required counts still render on the card, but gating on them would
 * mean asking the player to count their inventory, which is the tedium this
 * page exists to remove.
 *
 * Base liquids are deliberately not part of the match: they are bought in bulk
 * for a few groschen, so treating them as scarce would only produce noise.
 */
export function matchRecipes(recipes, heldIds) {
  const held = heldIds instanceof Set ? heldIds : new Set(heldIds || [])
  const canBrew = []
  const oneShort = []
  if (held.size === 0) return { canBrew, oneShort }

  for (const recipe of recipes) {
    const missing = recipe.items.filter((item) => !held.has(item.id))
    if (missing.length === 0) canBrew.push(recipe)
    else if (missing.length === 1) oneShort.push({ ...recipe, missing: missing[0] })
  }
  return { canBrew, oneShort }
}

export function parseHeldIds(value, ingredients) {
  const known = new Set(ingredients.map((ingredient) => ingredient.id))
  const raw = Array.isArray(value) ? value.join(',') : String(value ?? '')
  return raw
    .split(',')
    .map((id) => id.trim())
    .filter((id) => known.has(id))
}

export function serializeHeldIds(heldIds) {
  return [...heldIds].sort().join(',')
}

/**
 * Referential integrity for the hand-authored dataset. Returns a list of
 * human-readable problems; an empty list means the data is coherent.
 *
 * This is the whole reason the steps carry structured `uses` hints alongside
 * their prose: a typo made while transcribing recipes fails the unit test
 * instead of quietly rendering a card that names an ingredient the recipe
 * never lists.
 */
export function validateDataset(recipes, ingredients) {
  const problems = []
  const seenIngredients = new Set()

  for (const ingredient of ingredients) {
    const where = `ingredient "${ingredient.id}"`
    if (!KEBAB_ID.test(ingredient.id || '')) problems.push(`${where}: id is not kebab-case`)
    if (seenIngredients.has(ingredient.id)) problems.push(`${where}: duplicate id`)
    seenIngredients.add(ingredient.id)
    if (!ingredient.name) problems.push(`${where}: missing name`)
    if (!INGREDIENT_CATEGORIES.includes(ingredient.category)) {
      problems.push(`${where}: unknown category "${ingredient.category}"`)
    }
  }

  const seenRecipes = new Set()
  for (const recipe of recipes) {
    const where = `recipe "${recipe.id}"`
    if (!KEBAB_ID.test(recipe.id || '')) problems.push(`${where}: id is not kebab-case`)
    if (seenRecipes.has(recipe.id)) problems.push(`${where}: duplicate id`)
    seenRecipes.add(recipe.id)
    if (!recipe.name) problems.push(`${where}: missing name`)
    if (!BASE_IDS.includes(recipe.base)) problems.push(`${where}: unknown base "${recipe.base}"`)
    if (recipe.dlc !== undefined && (typeof recipe.dlc !== 'string' || !recipe.dlc)) {
      problems.push(`${where}: dlc must be a non-empty name when present`)
    }

    const entries = recipe.ingredients || []
    if (entries.length === 0) problems.push(`${where}: no ingredients`)
    const declared = new Set()
    for (const entry of entries) {
      if (!seenIngredients.has(entry.id)) problems.push(`${where}: unknown ingredient "${entry.id}"`)
      if (declared.has(entry.id)) problems.push(`${where}: ingredient "${entry.id}" listed twice`)
      declared.add(entry.id)
      if (!Number.isInteger(entry.qty) || entry.qty < 1) {
        problems.push(`${where}: ingredient "${entry.id}" has a bad qty`)
      }
    }

    const steps = recipe.steps || []
    if (steps.length === 0) problems.push(`${where}: no steps`)
    let hasFinish = false
    steps.forEach((step, i) => {
      if (!step.text) problems.push(`${where}: step ${i + 1} has no text`)
      for (const used of step.uses || []) {
        if (!declared.has(used)) {
          problems.push(`${where}: step ${i + 1} uses "${used}", which the recipe does not list`)
        }
      }
      if (step.turns !== undefined && (!Number.isInteger(step.turns) || step.turns < 1)) {
        problems.push(`${where}: step ${i + 1} has a bad turn count`)
      }
      for (const flag of ['grind', 'bellows']) {
        if (step[flag] !== undefined && typeof step[flag] !== 'boolean') {
          problems.push(`${where}: step ${i + 1} has a non-boolean "${flag}"`)
        }
      }
      if (step.finish) {
        hasFinish = true
        if (!FINISH_METHODS.includes(step.finish)) {
          problems.push(`${where}: step ${i + 1} has an unknown finish "${step.finish}"`)
        }
      }
    })
    if (!hasFinish) problems.push(`${where}: no finishing step`)

    // Every listed ingredient should be accounted for by the written steps —
    // otherwise the card tells you to fetch something the instructions never use.
    for (const entry of entries) {
      const used = steps.some((step) => (step.uses || []).includes(entry.id))
      if (!used) problems.push(`${where}: ingredient "${entry.id}" appears in no step`)
    }
  }

  return problems
}
