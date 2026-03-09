import { _ as __nuxt_component_0 } from './nuxt-link-CgzrXG5R.mjs';
import { ref, mergeProps, unref, withCtx, createTextVNode, toDisplayString, useSSRContext } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/index.mjs';
import { ssrRenderAttrs, ssrRenderStyle, ssrInterpolate, ssrRenderComponent, ssrRenderList, ssrIncludeBooleanAttr, ssrRenderAttr } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/server-renderer/index.mjs';
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
  __name: "[slug]",
  __ssrInlineRender: true,
  setup(__props) {
    useRoute();
    useRouter();
    const { t } = useI18nStore();
    const recipe = ref(null);
    const loading = ref(true);
    const error = ref("");
    const completedSteps = ref(/* @__PURE__ */ new Set());
    return (_ctx, _push, _parent, _attrs) => {
      const _component_NuxtLink = __nuxt_component_0;
      _push(`<div${ssrRenderAttrs(mergeProps({ class: "max-w-3xl mx-auto py-8 px-4" }, _attrs))}>`);
      if (unref(loading)) {
        _push(`<p class="text-center py-12" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}" role="status">${ssrInterpolate(unref(t)("recipes.loading"))}</p>`);
      } else if (unref(error)) {
        _push(`<p class="text-center py-12 text-red-500" role="alert">${ssrInterpolate(unref(error))}</p>`);
      } else if (unref(recipe)) {
        _push(`<!--[--><div class="flex justify-between items-start mb-6"><div><h1 class="text-3xl font-light mb-1" style="${ssrRenderStyle({ color: "var(--color-text-primary)" })}">${ssrInterpolate(unref(recipe).title)}</h1>`);
        if (unref(recipe).category) {
          _push(`<span class="inline-block text-xs px-2 py-0.5 rounded-full" style="${ssrRenderStyle({
            backgroundColor: "var(--color-tag-bg)",
            color: "var(--color-text-secondary)"
          })}">${ssrInterpolate(unref(recipe).category)}</span>`);
        } else {
          _push(`<!---->`);
        }
        _push(`</div><div class="flex gap-2">`);
        _push(ssrRenderComponent(_component_NuxtLink, {
          to: `/recipes/${unref(recipe).slug}/edit`,
          class: "px-3 py-1.5 rounded-lg text-sm transition-colors duration-200",
          style: {
            border: "1px solid var(--color-border)",
            color: "var(--color-text-primary)"
          }
        }, {
          default: withCtx((_, _push2, _parent2, _scopeId) => {
            if (_push2) {
              _push2(`${ssrInterpolate(unref(t)("recipe.edit"))}`);
            } else {
              return [
                createTextVNode(toDisplayString(unref(t)("recipe.edit")), 1)
              ];
            }
          }),
          _: 1
        }, _parent));
        _push(`<button class="px-3 py-1.5 rounded-lg text-sm text-red-500 transition-colors duration-200 hover:bg-red-500/10" style="${ssrRenderStyle({ border: "1px solid var(--color-border)" })}">${ssrInterpolate(unref(t)("recipe.delete"))}</button></div></div><section class="mb-8"><h2 class="text-xl font-medium mb-3 pb-2" style="${ssrRenderStyle({ color: "var(--color-text-primary)", borderBottom: "1px solid var(--color-border)" })}">${ssrInterpolate(unref(t)("recipe.ingredients"))}</h2><ul class="space-y-1"><!--[-->`);
        ssrRenderList(unref(recipe).ingredients, (ing) => {
          _push(`<li style="${ssrRenderStyle({ color: "var(--color-text-primary)" })}">`);
          if (ing.amount) {
            _push(`<span class="font-medium">${ssrInterpolate(ing.amount)}</span>`);
          } else {
            _push(`<!---->`);
          }
          if (ing.unit) {
            _push(`<span>${ssrInterpolate(ing.unit)}</span>`);
          } else {
            _push(`<!---->`);
          }
          _push(` ${ssrInterpolate(ing.name)}</li>`);
        });
        _push(`<!--]--></ul></section><section><h2 class="text-xl font-medium mb-3 pb-2" style="${ssrRenderStyle({ color: "var(--color-text-primary)", borderBottom: "1px solid var(--color-border)" })}">${ssrInterpolate(unref(t)("recipe.steps"))}</h2><ol class="space-y-3"><!--[-->`);
        ssrRenderList(unref(recipe).steps, (step, i) => {
          _push(`<li class="flex items-start gap-3 cursor-pointer select-none transition-opacity duration-200" style="${ssrRenderStyle({ color: "var(--color-text-primary)", opacity: unref(completedSteps).has(step.id) ? 0.4 : 1 })}"><input type="checkbox"${ssrIncludeBooleanAttr(unref(completedSteps).has(step.id)) ? " checked" : ""}${ssrRenderAttr("aria-label", `${unref(t)("recipe.steps")} ${i + 1}: ${step.content}`)} class="mt-1 shrink-0 accent-[var(--color-accent,#ff643e)]"><span><span class="font-medium" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(i + 1)}.</span> ${ssrInterpolate(step.content)}</span></li>`);
        });
        _push(`<!--]--></ol></section><div class="mt-8">`);
        _push(ssrRenderComponent(_component_NuxtLink, {
          to: "/recipes",
          class: "text-sm transition-colors duration-200",
          style: { color: "var(--color-text-secondary)" }
        }, {
          default: withCtx((_, _push2, _parent2, _scopeId) => {
            if (_push2) {
              _push2(`${ssrInterpolate(unref(t)("recipe.backToRecipes"))}`);
            } else {
              return [
                createTextVNode(toDisplayString(unref(t)("recipe.backToRecipes")), 1)
              ];
            }
          }),
          _: 1
        }, _parent));
        _push(`</div><!--]-->`);
      } else {
        _push(`<!---->`);
      }
      _push(`</div>`);
    };
  }
};
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("pages/recipes/[slug].vue");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};

export { _sfc_main as default };
//# sourceMappingURL=_slug_-dQIpVxCD.mjs.map
