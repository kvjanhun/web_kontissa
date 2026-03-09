import { mergeProps, unref, useSSRContext } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/index.mjs';
import { ssrRenderAttrs } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/server-renderer/index.mjs';
import { storeToRefs } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/pinia/dist/pinia.prod.cjs';
import { c as useDarkModeStore, u as useI18nStore } from './server.mjs';

const _sfc_main = {
  __name: "ThemeToggle",
  __ssrInlineRender: true,
  setup(__props) {
    const darkModeStore = useDarkModeStore();
    const { isDark } = storeToRefs(darkModeStore);
    const { toggleDark } = darkModeStore;
    const { t } = useI18nStore();
    return (_ctx, _push, _parent, _attrs) => {
      _push(`<button${ssrRenderAttrs(mergeProps({
        class: "p-2 rounded-lg transition-colors duration-200 hover:bg-white/10",
        "aria-label": unref(isDark) ? unref(t)("theme.switchToLight") : unref(t)("theme.switchToDark")
      }, _attrs))}>`);
      if (unref(isDark)) {
        _push(`<svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`);
      } else {
        _push(`<svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`);
      }
      _push(`</button>`);
    };
  }
};
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("components/ThemeToggle.vue");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};

export { _sfc_main as _ };
//# sourceMappingURL=ThemeToggle-xR7Kb5x1.mjs.map
