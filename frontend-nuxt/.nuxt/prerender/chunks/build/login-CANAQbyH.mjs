import { ref, mergeProps, unref, useSSRContext } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/index.mjs';
import { ssrRenderAttrs, ssrRenderStyle, ssrInterpolate, ssrRenderAttr, ssrIncludeBooleanAttr } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/server-renderer/index.mjs';
import { a as useRouter, b as useAuthStore, u as useI18nStore } from './server.mjs';
import { u as useHead } from './v3-DCBci_gg.mjs';
import { storeToRefs } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/pinia/dist/pinia.prod.cjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ofetch/dist/node.mjs';
import '../_/renderer.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue-bundle-renderer/dist/runtime.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/h3/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ufo/dist/index.mjs';
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
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue-router/vue-router.node.mjs';

const _sfc_main = {
  __name: "login",
  __ssrInlineRender: true,
  setup(__props) {
    useHead({
      meta: [
        { name: "robots", content: "noindex" }
      ]
    });
    useRouter();
    const authStore = useAuthStore();
    const { user, isAuthenticated } = storeToRefs(authStore);
    const { login, logout } = authStore;
    const { t } = useI18nStore();
    const email = ref("");
    const password = ref("");
    const error = ref("");
    const loading = ref(false);
    return (_ctx, _push, _parent, _attrs) => {
      _push(`<div${ssrRenderAttrs(mergeProps({ class: "max-w-sm mx-auto mt-12" }, _attrs))}>`);
      if (unref(isAuthenticated)) {
        _push(`<div class="text-center space-y-4"><h1 class="text-3xl font-light mb-4" style="${ssrRenderStyle({ color: "var(--color-text-primary)" })}">${ssrInterpolate(unref(t)("login.loggedIn"))}</h1><p style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(unref(t)("login.signedInAs"))} <strong>${ssrInterpolate(unref(user).username)}</strong> (${ssrInterpolate(unref(user).email)}) </p><button class="bg-accent text-white px-6 py-2 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90">${ssrInterpolate(unref(t)("nav.logout"))}</button></div>`);
      } else {
        _push(`<div><h1 class="text-3xl font-light mb-8 text-center" style="${ssrRenderStyle({ color: "var(--color-text-primary)" })}">${ssrInterpolate(unref(t)("login.heading"))}</h1>`);
        if (unref(error)) {
          _push(`<div id="login-error" role="alert" class="mb-4 p-3 rounded-lg text-sm bg-red-500/10 text-red-400 border border-red-500/20">${ssrInterpolate(unref(error))}</div>`);
        } else {
          _push(`<!---->`);
        }
        _push(`<form class="space-y-4"><div><label for="email" class="block text-sm mb-1" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(unref(t)("login.email"))}</label><input id="email"${ssrRenderAttr("value", unref(email))} type="email" autocomplete="email" required${ssrRenderAttr("aria-invalid", !!unref(error))}${ssrRenderAttr("aria-describedby", unref(error) ? "login-error" : void 0)} class="w-full px-3 py-2 rounded-lg text-sm outline-none transition-colors duration-200 focus:ring-2 focus:ring-accent" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-secondary)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" })}"></div><div><label for="password" class="block text-sm mb-1" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(unref(t)("login.password"))}</label><input id="password"${ssrRenderAttr("value", unref(password))} type="password" autocomplete="current-password" required class="w-full px-3 py-2 rounded-lg text-sm outline-none transition-colors duration-200 focus:ring-2 focus:ring-accent" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-secondary)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" })}"></div><button type="submit"${ssrIncludeBooleanAttr(unref(loading)) ? " disabled" : ""} class="w-full bg-accent text-white py-2 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90 disabled:opacity-50">${ssrInterpolate(unref(loading) ? unref(t)("login.signingIn") : unref(t)("login.signIn"))}</button></form></div>`);
      }
      _push(`</div>`);
    };
  }
};
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("pages/login.vue");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};

export { _sfc_main as default };
//# sourceMappingURL=login-CANAQbyH.mjs.map
