import { computed, mergeProps, useSSRContext, ref, unref } from "vue";
import { ssrRenderAttrs, ssrRenderStyle, ssrInterpolate, ssrRenderList, ssrRenderComponent } from "vue/server-renderer";
import { _ as _export_sfc } from "./_plugin-vue_export-helper-1tPrXgE0.js";
import { u as useI18nStore } from "../server.mjs";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/hookable/dist/index.mjs";
import { u as useHead } from "./v3-DCBci_gg.js";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ofetch/dist/node.mjs";
import "#internal/nuxt/paths";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unctx/dist/index.mjs";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/h3/dist/index.mjs";
import "pinia";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/defu/dist/defu.mjs";
import "vue-router";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ufo/dist/index.mjs";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/klona/dist/index.mjs";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/@unhead/vue/dist/index.mjs";
const _sfc_main$1 = {
  __name: "SectionBlock",
  __ssrInlineRender: true,
  props: {
    section: { type: Object, required: true },
    compact: { type: Boolean, default: false }
  },
  setup(__props) {
    const props = __props;
    const pills = computed(() => {
      if (props.section.section_type !== "pills") return [];
      return props.section.content.split(",").map((s) => s.trim()).filter(Boolean);
    });
    const currentlyItems = computed(() => {
      if (props.section.section_type !== "currently") return [];
      return props.section.content.split("\n").map((line) => {
        const idx = line.indexOf(":");
        if (idx === -1) return { label: line.trim(), value: "" };
        return { label: line.slice(0, idx).trim(), value: line.slice(idx + 1).trim() };
      }).filter((item) => item.label);
    });
    return (_ctx, _push, _parent, _attrs) => {
      if (__props.section.section_type === "quote") {
        _push(`<div${ssrRenderAttrs(mergeProps({
          id: __props.section.slug,
          class: "mb-6 py-6 text-center"
        }, _attrs))} data-v-077997d1><div class="quote-mark" style="${ssrRenderStyle({ color: "var(--color-accent, #ff643e)" })}" data-v-077997d1>“</div><blockquote class="text-3xl font-light italic px-6" style="${ssrRenderStyle({ color: "var(--color-text-primary)" })}" data-v-077997d1>${ssrInterpolate(__props.section.content)}</blockquote><div class="mt-3 mx-auto" style="${ssrRenderStyle({ width: "3rem", height: "2px", background: "var(--color-accent, #ff643e)", opacity: 0.5 })}" data-v-077997d1></div></div>`);
      } else if (__props.section.section_type === "currently") {
        _push(`<article${ssrRenderAttrs(mergeProps({
          class: ["text-base leading-relaxed rounded-lg overflow-hidden h-full", { "mb-6": !__props.compact }],
          id: __props.section.slug,
          style: { background: "var(--color-bg-secondary)", border: "1px solid var(--color-border)" }
        }, _attrs))} data-v-077997d1><div class="px-5 pt-4 pb-4" data-v-077997d1><h2 class="text-xl font-medium m-0 pb-1" data-v-077997d1>${ssrInterpolate(__props.section.title)}</h2><div style="${ssrRenderStyle({ width: "3rem", height: "2px", background: "var(--color-accent, #ff643e)", opacity: 0.6 })}" data-v-077997d1></div></div><div class="px-5 pb-4 space-y-2" data-v-077997d1><!--[-->`);
        ssrRenderList(currentlyItems.value, (item, i) => {
          _push(`<div class="flex items-baseline gap-3 pl-3 py-1.5 rounded" style="${ssrRenderStyle({ borderLeft: "2px solid var(--color-accent, #ff643e)", background: "var(--color-bg-tertiary)" })}" data-v-077997d1><span class="text-xs font-semibold uppercase tracking-wide shrink-0" style="${ssrRenderStyle({ color: "var(--color-accent, #ff643e)" })}" data-v-077997d1>${ssrInterpolate(item.label)}</span>`);
          if (item.value) {
            _push(`<span class="text-sm" style="${ssrRenderStyle({ color: "var(--color-text-primary)" })}" data-v-077997d1>${ssrInterpolate(item.value)}</span>`);
          } else {
            _push(`<!---->`);
          }
          _push(`</div>`);
        });
        _push(`<!--]--></div></article>`);
      } else if (__props.section.section_type === "pills") {
        _push(`<article${ssrRenderAttrs(mergeProps({
          class: ["text-base leading-relaxed rounded-lg", { "mb-6": !__props.compact, "h-full": __props.compact }],
          id: __props.section.slug,
          style: { background: "var(--color-bg-secondary)", border: "1px solid var(--color-border)" }
        }, _attrs))} data-v-077997d1><div class="px-5 pt-4 pb-4" data-v-077997d1><h2 class="text-xl font-medium m-0 pb-1" data-v-077997d1>${ssrInterpolate(__props.section.title)}</h2><div style="${ssrRenderStyle({ width: "3rem", height: "2px", background: "var(--color-accent, #ff643e)", opacity: 0.6 })}" data-v-077997d1></div></div><div class="px-5 pb-4 grid grid-cols-3 gap-2" data-v-077997d1><!--[-->`);
        ssrRenderList(pills.value, (pill) => {
          _push(`<div class="pill flex items-center pl-3 py-1.5 rounded text-sm transition-all duration-200" style="${ssrRenderStyle({ borderLeft: "2px solid var(--color-accent, #ff643e)", background: "var(--color-bg-tertiary)", color: "var(--color-text-primary)" })}" data-v-077997d1>${ssrInterpolate(pill)}</div>`);
        });
        _push(`<!--]--></div></article>`);
      } else {
        _push(`<article${ssrRenderAttrs(mergeProps({
          class: ["text-base leading-relaxed rounded-lg", { "mb-6": !__props.compact, "h-full": __props.compact }],
          id: __props.section.slug,
          style: { background: "var(--color-bg-secondary)", border: "1px solid var(--color-border)" }
        }, _attrs))} data-v-077997d1><div class="px-5 pt-4 pb-4" data-v-077997d1><h2 class="text-xl font-medium m-0 pb-1" data-v-077997d1>${ssrInterpolate(__props.section.title)}</h2><div style="${ssrRenderStyle({ width: "3rem", height: "2px", background: "var(--color-accent, #ff643e)", opacity: 0.6 })}" data-v-077997d1></div></div><div class="section-content px-5 pb-4" data-v-077997d1>${__props.section.content ?? ""}</div></article>`);
      }
    };
  }
};
const _sfc_setup$1 = _sfc_main$1.setup;
_sfc_main$1.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("components/SectionBlock.vue");
  return _sfc_setup$1 ? _sfc_setup$1(props, ctx) : void 0;
};
const __nuxt_component_0 = /* @__PURE__ */ _export_sfc(_sfc_main$1, [["__scopeId", "data-v-077997d1"]]);
const _sfc_main = {
  __name: "about",
  __ssrInlineRender: true,
  setup(__props) {
    const { t } = useI18nStore();
    useHead({
      title: computed(() => t("about.metaTitle")),
      meta: [
        { name: "description", content: computed(() => t("about.metaDescription")) }
      ]
    });
    const sections = ref([]);
    const loading = ref(true);
    const error = ref(null);
    const COMPACT_TYPES = /* @__PURE__ */ new Set(["currently", "pills"]);
    const layoutGroups = computed(() => {
      const groups = [];
      let compactBuffer = [];
      for (const s of sections.value) {
        if (COMPACT_TYPES.has(s.section_type)) {
          compactBuffer.push(s);
          if (compactBuffer.length === 2) {
            groups.push({ type: "pair", sections: [...compactBuffer] });
            compactBuffer = [];
          }
        } else {
          if (compactBuffer.length) {
            groups.push({ type: "single", section: compactBuffer[0] });
            compactBuffer = [];
          }
          groups.push({ type: "single", section: s });
        }
      }
      if (compactBuffer.length) {
        groups.push({ type: "single", section: compactBuffer[0] });
      }
      return groups;
    });
    return (_ctx, _push, _parent, _attrs) => {
      const _component_SectionBlock = __nuxt_component_0;
      _push(`<div${ssrRenderAttrs(_attrs)}>`);
      if (unref(loading)) {
        _push(`<div class="space-y-6"><!--[-->`);
        ssrRenderList(3, (n) => {
          _push(`<div class="animate-pulse"><div class="h-8 rounded w-1/4 mb-3" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-tertiary)" })}"></div><div class="h-4 rounded w-full mb-2" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-secondary)" })}"></div><div class="h-4 rounded w-3/4" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-secondary)" })}"></div></div>`);
        });
        _push(`<!--]--></div>`);
      } else if (unref(error)) {
        _push(`<div class="rounded-lg p-6 text-center" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-secondary)", border: "1px solid var(--color-border)" })}"><p class="text-red-500 mb-2">${ssrInterpolate(unref(t)("about.loadError"))}</p><p style="${ssrRenderStyle({ color: "var(--color-text-tertiary)" })}" class="text-sm">${ssrInterpolate(unref(t)("about.loadErrorHint"))}</p></div>`);
      } else {
        _push(`<!--[-->`);
        ssrRenderList(unref(layoutGroups), (group, gi) => {
          _push(`<!--[-->`);
          if (group.type === "pair") {
            _push(`<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6"><!--[-->`);
            ssrRenderList(group.sections, (s) => {
              _push(ssrRenderComponent(_component_SectionBlock, {
                key: s.id,
                section: s,
                compact: true
              }, null, _parent));
            });
            _push(`<!--]--></div>`);
          } else {
            _push(ssrRenderComponent(_component_SectionBlock, {
              section: group.section
            }, null, _parent));
          }
          _push(`<!--]-->`);
        });
        _push(`<!--]-->`);
      }
      _push(`</div>`);
    };
  }
};
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("pages/about.vue");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
export {
  _sfc_main as default
};
//# sourceMappingURL=about-B0Ltgr1U.js.map
