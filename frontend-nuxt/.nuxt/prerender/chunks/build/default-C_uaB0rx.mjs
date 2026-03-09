import { ref, unref, mergeProps, withCtx, createTextVNode, toDisplayString, computed, useSSRContext } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/index.mjs';
import { ssrRenderComponent, ssrRenderStyle, ssrRenderSlot, ssrInterpolate, ssrRenderAttrs, ssrRenderAttr, ssrRenderList } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/server-renderer/index.mjs';
import { b as useAuthStore, u as useI18nStore, a as useRouter } from './server.mjs';
import { _ as __nuxt_component_0 } from './nuxt-link-CgzrXG5R.mjs';
import { useRouter as useRouter$1 } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue-router/vue-router.node.mjs';
import { storeToRefs } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/pinia/dist/pinia.prod.cjs';
import { _ as _sfc_main$4 } from './ThemeToggle-xR7Kb5x1.mjs';
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

function useNavLinks(handleLogout) {
  const { isAuthenticated, isAdmin } = storeToRefs(useAuthStore());
  const navLinks = computed(() => {
    const links = [
      { to: "/about", labelKey: "nav.about" },
      { to: "/contact", labelKey: "nav.contact" },
      { to: "/sanakenno", labelKey: "nav.sanakenno" }
    ];
    if (isAuthenticated.value) {
      links.push({ to: "/recipes", labelKey: "nav.recipes" });
    }
    if (isAdmin.value) {
      links.push({ to: "/admin", labelKey: "nav.admin" });
    }
    if (isAuthenticated.value) {
      links.push({ to: "/login", labelKey: "nav.logout", action: handleLogout });
    } else {
      links.push({ to: "/login", labelKey: "nav.login" });
    }
    return links;
  });
  return { navLinks };
}
const _sfc_main$3 = {
  __name: "LangToggle",
  __ssrInlineRender: true,
  setup(__props) {
    const i18nStore = useI18nStore();
    const { locale } = storeToRefs(i18nStore);
    const { setLocale } = i18nStore;
    return (_ctx, _push, _parent, _attrs) => {
      _push(`<button${ssrRenderAttrs(mergeProps({
        class: "px-2 py-1 rounded text-xs font-medium transition-colors duration-200 hover:bg-white/10",
        style: { color: "var(--color-text-secondary)", border: "1px solid rgba(255,255,255,0.15)" },
        "aria-label": unref(locale) === "fi" ? "Switch to English" : "Vaihda suomeksi"
      }, _attrs))}>${ssrInterpolate(unref(locale) === "fi" ? "EN" : "FI")}</button>`);
    };
  }
};
const _sfc_setup$3 = _sfc_main$3.setup;
_sfc_main$3.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("components/LangToggle.vue");
  return _sfc_setup$3 ? _sfc_setup$3(props, ctx) : void 0;
};
const _sfc_main$2 = {
  __name: "AppHeader",
  __ssrInlineRender: true,
  setup(__props) {
    const { logout } = useAuthStore();
    const { t } = useI18nStore();
    const router = useRouter$1();
    const menuOpen = ref(false);
    async function handleLogout() {
      await logout();
      router.push("/login");
    }
    const { navLinks } = useNavLinks(handleLogout);
    function closeMenu() {
      menuOpen.value = false;
    }
    return (_ctx, _push, _parent, _attrs) => {
      const _component_NuxtLink = __nuxt_component_0;
      _push(`<header${ssrRenderAttrs(mergeProps({
        class: "sticky top-0 z-50",
        style: {
          backgroundColor: "var(--color-header-bg)",
          borderBottom: "2px solid var(--color-header-border)",
          paddingTop: "env(safe-area-inset-top)"
        }
      }, _attrs))}><div class="px-6 h-16 flex justify-between items-center"><div class="flex gap-6 items-center">`);
      _push(ssrRenderComponent(_component_NuxtLink, {
        to: "/",
        class: "!text-white text-2xl font-normal tracking-tight"
      }, {
        default: withCtx((_, _push2, _parent2, _scopeId) => {
          if (_push2) {
            _push2(`erez.ac`);
          } else {
            return [
              createTextVNode("erez.ac")
            ];
          }
        }),
        _: 1
      }, _parent));
      _push(`</div><div class="flex items-center gap-2">`);
      _push(ssrRenderComponent(_sfc_main$3, null, null, _parent));
      _push(ssrRenderComponent(_sfc_main$4, { class: "text-stone-400" }, null, _parent));
      _push(`<button class="p-2 text-stone-400 hover:text-white"${ssrRenderAttr("aria-label", unref(t)("nav.toggleMenu"))}${ssrRenderAttr("aria-expanded", menuOpen.value)}><svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" class="size-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">`);
      if (!menuOpen.value) {
        _push(`<path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16"></path>`);
      } else {
        _push(`<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"></path>`);
      }
      _push(`</svg></button></div></div>`);
      if (menuOpen.value) {
        _push(`<nav class="absolute top-full right-0 flex flex-col py-2 shadow-lg rounded-bl-lg min-w-44" style="${ssrRenderStyle({
          backgroundColor: "var(--color-header-bg)",
          borderBottom: "2px solid var(--color-header-border)",
          borderLeft: "2px solid var(--color-header-border)"
        })}" aria-label="Main"><!--[-->`);
        ssrRenderList(unref(navLinks), (link) => {
          _push(ssrRenderComponent(_component_NuxtLink, {
            key: link.to,
            to: link.action ? "" : link.to,
            class: "!text-stone-400 px-6 py-3 text-sm transition-colors duration-200 hover:!text-accent hover:bg-white/10",
            onClick: ($event) => {
              closeMenu();
              link.action ? link.action() : unref(router).push(link.to);
            }
          }, {
            default: withCtx((_, _push2, _parent2, _scopeId) => {
              if (_push2) {
                _push2(`${ssrInterpolate(unref(t)(link.labelKey))}`);
              } else {
                return [
                  createTextVNode(toDisplayString(unref(t)(link.labelKey)), 1)
                ];
              }
            }),
            _: 2
          }, _parent));
        });
        _push(`<!--]--></nav>`);
      } else {
        _push(`<!---->`);
      }
      _push(`</header>`);
    };
  }
};
const _sfc_setup$2 = _sfc_main$2.setup;
_sfc_main$2.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("components/AppHeader.vue");
  return _sfc_setup$2 ? _sfc_setup$2(props, ctx) : void 0;
};
const _sfc_main$1 = {
  __name: "AppFooter",
  __ssrInlineRender: true,
  props: {
    updateDate: { type: String, default: "" }
  },
  setup(__props) {
    const { t } = useI18nStore();
    return (_ctx, _push, _parent, _attrs) => {
      const _component_NuxtLink = __nuxt_component_0;
      _push(`<footer${ssrRenderAttrs(mergeProps({
        class: "px-6 py-5",
        style: {
          backgroundColor: "var(--color-header-bg)",
          borderTop: "2px solid var(--color-header-border)"
        }
      }, _attrs))}><nav class="flex flex-wrap gap-x-5 gap-y-2 text-sm mb-3" aria-label="Footer">`);
      _push(ssrRenderComponent(_component_NuxtLink, {
        to: "/about",
        class: "!text-stone-400 hover:!text-accent transition-colors"
      }, {
        default: withCtx((_, _push2, _parent2, _scopeId) => {
          if (_push2) {
            _push2(`${ssrInterpolate(unref(t)("nav.about"))}`);
          } else {
            return [
              createTextVNode(toDisplayString(unref(t)("nav.about")), 1)
            ];
          }
        }),
        _: 1
      }, _parent));
      _push(ssrRenderComponent(_component_NuxtLink, {
        to: "/contact",
        class: "!text-stone-400 hover:!text-accent transition-colors"
      }, {
        default: withCtx((_, _push2, _parent2, _scopeId) => {
          if (_push2) {
            _push2(`${ssrInterpolate(unref(t)("nav.contact"))}`);
          } else {
            return [
              createTextVNode(toDisplayString(unref(t)("nav.contact")), 1)
            ];
          }
        }),
        _: 1
      }, _parent));
      _push(ssrRenderComponent(_component_NuxtLink, {
        to: "/sanakenno",
        class: "!text-stone-400 hover:!text-accent transition-colors"
      }, {
        default: withCtx((_, _push2, _parent2, _scopeId) => {
          if (_push2) {
            _push2(`${ssrInterpolate(unref(t)("nav.sanakenno"))}`);
          } else {
            return [
              createTextVNode(toDisplayString(unref(t)("nav.sanakenno")), 1)
            ];
          }
        }),
        _: 1
      }, _parent));
      _push(`</nav><div class="text-sm" style="${ssrRenderStyle({ "color": "var(--color-text-tertiary)" })}">`);
      if (__props.updateDate) {
        _push(`<span>${ssrInterpolate(unref(t)("footer.lastUpdated", { date: __props.updateDate }))}</span>`);
      } else {
        _push(`<!---->`);
      }
      _push(`</div></footer>`);
    };
  }
};
const _sfc_setup$1 = _sfc_main$1.setup;
_sfc_main$1.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("components/AppFooter.vue");
  return _sfc_setup$1 ? _sfc_setup$1(props, ctx) : void 0;
};
const _sfc_main = {
  __name: "default",
  __ssrInlineRender: true,
  setup(__props) {
    useAuthStore();
    const { t } = useI18nStore();
    const updateDate = ref("");
    const routeAnnouncement = ref("");
    const router = useRouter();
    router.afterEach((to) => {
      const titleKey = to.meta.titleKey;
      routeAnnouncement.value = titleKey ? t(titleKey) : "erez.ac";
    });
    return (_ctx, _push, _parent, _attrs) => {
      _push(`<!--[--><a href="#main-content" class="skip-link">Skip to content</a><div class="flex flex-col min-h-screen">`);
      _push(ssrRenderComponent(_sfc_main$2, null, null, _parent));
      _push(`<main id="main-content" class="grow p-6" style="${ssrRenderStyle({
        backgroundColor: "var(--color-bg-primary)",
        color: "var(--color-text-primary)"
      })}">`);
      ssrRenderSlot(_ctx.$slots, "default", {}, null, _push, _parent);
      _push(`</main>`);
      _push(ssrRenderComponent(_sfc_main$1, { "update-date": unref(updateDate) }, null, _parent));
      _push(`</div><div aria-live="polite" aria-atomic="true" class="sr-only">${ssrInterpolate(unref(routeAnnouncement))}</div><!--]-->`);
    };
  }
};
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("layouts/default.vue");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};

export { _sfc_main as default };
//# sourceMappingURL=default-C_uaB0rx.mjs.map
