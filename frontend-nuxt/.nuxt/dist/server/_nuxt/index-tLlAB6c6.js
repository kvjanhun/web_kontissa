import { _ as __nuxt_component_0 } from "./nuxt-link-CgzrXG5R.js";
import { ref, watch, mergeProps, unref, withCtx, createTextVNode, toDisplayString, createVNode, openBlock, createBlock, createCommentVNode, useSSRContext } from "vue";
import { ssrRenderAttrs, ssrRenderStyle, ssrInterpolate, ssrRenderComponent, ssrRenderAttr, ssrIncludeBooleanAttr, ssrLooseContain, ssrLooseEqual, ssrRenderList } from "vue/server-renderer";
import { a as useRouter, u as useI18nStore } from "../server.mjs";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/hookable/dist/index.mjs";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ufo/dist/index.mjs";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ofetch/dist/node.mjs";
import "#internal/nuxt/paths";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unctx/dist/index.mjs";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/h3/dist/index.mjs";
import "pinia";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/defu/dist/defu.mjs";
import "vue-router";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/klona/dist/index.mjs";
const _sfc_main = {
  __name: "index",
  __ssrInlineRender: true,
  setup(__props) {
    useRouter();
    const { t } = useI18nStore();
    const recipes = ref([]);
    const categories = ref([]);
    const search = ref("");
    const selectedCategory = ref("");
    const loading = ref(true);
    const error = ref("");
    let debounceTimer = null;
    async function fetchRecipes() {
      loading.value = true;
      error.value = "";
      try {
        const params = new URLSearchParams();
        if (search.value) params.set("q", search.value);
        if (selectedCategory.value) params.set("category", selectedCategory.value);
        const res = await fetch(`/api/recipes?${params}`);
        if (!res.ok) throw new Error(t("recipes.loadError"));
        recipes.value = await res.json();
      } catch (e) {
        error.value = e.message;
      } finally {
        loading.value = false;
      }
    }
    function debouncedFetch() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(fetchRecipes, 300);
    }
    watch(search, debouncedFetch);
    watch(selectedCategory, fetchRecipes);
    return (_ctx, _push, _parent, _attrs) => {
      const _component_NuxtLink = __nuxt_component_0;
      _push(`<div${ssrRenderAttrs(mergeProps({ class: "max-w-4xl mx-auto py-8 px-4" }, _attrs))}><div class="flex justify-between items-center mb-6"><h1 class="text-3xl font-light" style="${ssrRenderStyle({ color: "var(--color-text-primary)" })}">${ssrInterpolate(unref(t)("recipes.heading"))}</h1>`);
      _push(ssrRenderComponent(_component_NuxtLink, {
        to: "/recipes/new",
        class: "px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90"
      }, {
        default: withCtx((_, _push2, _parent2, _scopeId) => {
          if (_push2) {
            _push2(`${ssrInterpolate(unref(t)("recipes.newRecipe"))}`);
          } else {
            return [
              createTextVNode(toDisplayString(unref(t)("recipes.newRecipe")), 1)
            ];
          }
        }),
        _: 1
      }, _parent));
      _push(`</div><div class="flex flex-col sm:flex-row gap-3 mb-6"><input${ssrRenderAttr("value", unref(search))} type="text"${ssrRenderAttr("placeholder", unref(t)("recipes.searchPlaceholder"))} class="flex-1 px-4 py-2 rounded-lg text-sm outline-none" style="${ssrRenderStyle({
        backgroundColor: "var(--color-input-bg)",
        border: "1px solid var(--color-border)",
        color: "var(--color-text-primary)"
      })}"><select class="px-4 py-2 rounded-lg text-sm outline-none" style="${ssrRenderStyle({
        backgroundColor: "var(--color-input-bg)",
        border: "1px solid var(--color-border)",
        color: "var(--color-text-primary)"
      })}"><option value=""${ssrIncludeBooleanAttr(Array.isArray(unref(selectedCategory)) ? ssrLooseContain(unref(selectedCategory), "") : ssrLooseEqual(unref(selectedCategory), "")) ? " selected" : ""}>${ssrInterpolate(unref(t)("recipes.allCategories"))}</option><!--[-->`);
      ssrRenderList(unref(categories), (cat) => {
        _push(`<option${ssrRenderAttr("value", cat)}${ssrIncludeBooleanAttr(Array.isArray(unref(selectedCategory)) ? ssrLooseContain(unref(selectedCategory), cat) : ssrLooseEqual(unref(selectedCategory), cat)) ? " selected" : ""}>${ssrInterpolate(cat)}</option>`);
      });
      _push(`<!--]--></select></div>`);
      if (unref(error)) {
        _push(`<p class="text-red-500 mb-4" role="alert">${ssrInterpolate(unref(error))}</p>`);
      } else {
        _push(`<!---->`);
      }
      if (unref(loading)) {
        _push(`<p class="text-center py-12" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}" role="status">${ssrInterpolate(unref(t)("recipes.loading"))}</p>`);
      } else if (unref(recipes).length === 0) {
        _push(`<p class="text-center py-12" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(unref(t)("recipes.noResults"))}</p>`);
      } else {
        _push(`<div class="grid gap-4 sm:grid-cols-2"><!--[-->`);
        ssrRenderList(unref(recipes), (recipe) => {
          _push(ssrRenderComponent(_component_NuxtLink, {
            key: recipe.id,
            to: `/recipes/${recipe.slug}`,
            class: "block p-5 rounded-lg transition-colors duration-200",
            style: {
              backgroundColor: "var(--color-card-bg)",
              border: "1px solid var(--color-border)"
            }
          }, {
            default: withCtx((_, _push2, _parent2, _scopeId) => {
              if (_push2) {
                _push2(`<h2 class="text-lg font-medium mb-1" style="${ssrRenderStyle({ color: "var(--color-text-primary)" })}"${_scopeId}>${ssrInterpolate(recipe.title)}</h2>`);
                if (recipe.category) {
                  _push2(`<span class="inline-block text-xs px-2 py-0.5 rounded-full" style="${ssrRenderStyle({
                    backgroundColor: "var(--color-tag-bg)",
                    color: "var(--color-text-secondary)"
                  })}"${_scopeId}>${ssrInterpolate(recipe.category)}</span>`);
                } else {
                  _push2(`<!---->`);
                }
              } else {
                return [
                  createVNode("h2", {
                    class: "text-lg font-medium mb-1",
                    style: { color: "var(--color-text-primary)" }
                  }, toDisplayString(recipe.title), 1),
                  recipe.category ? (openBlock(), createBlock("span", {
                    key: 0,
                    class: "inline-block text-xs px-2 py-0.5 rounded-full",
                    style: {
                      backgroundColor: "var(--color-tag-bg)",
                      color: "var(--color-text-secondary)"
                    }
                  }, toDisplayString(recipe.category), 1)) : createCommentVNode("", true)
                ];
              }
            }),
            _: 2
          }, _parent));
        });
        _push(`<!--]--></div>`);
      }
      _push(`</div>`);
    };
  }
};
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("pages/recipes/index.vue");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
export {
  _sfc_main as default
};
//# sourceMappingURL=index-tLlAB6c6.js.map
