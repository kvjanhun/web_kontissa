import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from '#app'
import ingredientsData from './data/ingredients.json'
import recipesData from './data/recipes.json'
import {
  BASE_IDS,
  decorateRecipes,
  findRecipe,
  matchRecipes,
  parseHeldIds,
  searchIngredients,
  searchRecipes,
  serializeHeldIds,
  sortIngredients,
} from './alchemyRecipes.js'

const HELD_STORAGE_KEY = 'alchemy:have'

// Decorated once at module load: the dataset is bundled, so there is nothing to
// fetch and no reason to redo the ingredient join per component instance.
const ALL_RECIPES = decorateRecipes(recipesData, ingredientsData)
const ALL_INGREDIENTS = sortIngredients(ingredientsData)

function readStoredHeld() {
  try {
    return window.localStorage.getItem(HELD_STORAGE_KEY) || ''
  } catch {
    // Private browsing and blocked site data both throw here. An empty
    // selection is a perfectly good starting point, so this is not worth surfacing.
    return ''
  }
}

function writeStoredHeld(value) {
  try {
    window.localStorage.setItem(HELD_STORAGE_KEY, value)
  } catch {
    // See readStoredHeld — losing the convenience is not worth an error state.
  }
}

export function useAlchemyBrowser() {
  const route = useRoute()
  const router = useRouter()

  // The page is pre-rendered without a query string, so any view driven by
  // `?recipe=` or `?have=` would disagree with the server HTML on first paint.
  // Rendering the plain recipe list until mount keeps hydration clean; deep
  // links resolve a tick later.
  const ready = ref(false)

  const recipeQuery = ref('')
  // A toggle group, not a single choice: every base liquid starts included, and
  // clicking one drops it out of the set rather than narrowing to just that one.
  // "All" is not a distinct state — it is just the full set restored.
  const baseFilter = ref(new Set(BASE_IDS))
  const ingredientQuery = ref('')
  const heldIds = ref([])

  const heldSet = computed(() => new Set(heldIds.value))
  const selectedCount = computed(() => heldIds.value.length)

  const selectedRecipe = computed(() => {
    if (!ready.value) return null
    const id = route.query.recipe
    return findRecipe(ALL_RECIPES, Array.isArray(id) ? id[0] : id)
  })

  const view = computed(() => {
    if (!ready.value) return 'list'
    if (selectedRecipe.value) return 'detail'
    if (route.query.tab === 'brew' || route.query.have !== undefined) return 'matcher'
    return 'list'
  })

  const allBasesSelected = computed(() => baseFilter.value.size === BASE_IDS.length)

  const visibleRecipes = computed(() =>
    searchRecipes(ALL_RECIPES, recipeQuery.value, { bases: baseFilter.value }),
  )

  function toggleBase(id) {
    const next = new Set(baseFilter.value)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    baseFilter.value = next
  }

  function selectAllBases() {
    baseFilter.value = new Set(BASE_IDS)
  }

  const visibleIngredients = computed(() =>
    searchIngredients(ALL_INGREDIENTS, ingredientQuery.value),
  )

  const matches = computed(() => matchRecipes(ALL_RECIPES, heldSet.value))

  function syncHeldFromRoute() {
    const raw = route.query.have
    if (raw === undefined) return false
    heldIds.value = parseHeldIds(raw, ALL_INGREDIENTS)
    return true
  }

  // Selection changes use `replace` so ticking a dozen herbs does not bury the
  // page the user arrived from under a dozen history entries. View changes use
  // `push`, so Back still steps out of a recipe.
  function writeHeldToRoute() {
    const serialized = serializeHeldIds(heldIds.value)
    writeStoredHeld(serialized)
    router.replace({ query: { tab: 'brew', ...(serialized ? { have: serialized } : {}) } })
  }

  function openRecipe(id) {
    router.push({ query: { recipe: id } })
  }

  function showList() {
    router.push({ query: {} })
  }

  function showMatcher() {
    const serialized = serializeHeldIds(heldIds.value)
    router.push({ query: { tab: 'brew', ...(serialized ? { have: serialized } : {}) } })
  }

  function toggleIngredient(id) {
    const next = new Set(heldIds.value)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    heldIds.value = [...next]
    writeHeldToRoute()
  }

  function clearSelection() {
    heldIds.value = []
    ingredientQuery.value = ''
    writeHeldToRoute()
  }

  onMounted(() => {
    // The URL wins when it carries a selection; otherwise fall back to whatever
    // the last visit left in storage.
    if (!syncHeldFromRoute()) {
      heldIds.value = parseHeldIds(readStoredHeld(), ALL_INGREDIENTS)
    }
    ready.value = true
  })

  watch(() => route.query.have, () => {
    if (ready.value) syncHeldFromRoute()
  })

  return {
    ready,
    view,
    recipes: ALL_RECIPES,
    ingredients: ALL_INGREDIENTS,
    recipeQuery,
    baseFilter,
    allBasesSelected,
    toggleBase,
    selectAllBases,
    ingredientQuery,
    visibleRecipes,
    visibleIngredients,
    selectedRecipe,
    heldSet,
    selectedCount,
    matches,
    openRecipe,
    showList,
    showMatcher,
    toggleIngredient,
    clearSelection,
  }
}
