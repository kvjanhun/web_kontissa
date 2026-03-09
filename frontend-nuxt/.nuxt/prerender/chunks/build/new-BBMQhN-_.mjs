import { _ as __nuxt_component_0 } from './nuxt-link-CgzrXG5R.mjs';
import { computed, ref, mergeProps, unref, withCtx, createTextVNode, toDisplayString, useSSRContext } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/index.mjs';
import { ssrRenderAttrs, ssrRenderStyle, ssrInterpolate, ssrRenderAttr, ssrIncludeBooleanAttr, ssrLooseContain, ssrLooseEqual, ssrRenderList, ssrRenderComponent } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/server-renderer/index.mjs';
import { d as useRoute, a as useRouter, u as useI18nStore } from './server.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ufo/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ofetch/dist/node.mjs';
import '../_/renderer.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue-bundle-renderer/dist/runtime.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/h3/dist/index.mjs';
import '../nitro/nitro.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/destr/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/hookable/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/node-mock-http/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unstorage/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unstorage/drivers/fs.mjs';
import 'node:crypto';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unstorage/drivers/fs-lite.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unstorage/drivers/lru-cache.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ohash/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/klona/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/defu/dist/defu.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/scule/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unctx/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/radix3/dist/index.mjs';
import 'node:fs';
import 'node:url';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/pathe/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unhead/dist/server.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/devalue/index.js';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unhead/dist/utils.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unhead/dist/plugins.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/pinia/dist/pinia.prod.cjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue-router/vue-router.node.mjs';

const _sfc_main = {
  __name: "new",
  __ssrInlineRender: true,
  setup(__props) {
    const route = useRoute();
    useRouter();
    const { t } = useI18nStore();
    const isEdit = computed(() => !!route.params.slug);
    ref(null);
    const title = ref("");
    const category = ref("");
    const categories = ref([]);
    const ingredients = ref([{ amount: "", unit: "", name: "" }]);
    const steps = ref([{ content: "" }]);
    const error = ref("");
    const saving = ref(false);
    const loading = ref(false);
    return (_ctx, _push, _parent, _attrs) => {
      const _component_NuxtLink = __nuxt_component_0;
      _push(`<div${ssrRenderAttrs(mergeProps({ class: "max-w-3xl mx-auto py-8 px-4" }, _attrs))}><h1 class="text-3xl font-light mb-6" style="${ssrRenderStyle({ color: "var(--color-text-primary)" })}">${ssrInterpolate(unref(isEdit) ? unref(t)("recipeForm.editHeading") : unref(t)("recipeForm.newHeading"))}</h1>`);
      if (unref(loading)) {
        _push(`<p class="text-center py-12" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}" role="status">${ssrInterpolate(unref(t)("recipes.loading"))}</p>`);
      } else {
        _push(`<form class="space-y-6">`);
        if (unref(error)) {
          _push(`<p class="text-red-500 text-sm" role="alert">${ssrInterpolate(unref(error))}</p>`);
        } else {
          _push(`<!---->`);
        }
        _push(`<div><label class="block text-sm mb-1" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(unref(t)("recipeForm.title"))}</label><input${ssrRenderAttr("value", unref(title))} type="text" required class="w-full px-4 py-2 rounded-lg text-sm outline-none" style="${ssrRenderStyle({
          backgroundColor: "var(--color-input-bg)",
          border: "1px solid var(--color-border)",
          color: "var(--color-text-primary)"
        })}"></div><div><label class="block text-sm mb-1" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(unref(t)("recipeForm.category"))}</label><select class="w-full px-4 py-2 rounded-lg text-sm outline-none" style="${ssrRenderStyle({
          backgroundColor: "var(--color-input-bg)",
          border: "1px solid var(--color-border)",
          color: "var(--color-text-primary)"
        })}"><option value=""${ssrIncludeBooleanAttr(Array.isArray(unref(category)) ? ssrLooseContain(unref(category), "") : ssrLooseEqual(unref(category), "")) ? " selected" : ""}>${ssrInterpolate(unref(t)("recipeForm.none"))}</option><!--[-->`);
        ssrRenderList(unref(categories), (cat) => {
          _push(`<option${ssrRenderAttr("value", cat)}${ssrIncludeBooleanAttr(Array.isArray(unref(category)) ? ssrLooseContain(unref(category), cat) : ssrLooseEqual(unref(category), cat)) ? " selected" : ""}>${ssrInterpolate(cat)}</option>`);
        });
        _push(`<!--]--></select></div><div><label class="block text-sm mb-2" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(unref(t)("recipeForm.ingredients"))}</label><!--[-->`);
        ssrRenderList(unref(ingredients), (ing, i) => {
          _push(`<div class="flex gap-2 mb-2"><input${ssrRenderAttr("value", ing.amount)} type="text"${ssrRenderAttr("placeholder", unref(t)("recipeForm.amount"))} class="w-20 px-3 py-2 rounded-lg text-sm outline-none" style="${ssrRenderStyle({
            backgroundColor: "var(--color-input-bg)",
            border: "1px solid var(--color-border)",
            color: "var(--color-text-primary)"
          })}"><input${ssrRenderAttr("value", ing.unit)} type="text"${ssrRenderAttr("placeholder", unref(t)("recipeForm.unit"))} class="w-20 px-3 py-2 rounded-lg text-sm outline-none" style="${ssrRenderStyle({
            backgroundColor: "var(--color-input-bg)",
            border: "1px solid var(--color-border)",
            color: "var(--color-text-primary)"
          })}"><input${ssrRenderAttr("value", ing.name)} type="text"${ssrRenderAttr("placeholder", unref(t)("recipeForm.ingredientName"))} class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" style="${ssrRenderStyle({
            backgroundColor: "var(--color-input-bg)",
            border: "1px solid var(--color-border)",
            color: "var(--color-text-primary)"
          })}"><button type="button" class="px-2 text-red-500 hover:bg-red-500/10 rounded"${ssrIncludeBooleanAttr(unref(ingredients).length === 1) ? " disabled" : ""}> \xD7 </button></div>`);
        });
        _push(`<!--]--><button type="button" class="text-sm transition-colors duration-200 hover:opacity-80" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(unref(t)("recipeForm.addIngredient"))}</button></div><div><label class="block text-sm mb-2" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(unref(t)("recipeForm.steps"))}</label><!--[-->`);
        ssrRenderList(unref(steps), (step, i) => {
          _push(`<div class="flex gap-2 mb-2"><span class="py-2 text-sm w-6 text-right" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(i + 1)}.</span><textarea${ssrRenderAttr("placeholder", unref(t)("recipeForm.stepPlaceholder"))} rows="2" class="flex-1 px-3 py-2 rounded-lg text-sm outline-none resize-y" style="${ssrRenderStyle({
            backgroundColor: "var(--color-input-bg)",
            border: "1px solid var(--color-border)",
            color: "var(--color-text-primary)"
          })}">${ssrInterpolate(step.content)}</textarea><button type="button" class="px-2 text-red-500 hover:bg-red-500/10 rounded self-start mt-2"${ssrIncludeBooleanAttr(unref(steps).length === 1) ? " disabled" : ""}> \xD7 </button></div>`);
        });
        _push(`<!--]--><button type="button" class="text-sm transition-colors duration-200 hover:opacity-80" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(unref(t)("recipeForm.addStep"))}</button></div><div class="flex gap-3 pt-2"><button type="submit"${ssrIncludeBooleanAttr(unref(saving)) ? " disabled" : ""} class="px-6 py-2 bg-accent text-white rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90 disabled:opacity-50">${ssrInterpolate(unref(saving) ? unref(t)("recipeForm.saving") : unref(isEdit) ? unref(t)("recipeForm.update") : unref(t)("recipeForm.create"))}</button>`);
        _push(ssrRenderComponent(_component_NuxtLink, {
          to: unref(isEdit) ? `/recipes/${unref(route).params.slug}` : "/recipes",
          class: "px-6 py-2 rounded-lg text-sm font-medium transition-colors duration-200",
          style: {
            border: "1px solid var(--color-border)",
            color: "var(--color-text-primary)"
          }
        }, {
          default: withCtx((_, _push2, _parent2, _scopeId) => {
            if (_push2) {
              _push2(`${ssrInterpolate(unref(t)("recipeForm.cancel"))}`);
            } else {
              return [
                createTextVNode(toDisplayString(unref(t)("recipeForm.cancel")), 1)
              ];
            }
          }),
          _: 1
        }, _parent));
        _push(`</div></form>`);
      }
      _push(`</div>`);
    };
  }
};
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("pages/recipes/new.vue");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};

export { _sfc_main as default };
//# sourceMappingURL=new-BBMQhN-_.mjs.map
