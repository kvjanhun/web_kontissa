import { describe, expect, it } from 'vitest'
import ingredients from '~/features/alchemy/data/ingredients.json'
import recipes from '~/features/alchemy/data/recipes.json'
import {
  baseClass,
  categoryClass,
  decorateRecipes,
  findRecipe,
  highlightStepText,
  INGREDIENT_CATEGORIES,
  itemCategoryClass,
  matchRecipes,
  normalizeText,
  parseHeldIds,
  searchIngredients,
  searchRecipes,
  serializeHeldIds,
  validateDataset,
} from '~/features/alchemy/alchemyRecipes.js'

const decorated = decorateRecipes(recipes, ingredients)

describe('validateDataset', () => {
  it('finds no problems in the shipped dataset', () => {
    expect(validateDataset(recipes, ingredients)).toEqual([])
  })

  it('catches a step naming an ingredient the recipe does not list', () => {
    const broken = [{
      ...recipes[0],
      steps: [{ text: 'Add sage.', uses: ['sage'] }, { text: 'Pour.', finish: 'pour' }],
    }]
    expect(validateDataset(broken, ingredients).join(' ')).toContain('which the recipe does not list')
  })

  it('catches an unknown ingredient id', () => {
    const broken = [{ ...recipes[0], ingredients: [{ id: 'moon-dust', qty: 1 }] }]
    expect(validateDataset(broken, ingredients).join(' ')).toContain('unknown ingredient "moon-dust"')
  })

  it('catches an ingredient that no step ever uses', () => {
    const broken = [{
      ...recipes[0],
      ingredients: [...recipes[0].ingredients, { id: 'cobweb', qty: 1 }],
    }]
    expect(validateDataset(broken, ingredients).join(' ')).toContain('appears in no step')
  })

  it('catches an unknown base liquid', () => {
    const broken = [{ ...recipes[0], base: 'mead' }]
    expect(validateDataset(broken, ingredients).join(' ')).toContain('unknown base "mead"')
  })
})

describe('normalizeText', () => {
  it('drops apostrophes instead of splitting the word', () => {
    expect(normalizeText("St. John's Wort")).toBe('st johns wort')
    expect(normalizeText("Boar's Tusk")).toBe('boars tusk')
  })

  it('folds case and diacritics', () => {
    expect(normalizeText('Näyttely')).toBe('nayttely')
  })
})

describe('searchIngredients', () => {
  it('matches without the punctuation the real name carries', () => {
    expect(searchIngredients(ingredients, 'st johns wort').map((i) => i.name)).toEqual(["St. John's Wort"])
  })

  it('matches on an alias', () => {
    expect(searchIngredients(ingredients, 'fly agaric').map((i) => i.name)).toEqual(['Amanita Muscaria'])
    expect(searchIngredients(ingredients, 'calendula').map((i) => i.name)).toEqual(['Marigold'])
  })

  it('returns everything for an empty query', () => {
    expect(searchIngredients(ingredients, '   ')).toHaveLength(ingredients.length)
  })

  it('returns nothing for a query that matches no ingredient', () => {
    expect(searchIngredients(ingredients, 'dragon scale')).toEqual([])
  })
})

describe('searchRecipes', () => {
  it('matches on the recipe name', () => {
    expect(searchRecipes(decorated, 'schnapps').map((r) => r.id)).toEqual(['saviour-schnapps'])
  })

  it('matches on an ingredient the recipe uses', () => {
    const ids = searchRecipes(decorated, 'nettle').map((r) => r.id)
    expect(ids).toContain('marigold-decoction')
    expect(ids).toContain('digestive-potion')
  })

  it('narrows to the included base liquids', () => {
    const wine = searchRecipes(decorated, '', { bases: new Set(['wine']) })
    expect(wine.every((r) => r.base === 'wine')).toBe(true)
    expect(wine.length).toBeGreaterThan(0)
  })

  it('accepts a plain array as well as a Set', () => {
    const oilAndWater = searchRecipes(decorated, '', { bases: ['oil', 'water'] })
    expect(oilAndWater.every((r) => r.base === 'oil' || r.base === 'water')).toBe(true)
  })

  it('applies query and bases together', () => {
    // Nettle appears in several bases, so the base set has to actually narrow it.
    const anyBase = searchRecipes(decorated, 'nettle').map((r) => r.id)
    const oilOnly = searchRecipes(decorated, 'nettle', { bases: new Set(['oil']) })
    expect(oilOnly.every((r) => r.base === 'oil')).toBe(true)
    expect(oilOnly.length).toBeLessThan(anyBase.length)
    expect(searchRecipes(decorated, 'nettle', { bases: new Set(['spiritus']) })).toEqual([])
  })

  it('an unset `bases` filter matches every base, same as omitting it', () => {
    expect(searchRecipes(decorated, '', { bases: undefined })).toHaveLength(decorated.length)
  })
})

describe('matchRecipes', () => {
  it('returns both lists empty when nothing is selected', () => {
    expect(matchRecipes(decorated, [])).toEqual({ canBrew: [], oneShort: [] })
  })

  it('matches on presence, ignoring the required counts', () => {
    // Marigold Decoction wants 2× marigold; holding the herb at all is enough.
    const { canBrew } = matchRecipes(decorated, ['nettle', 'marigold'])
    expect(canBrew.map((r) => r.id)).toContain('marigold-decoction')
  })

  it('reports a recipe missing exactly one ingredient, and which', () => {
    const { canBrew, oneShort } = matchRecipes(decorated, ['nettle'])
    expect(canBrew).toEqual([])
    const schnapps = oneShort.find((r) => r.id === 'saviour-schnapps')
    expect(schnapps.missing.id).toBe('belladonna')
  })

  it('leaves out a recipe missing two or more ingredients', () => {
    const { canBrew, oneShort } = matchRecipes(decorated, ['nettle'])
    expect([...canBrew, ...oneShort].map((r) => r.id)).not.toContain('aesop')
  })

  it('returns nothing when the held ingredients complete no recipe', () => {
    // Cobweb only appears in Quickfinger Potion, which also needs valerian and
    // eyebright — two short, so it lands in neither bucket.
    expect(matchRecipes(decorated, ['cobweb'])).toEqual({ canBrew: [], oneShort: [] })
  })
})

describe('held id round-trip', () => {
  it('drops ids that are not real ingredients', () => {
    expect(parseHeldIds('nettle,moon-dust,sage', ingredients)).toEqual(['nettle', 'sage'])
  })

  it('handles an empty and an undefined value', () => {
    expect(parseHeldIds('', ingredients)).toEqual([])
    expect(parseHeldIds(undefined, ingredients)).toEqual([])
  })

  it('serializes in a stable order so the URL does not churn', () => {
    expect(serializeHeldIds(['sage', 'nettle'])).toBe('nettle,sage')
    expect(serializeHeldIds(['nettle', 'sage'])).toBe('nettle,sage')
  })
})

describe('findRecipe', () => {
  it('finds by id and returns null for anything else', () => {
    expect(findRecipe(decorated, 'artemisia').name).toBe('Artemisia')
    expect(findRecipe(decorated, 'nope')).toBeNull()
    expect(findRecipe(decorated, undefined)).toBeNull()
  })
})

describe('colour axes', () => {
  it('maps each ingredient category to its own class', () => {
    expect(categoryClass('herb')).toBe('al-cat-herb')
    expect(categoryClass('mineral')).toBe('al-cat-mineral')
    expect(categoryClass('animal')).toBe('al-cat-animal')
  })

  it('falls back to "other" for a missing or unknown category', () => {
    expect(categoryClass(undefined)).toBe('al-cat-other')
    expect(categoryClass('mythical')).toBe('al-cat-other')
  })

  it('maps each base liquid to its own class, and unknown bases to none', () => {
    expect(baseClass('spiritus')).toBe('al-base-spiritus')
    expect(baseClass('wine')).toBe('al-base-wine')
    expect(baseClass('mead')).toBe('')
  })

  it('reads the category off a decorated recipe item', () => {
    const schnapps = findRecipe(decorated, 'saviour-schnapps')
    expect(itemCategoryClass(schnapps.items[0])).toBe('al-cat-herb')
    const aesop = findRecipe(decorated, 'aesop')
    const tusk = aesop.items.find((item) => item.id === 'boars-tusk')
    expect(itemCategoryClass(tusk)).toBe('al-cat-animal')
  })

  it('no ingredient in the dataset lands on the fallback by accident', () => {
    // categoryClass() quietly maps anything unknown to 'other', so assert on the
    // declared category instead: a typo must not slip through as a real colour.
    const declared = ingredients.map((ingredient) => ingredient.category)
    expect(declared.every((c) => INGREDIENT_CATEGORIES.includes(c))).toBe(true)
  })

  it('every base liquid used by a recipe has a class', () => {
    for (const recipe of recipes) {
      expect(baseClass(recipe.base)).toBe(`al-base-${recipe.base}`)
    }
  })
})

describe('highlightStepText', () => {
  const aesop = findRecipe(decorated, 'aesop')

  it('splits plain text around each used ingredient, case-insensitively', () => {
    const step = aesop.steps[0] // "Grind comfrey and add it to the cauldron."
    const parts = highlightStepText(step, aesop.items)
    const hit = parts.find((p) => p.category)
    expect(hit).toBeTruthy()
    expect(hit.text.toLowerCase()).toBe('comfrey')
    expect(hit.category).toBe('herb')
    expect(parts.map((p) => p.text).join('')).toBe(step.text)
  })

  it('matches a name containing an apostrophe with a word boundary', () => {
    const step = aesop.steps[1] // "Add the boar's tusk and boil for 2 turns."
    const parts = highlightStepText(step, aesop.items)
    const hit = parts.find((p) => p.category)
    expect(hit.text.toLowerCase()).toBe("boar's tusk")
    expect(hit.category).toBe('animal')
  })

  it('only highlights the ingredient(s) this step declares in `uses`', () => {
    // Aesop's belladonna step must not also highlight comfrey or boar's tusk,
    // even though both appear elsewhere in the same recipe.
    const step = aesop.steps[2] // "Grind belladonna and add it to the cauldron."
    const parts = highlightStepText(step, aesop.items)
    expect(parts.filter((p) => p.category)).toHaveLength(1)
    expect(parts.find((p) => p.category).text.toLowerCase()).toBe('belladonna')
  })

  it('returns the text untouched when the step uses nothing', () => {
    const step = { text: 'Pour into a phial.', finish: 'pour' }
    expect(highlightStepText(step, aesop.items)).toEqual([{ text: 'Pour into a phial.' }])
  })

  it('every step across the dataset highlights all of its declared ingredients', () => {
    for (const recipe of decorated) {
      for (const step of recipe.steps) {
        const parts = highlightStepText(step, recipe.items)
        expect(parts.filter((p) => p.category)).toHaveLength((step.uses || []).length)
        expect(parts.map((p) => p.text).join('')).toBe(step.text)
      }
    }
  })
})
