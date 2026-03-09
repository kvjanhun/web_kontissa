import { _ as __nuxt_component_0 } from './nuxt-link-CgzrXG5R.mjs';
import { mergeProps, unref, withCtx, createTextVNode, toDisplayString, useSSRContext } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/index.mjs';
import { ssrRenderAttrs, ssrRenderStyle, ssrInterpolate, ssrRenderComponent } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/server-renderer/index.mjs';
import { u as useI18nStore } from './server.mjs';
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
  __name: "[...slug]",
  __ssrInlineRender: true,
  setup(__props) {
    const { t } = useI18nStore();
    return (_ctx, _push, _parent, _attrs) => {
      const _component_NuxtLink = __nuxt_component_0;
      _push(`<div${ssrRenderAttrs(mergeProps({ class: "flex flex-col items-center justify-center py-20 text-center" }, _attrs))}><h1 class="text-7xl font-bold text-accent mb-4">404</h1><p class="text-xl mb-8" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(unref(t)("notFound.heading"))}</p>`);
      _push(ssrRenderComponent(_component_NuxtLink, {
        to: "/",
        class: "px-6 py-2.5 bg-accent text-white rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90"
      }, {
        default: withCtx((_, _push2, _parent2, _scopeId) => {
          if (_push2) {
            _push2(`${ssrInterpolate(unref(t)("notFound.backHome"))}`);
          } else {
            return [
              createTextVNode(toDisplayString(unref(t)("notFound.backHome")), 1)
            ];
          }
        }),
        _: 1
      }, _parent));
      _push(`</div>`);
    };
  }
};
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("pages/[...slug].vue");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};

export { _sfc_main as default };
//# sourceMappingURL=_...slug_-74uzxZeM.mjs.map
