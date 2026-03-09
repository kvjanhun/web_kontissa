import { _ as __nuxt_component_0 } from "./nuxt-link-CgzrXG5R.js";
import { mergeProps, unref, withCtx, createTextVNode, toDisplayString, useSSRContext } from "vue";
import { ssrRenderAttrs, ssrRenderStyle, ssrInterpolate, ssrRenderComponent } from "vue/server-renderer";
import { u as useI18nStore } from "../server.mjs";
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
export {
  _sfc_main as default
};
//# sourceMappingURL=_...slug_-74uzxZeM.js.map
