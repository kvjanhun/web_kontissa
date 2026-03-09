import { ref, mergeProps, unref, useSSRContext, computed, resolveComponent, createVNode, resolveDynamicComponent } from "vue";
import { ssrRenderAttrs, ssrInterpolate, ssrRenderStyle, ssrRenderAttr, ssrIncludeBooleanAttr, ssrLooseContain, ssrLooseEqual, ssrRenderList, ssrRenderClass, ssrRenderComponent, ssrRenderVNode } from "vue/server-renderer";
import { u as useI18nStore, a as useRouter, b as useAuthStore } from "../server.mjs";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/hookable/dist/index.mjs";
import { u as useHead } from "./v3-DCBci_gg.js";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/klona/dist/index.mjs";
import "#internal/nuxt/paths";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/defu/dist/defu.mjs";
import { storeToRefs } from "pinia";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ofetch/dist/node.mjs";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unctx/dist/index.mjs";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/h3/dist/index.mjs";
import "vue-router";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ufo/dist/index.mjs";
import "/Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/@unhead/vue/dist/index.mjs";
const _sfc_main$8 = {
  __name: "AdminSections",
  __ssrInlineRender: true,
  setup(__props) {
    const { t } = useI18nStore();
    const sections = ref([]);
    const editingId = ref(null);
    const error = ref("");
    const success = ref("");
    const TYPE_COLORS = {
      text: "bg-stone-500/20 text-stone-400",
      pills: "bg-blue-500/20 text-blue-400",
      quote: "bg-purple-500/20 text-purple-400",
      currently: "bg-green-500/20 text-green-400"
    };
    const form = ref({ title: "", slug: "", content: "", section_type: "text" });
    const editForm = ref({ title: "", slug: "", content: "", section_type: "text" });
    return (_ctx, _push, _parent, _attrs) => {
      _push(`<div${ssrRenderAttrs(mergeProps({ class: "space-y-4" }, _attrs))}>`);
      if (error.value) {
        _push(`<div role="alert" class="p-3 rounded-lg text-sm bg-red-500/10 text-red-400 border border-red-500/20">${ssrInterpolate(error.value)}</div>`);
      } else {
        _push(`<!---->`);
      }
      if (success.value) {
        _push(`<div role="status" class="p-3 rounded-lg text-sm bg-green-500/10 text-green-400 border border-green-500/20">${ssrInterpolate(success.value)}</div>`);
      } else {
        _push(`<!---->`);
      }
      _push(`<div class="p-4 rounded-lg" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-secondary)", border: "1px solid var(--color-border)" })}"><h2 class="text-lg font-medium mb-3" style="${ssrRenderStyle({ color: "var(--color-text-primary)" })}">${ssrInterpolate(unref(t)("admin.addSection"))}</h2><form class="space-y-3"><div class="flex flex-col sm:flex-row gap-3"><input${ssrRenderAttr("value", form.value.title)}${ssrRenderAttr("placeholder", unref(t)("admin.title"))} required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-primary)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" })}"><input${ssrRenderAttr("value", form.value.slug)}${ssrRenderAttr("placeholder", unref(t)("admin.slug"))} required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-primary)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" })}"><select class="px-3 py-2 rounded-lg text-sm outline-none" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-primary)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" })}"><option value="text"${ssrIncludeBooleanAttr(Array.isArray(form.value.section_type) ? ssrLooseContain(form.value.section_type, "text") : ssrLooseEqual(form.value.section_type, "text")) ? " selected" : ""}>Text</option><option value="pills"${ssrIncludeBooleanAttr(Array.isArray(form.value.section_type) ? ssrLooseContain(form.value.section_type, "pills") : ssrLooseEqual(form.value.section_type, "pills")) ? " selected" : ""}>Pills</option><option value="quote"${ssrIncludeBooleanAttr(Array.isArray(form.value.section_type) ? ssrLooseContain(form.value.section_type, "quote") : ssrLooseEqual(form.value.section_type, "quote")) ? " selected" : ""}>Quote</option><option value="currently"${ssrIncludeBooleanAttr(Array.isArray(form.value.section_type) ? ssrLooseContain(form.value.section_type, "currently") : ssrLooseEqual(form.value.section_type, "currently")) ? " selected" : ""}>Currently</option></select></div><textarea${ssrRenderAttr("placeholder", form.value.section_type === "pills" ? "Comma-separated values, e.g. Python, Flask, Vue.js" : form.value.section_type === "quote" ? "A short tagline or quote" : form.value.section_type === "currently" ? "One item per line, e.g.\nPlaying: Elden Ring\nReading: SICP" : unref(t)("admin.contentHtml"))} required rows="4" class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-y" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-primary)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" })}">${ssrInterpolate(form.value.content)}</textarea><button type="submit" class="bg-accent text-white px-4 py-2 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90">${ssrInterpolate(unref(t)("admin.addSection"))}</button></form></div><!--[-->`);
      ssrRenderList(sections.value, (section, idx) => {
        _push(`<div class="p-4 rounded-lg" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-secondary)", border: "1px solid var(--color-border)" })}">`);
        if (editingId.value !== section.id) {
          _push(`<div><div class="flex justify-between items-start mb-2"><div><h3 class="text-base font-medium" style="${ssrRenderStyle({ color: "var(--color-text-primary)" })}">${ssrInterpolate(section.title)}</h3><span class="text-xs" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">slug: ${ssrInterpolate(section.slug)} | id: ${ssrInterpolate(section.id)} | pos: ${ssrInterpolate(section.position)}</span><span class="${ssrRenderClass([TYPE_COLORS[section.section_type || "text"], "text-xs px-1.5 py-0.5 rounded-full ml-2"])}">${ssrInterpolate(section.section_type || "text")}</span></div><div class="flex gap-2"><button${ssrIncludeBooleanAttr(idx === 0) ? " disabled" : ""} class="text-xs px-2 py-1 rounded transition-colors duration-200 hover:bg-white/10 disabled:opacity-30" style="${ssrRenderStyle({ color: "var(--color-text-secondary)", border: "1px solid var(--color-border)" })}" aria-label="Move up">↑</button><button${ssrIncludeBooleanAttr(idx === sections.value.length - 1) ? " disabled" : ""} class="text-xs px-2 py-1 rounded transition-colors duration-200 hover:bg-white/10 disabled:opacity-30" style="${ssrRenderStyle({ color: "var(--color-text-secondary)", border: "1px solid var(--color-border)" })}" aria-label="Move down">↓</button><button class="text-xs px-3 py-1 rounded transition-colors duration-200 hover:bg-white/10" style="${ssrRenderStyle({ color: "var(--color-text-secondary)", border: "1px solid var(--color-border)" })}">${ssrInterpolate(unref(t)("admin.edit"))}</button><button class="text-xs px-3 py-1 rounded text-red-400 transition-colors duration-200 hover:bg-red-500/10" style="${ssrRenderStyle({ border: "1px solid var(--color-border)" })}">${ssrInterpolate(unref(t)("admin.delete"))}</button></div></div><p class="text-sm truncate" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(section.content.substring(0, 200))}</p></div>`);
        } else {
          _push(`<form class="space-y-3"><div class="flex flex-col sm:flex-row gap-3"><input${ssrRenderAttr("value", editForm.value.title)} required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-primary)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" })}"><input${ssrRenderAttr("value", editForm.value.slug)} required class="flex-1 px-3 py-2 rounded-lg text-sm outline-none" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-primary)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" })}"><select class="px-3 py-2 rounded-lg text-sm outline-none" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-primary)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" })}"><option value="text"${ssrIncludeBooleanAttr(Array.isArray(editForm.value.section_type) ? ssrLooseContain(editForm.value.section_type, "text") : ssrLooseEqual(editForm.value.section_type, "text")) ? " selected" : ""}>Text</option><option value="pills"${ssrIncludeBooleanAttr(Array.isArray(editForm.value.section_type) ? ssrLooseContain(editForm.value.section_type, "pills") : ssrLooseEqual(editForm.value.section_type, "pills")) ? " selected" : ""}>Pills</option><option value="quote"${ssrIncludeBooleanAttr(Array.isArray(editForm.value.section_type) ? ssrLooseContain(editForm.value.section_type, "quote") : ssrLooseEqual(editForm.value.section_type, "quote")) ? " selected" : ""}>Quote</option><option value="currently"${ssrIncludeBooleanAttr(Array.isArray(editForm.value.section_type) ? ssrLooseContain(editForm.value.section_type, "currently") : ssrLooseEqual(editForm.value.section_type, "currently")) ? " selected" : ""}>Currently</option></select></div><textarea${ssrRenderAttr("placeholder", editForm.value.section_type === "pills" ? "Comma-separated values, e.g. Python, Flask, Vue.js" : editForm.value.section_type === "quote" ? "A short tagline or quote" : editForm.value.section_type === "currently" ? "One item per line, e.g.\nPlaying: Elden Ring\nReading: SICP" : unref(t)("admin.contentHtml"))} required rows="4" class="w-full px-3 py-2 rounded-lg text-sm outline-none resize-y" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-primary)", border: "1px solid var(--color-border)", color: "var(--color-text-primary)" })}">${ssrInterpolate(editForm.value.content)}</textarea><div class="flex gap-2"><button type="submit" class="bg-accent text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-opacity duration-200 hover:opacity-90">${ssrInterpolate(unref(t)("admin.save"))}</button><button type="button" class="px-4 py-1.5 rounded-lg text-sm transition-colors duration-200 hover:bg-white/10" style="${ssrRenderStyle({ color: "var(--color-text-secondary)", border: "1px solid var(--color-border)" })}">${ssrInterpolate(unref(t)("admin.cancel"))}</button></div></form>`);
        }
        _push(`</div>`);
      });
      _push(`<!--]-->`);
      if (!sections.value.length) {
        _push(`<p class="text-center py-8" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(unref(t)("admin.noSections"))}</p>`);
      } else {
        _push(`<!---->`);
      }
      _push(`</div>`);
    };
  }
};
const _sfc_setup$8 = _sfc_main$8.setup;
_sfc_main$8.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("components/admin/AdminSections.vue");
  return _sfc_setup$8 ? _sfc_setup$8(props, ctx) : void 0;
};
const W = 800;
const H = 280;
const _sfc_main$7 = {
  __name: "AdminPageViews",
  __ssrInlineRender: true,
  setup(__props) {
    const pageViews = ref([]);
    const events = ref(null);
    const loading = ref(true);
    const selectedDays = ref(7);
    const enabledPaths = ref(/* @__PURE__ */ new Set());
    const PATH_COLORS = ["#ff643e", "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"];
    function pathColor(path) {
      if (!events.value) return PATH_COLORS[0];
      const idx = events.value.paths.indexOf(path);
      return PATH_COLORS[idx % PATH_COLORS.length];
    }
    const PAD = { top: 20, right: 20, bottom: 40, left: 45 };
    const chartW = W - PAD.left - PAD.right;
    const chartH = H - PAD.top - PAD.bottom;
    const maxCount = computed(() => {
      if (!events.value) return 0;
      let max = 0;
      for (const day of events.value.series) {
        for (const [path, count] of Object.entries(day.counts)) {
          if (enabledPaths.value.has(path) && count > max) max = count;
        }
      }
      return max || 1;
    });
    const yTicks = computed(() => {
      const m = maxCount.value;
      if (m <= 5) return Array.from({ length: m + 1 }, (_, i) => i);
      const step = Math.ceil(m / 5);
      const ticks = [];
      for (let i = 0; i <= m; i += step) ticks.push(i);
      if (ticks[ticks.length - 1] < m) ticks.push(m);
      return ticks;
    });
    const xLabels = computed(() => {
      if (!events.value) return [];
      const series = events.value.series;
      const step = Math.max(1, Math.floor(series.length / 7));
      const labels = [];
      for (let i = 0; i < series.length; i += step) {
        labels.push({ idx: i, label: series[i].date.slice(5) });
      }
      const last = series.length - 1;
      if (labels.length === 0 || labels[labels.length - 1].idx !== last) {
        labels.push({ idx: last, label: series[last].date.slice(5) });
      }
      return labels;
    });
    function polyline(path) {
      if (!events.value) return "";
      const series = events.value.series;
      const len = series.length;
      if (len === 0) return "";
      const m = maxCount.value;
      return series.map((day, i) => {
        const x = PAD.left + (len > 1 ? i / (len - 1) * chartW : chartW / 2);
        const count = day.counts[path] || 0;
        const y = PAD.top + chartH - count / m * chartH;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(" ");
    }
    function xPos(i) {
      const len = events.value?.series.length || 1;
      return PAD.left + (len > 1 ? i / (len - 1) * chartW : chartW / 2);
    }
    function yPos(val) {
      return PAD.top + chartH - val / maxCount.value * chartH;
    }
    function formatDate(iso) {
      if (!iso) return "-";
      return new Date(iso).toLocaleString();
    }
    return (_ctx, _push, _parent, _attrs) => {
      _push(`<div${ssrRenderAttrs(_attrs)}>`);
      if (loading.value) {
        _push(`<div class="text-center py-4" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Loading...</div>`);
      } else {
        _push(`<!--[-->`);
        if (events.value) {
          _push(`<div class="flex gap-2 mb-4"><!--[-->`);
          ssrRenderList([7, 30, 90], (d) => {
            _push(`<button class="px-3 py-1 rounded text-sm font-medium" style="${ssrRenderStyle({
              background: selectedDays.value === d ? "var(--color-accent)" : "var(--color-bg-secondary)",
              color: selectedDays.value === d ? "white" : "var(--color-text-secondary)",
              border: "1px solid " + (selectedDays.value === d ? "var(--color-accent)" : "var(--color-border)"),
              cursor: "pointer"
            })}">${ssrInterpolate(d)}d</button>`);
          });
          _push(`<!--]--></div>`);
        } else {
          _push(`<!---->`);
        }
        if (events.value && events.value.series.length > 0) {
          _push(`<div class="mb-4 overflow-x-auto"><svg${ssrRenderAttr("viewBox", `0 0 ${W} ${H}`)} class="w-full" style="${ssrRenderStyle({ "min-width": "400px" })}"><!--[-->`);
          ssrRenderList(yTicks.value, (tick) => {
            _push(`<line${ssrRenderAttr("x1", PAD.left)}${ssrRenderAttr("y1", yPos(tick))}${ssrRenderAttr("x2", W - PAD.right)}${ssrRenderAttr("y2", yPos(tick))} stroke="var(--color-border)" stroke-width="0.5"></line>`);
          });
          _push(`<!--]--><!--[-->`);
          ssrRenderList(yTicks.value, (tick) => {
            _push(`<text${ssrRenderAttr("x", PAD.left - 8)}${ssrRenderAttr("y", yPos(tick) + 4)} text-anchor="end" fill="var(--color-text-tertiary)" font-size="11">${ssrInterpolate(tick)}</text>`);
          });
          _push(`<!--]--><!--[-->`);
          ssrRenderList(xLabels.value, (lbl) => {
            _push(`<text${ssrRenderAttr("x", xPos(lbl.idx))}${ssrRenderAttr("y", H - 8)} text-anchor="middle" fill="var(--color-text-tertiary)" font-size="11">${ssrInterpolate(lbl.label)}</text>`);
          });
          _push(`<!--]--><!--[-->`);
          ssrRenderList(events.value.paths, (path) => {
            _push(`<polyline${ssrRenderAttr("points", polyline(path))} fill="none"${ssrRenderAttr("stroke", pathColor(path))} stroke-width="2" stroke-linejoin="round" stroke-linecap="round" style="${ssrRenderStyle(enabledPaths.value.has(path) ? null : { display: "none" })}"></polyline>`);
          });
          _push(`<!--]--></svg></div>`);
        } else {
          _push(`<!---->`);
        }
        if (events.value && events.value.paths.length > 0) {
          _push(`<div class="flex flex-wrap gap-2 mb-6"><!--[-->`);
          ssrRenderList(events.value.paths, (path) => {
            _push(`<button class="px-3 py-1 rounded-full text-xs font-medium" style="${ssrRenderStyle({
              background: enabledPaths.value.has(path) ? pathColor(path) + "20" : "var(--color-bg-secondary)",
              color: enabledPaths.value.has(path) ? pathColor(path) : "var(--color-text-tertiary)",
              border: "1px solid " + (enabledPaths.value.has(path) ? pathColor(path) : "var(--color-border)"),
              cursor: "pointer"
            })}">${ssrInterpolate(path)}</button>`);
          });
          _push(`<!--]--></div>`);
        } else {
          _push(`<!---->`);
        }
        if (pageViews.value.length === 0) {
          _push(`<div class="text-center py-4" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">No page views recorded yet.</div>`);
        } else {
          _push(`<table class="w-full text-sm"><thead><tr style="${ssrRenderStyle({ borderBottom: "1px solid var(--color-border)" })}"><th class="text-left py-2 px-3 font-medium" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Path</th><th class="text-right py-2 px-3 font-medium" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Views</th><th class="text-right py-2 px-3 font-medium" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">First Seen</th><th class="text-right py-2 px-3 font-medium" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Last Updated</th></tr></thead><tbody><!--[-->`);
          ssrRenderList(pageViews.value, (pv) => {
            _push(`<tr style="${ssrRenderStyle({ borderBottom: "1px solid var(--color-border)" })}"><td class="py-2 px-3" style="${ssrRenderStyle({ color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" })}">${ssrInterpolate(pv.path)}</td><td class="text-right py-2 px-3" style="${ssrRenderStyle({ color: "var(--color-text-primary)" })}">${ssrInterpolate(pv.count)}</td><td class="text-right py-2 px-3 text-xs" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(formatDate(pv.created_at))}</td><td class="text-right py-2 px-3 text-xs" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(formatDate(pv.updated_at))}</td></tr>`);
          });
          _push(`<!--]--></tbody></table>`);
        }
        _push(`<!--]-->`);
      }
      _push(`</div>`);
    };
  }
};
const _sfc_setup$7 = _sfc_main$7.setup;
_sfc_main$7.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("components/admin/AdminPageViews.vue");
  return _sfc_setup$7 ? _sfc_setup$7(props, ctx) : void 0;
};
const _sfc_main$6 = {
  __name: "AdminRecipes",
  __ssrInlineRender: true,
  setup(__props) {
    const recipes = ref([]);
    const loading = ref(true);
    const error = ref("");
    function formatDate(iso) {
      if (!iso) return "-";
      return new Date(iso).toLocaleDateString();
    }
    return (_ctx, _push, _parent, _attrs) => {
      _push(`<div${ssrRenderAttrs(_attrs)}>`);
      if (error.value) {
        _push(`<div role="alert" class="mb-4 p-3 rounded-lg text-sm bg-red-500/10 text-red-400 border border-red-500/20">${ssrInterpolate(error.value)}</div>`);
      } else {
        _push(`<!---->`);
      }
      if (loading.value) {
        _push(`<div class="text-center py-4" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Loading...</div>`);
      } else if (recipes.value.length === 0) {
        _push(`<div class="text-center py-4" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">No recipes yet.</div>`);
      } else {
        _push(`<div class="overflow-x-auto"><table class="w-full text-sm"><thead><tr style="${ssrRenderStyle({ borderBottom: "1px solid var(--color-border)" })}"><th class="text-left py-2 px-3 font-medium" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Title</th><th class="text-left py-2 px-3 font-medium" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Category</th><th class="text-right py-2 px-3 font-medium" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Created</th><th class="text-right py-2 px-3 font-medium" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Actions</th></tr></thead><tbody><!--[-->`);
        ssrRenderList(recipes.value, (recipe) => {
          _push(`<tr style="${ssrRenderStyle({ borderBottom: "1px solid var(--color-border)" })}"><td class="py-2 px-3" style="${ssrRenderStyle({ color: "var(--color-text-primary)" })}">${ssrInterpolate(recipe.title)}</td><td class="py-2 px-3" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(recipe.category || "-")}</td><td class="text-right py-2 px-3 text-xs" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(formatDate(recipe.created_at))}</td><td class="text-right py-2 px-3"><a${ssrRenderAttr("href", `/recipes/${recipe.slug}/edit`)} class="text-xs px-2 py-1 rounded transition-colors duration-200 hover:bg-white/10" style="${ssrRenderStyle({ color: "var(--color-text-secondary)", border: "1px solid var(--color-border)" })}">Edit</a><button class="ml-2 text-xs px-2 py-1 rounded text-red-400 transition-colors duration-200 hover:bg-red-500/10" style="${ssrRenderStyle({ border: "1px solid var(--color-border)" })}">Delete</button></td></tr>`);
        });
        _push(`<!--]--></tbody></table></div>`);
      }
      _push(`</div>`);
    };
  }
};
const _sfc_setup$6 = _sfc_main$6.setup;
_sfc_main$6.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("components/admin/AdminRecipes.vue");
  return _sfc_setup$6 ? _sfc_setup$6(props, ctx) : void 0;
};
const _sfc_main$5 = {
  __name: "AdminHealth",
  __ssrInlineRender: true,
  setup(__props) {
    const health = ref(null);
    const loading = ref(true);
    function formatBytes(bytes) {
      if (!bytes) return "0 B";
      const units = ["B", "KB", "MB", "GB", "TB"];
      let i = 0;
      let val = bytes;
      while (val >= 1024 && i < units.length - 1) {
        val /= 1024;
        i++;
      }
      return `${val.toFixed(1)} ${units[i]}`;
    }
    function formatUptime(seconds) {
      if (!seconds) return "0s";
      const d = Math.floor(seconds / 86400);
      const h = Math.floor(seconds % 86400 / 3600);
      const m = Math.floor(seconds % 3600 / 60);
      const s = Math.floor(seconds % 60);
      const parts = [];
      if (d) parts.push(`${d}d`);
      if (h) parts.push(`${h}h`);
      if (m) parts.push(`${m}m`);
      parts.push(`${s}s`);
      return parts.join(" ");
    }
    return (_ctx, _push, _parent, _attrs) => {
      _push(`<div${ssrRenderAttrs(_attrs)}>`);
      if (loading.value) {
        _push(`<div class="text-center py-4" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Loading...</div>`);
      } else if (!health.value) {
        _push(`<div class="text-center py-4" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Failed to load health data.</div>`);
      } else {
        _push(`<div class="space-y-2"><!--[-->`);
        ssrRenderList({
          "Python": health.value.python_version,
          "OS": health.value.os_info || "N/A",
          "Memory (RSS)": health.value.memory_rss_bytes ? formatBytes(health.value.memory_rss_bytes) : "N/A",
          "Database Size": formatBytes(health.value.db_size_bytes),
          "Disk Total": formatBytes(health.value.disk_total_bytes),
          "Disk Free": formatBytes(health.value.disk_free_bytes),
          "Uptime": formatUptime(health.value.uptime_seconds),
          "Requests": health.value.request_count != null ? health.value.request_count.toLocaleString() : "N/A"
        }, (value, label) => {
          _push(`<div class="flex justify-between py-2 px-3 rounded" style="${ssrRenderStyle({ borderBottom: "1px solid var(--color-border)" })}"><span class="text-sm font-medium" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(label)}</span><span class="text-sm" style="${ssrRenderStyle({ color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" })}">${ssrInterpolate(value)}</span></div>`);
        });
        _push(`<!--]-->`);
        if (health.value.table_counts) {
          _push(`<div class="mt-4"><h3 class="text-sm font-medium mb-2 px-3" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">DB Row Counts</h3><!--[-->`);
          ssrRenderList(health.value.table_counts, (count, table) => {
            _push(`<div class="flex justify-between py-1.5 px-3" style="${ssrRenderStyle({ borderBottom: "1px solid var(--color-border)" })}"><span class="text-sm" style="${ssrRenderStyle({ color: "var(--color-text-secondary)", fontFamily: "var(--font-mono)" })}">${ssrInterpolate(table)}</span><span class="text-sm" style="${ssrRenderStyle({ color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" })}">${ssrInterpolate(count != null ? count.toLocaleString() : "N/A")}</span></div>`);
          });
          _push(`<!--]--></div>`);
        } else {
          _push(`<!---->`);
        }
        _push(`</div>`);
      }
      _push(`</div>`);
    };
  }
};
const _sfc_setup$5 = _sfc_main$5.setup;
_sfc_main$5.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("components/admin/AdminHealth.vue");
  return _sfc_setup$5 ? _sfc_setup$5(props, ctx) : void 0;
};
const _sfc_main$4 = {
  __name: "AdminBlockedWords",
  __ssrInlineRender: true,
  setup(__props) {
    const words = ref([]);
    const loading = ref(true);
    const error = ref("");
    function formatDate(iso) {
      if (!iso) return "-";
      return new Date(iso).toLocaleString();
    }
    return (_ctx, _push, _parent, _attrs) => {
      _push(`<div${ssrRenderAttrs(_attrs)}>`);
      if (error.value) {
        _push(`<div role="alert" class="mb-4 p-3 rounded-lg text-sm bg-red-500/10 text-red-400 border border-red-500/20">${ssrInterpolate(error.value)}</div>`);
      } else {
        _push(`<!---->`);
      }
      if (loading.value) {
        _push(`<div class="text-center py-4" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Loading...</div>`);
      } else if (words.value.length === 0) {
        _push(`<div class="text-center py-4" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">No blocked words.</div>`);
      } else {
        _push(`<div class="max-h-96 overflow-y-auto overflow-x-auto"><table class="w-full text-sm"><thead class="sticky top-0" style="${ssrRenderStyle({ backgroundColor: "var(--color-bg-primary)" })}"><tr style="${ssrRenderStyle({ borderBottom: "1px solid var(--color-border)" })}"><th class="text-left py-2 px-3 font-medium" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Word</th><th class="text-right py-2 px-3 font-medium" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Blocked At</th><th class="text-right py-2 px-3 font-medium" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Actions</th></tr></thead><tbody><!--[-->`);
        ssrRenderList(words.value, (bw) => {
          _push(`<tr style="${ssrRenderStyle({ borderBottom: "1px solid var(--color-border)" })}"><td class="py-2 px-3" style="${ssrRenderStyle({ color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" })}">${ssrInterpolate(bw.word)}</td><td class="text-right py-2 px-3 text-xs" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">${ssrInterpolate(formatDate(bw.blocked_at))}</td><td class="text-right py-2 px-3"><button class="text-xs px-2 py-1 rounded text-red-400 transition-colors duration-200 hover:bg-red-500/10" style="${ssrRenderStyle({ border: "1px solid var(--color-border)" })}">Unblock</button></td></tr>`);
        });
        _push(`<!--]--></tbody></table></div>`);
      }
      _push(`</div>`);
    };
  }
};
const _sfc_setup$4 = _sfc_main$4.setup;
_sfc_main$4.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("components/admin/AdminBlockedWords.vue");
  return _sfc_setup$4 ? _sfc_setup$4(props, ctx) : void 0;
};
const _sfc_main$3 = {
  __name: "KennoVariationsGrid",
  __ssrInlineRender: true,
  props: {
    variations: { type: Array, required: true },
    activeCenter: { type: String, default: "" },
    disabled: { type: Boolean, default: false },
    showTarget: { type: Boolean, default: false }
  },
  emits: ["select"],
  setup(__props, { emit: __emit }) {
    return (_ctx, _push, _parent, _attrs) => {
      _push(`<div${ssrRenderAttrs(mergeProps({ class: "grid grid-cols-7 gap-1" }, _attrs))}><!--[-->`);
      ssrRenderList(__props.variations, (v) => {
        _push(`<button class="flex flex-col items-center py-1.5 px-0.5 rounded text-xs leading-tight" style="${ssrRenderStyle({
          background: __props.activeCenter === v.center ? "var(--color-accent)" : "var(--color-bg-secondary)",
          color: __props.activeCenter === v.center ? "white" : "var(--color-text-secondary)",
          border: "1px solid " + (__props.activeCenter === v.center ? "var(--color-accent)" : "var(--color-border)"),
          cursor: __props.activeCenter === v.center ? "default" : __props.disabled ? "wait" : "pointer",
          opacity: __props.disabled && __props.activeCenter !== v.center ? "0.6" : "1"
        })}"${ssrIncludeBooleanAttr(__props.activeCenter === v.center || __props.disabled) ? " disabled" : ""}><span class="font-semibold text-sm">${ssrInterpolate(v.center.toUpperCase())}</span><span>${ssrInterpolate(v.word_count)}w</span><span>${ssrInterpolate(v.max_score)}p</span>`);
        if (__props.showTarget) {
          _push(`<span class="text-xs" style="${ssrRenderStyle({ color: __props.activeCenter === v.center ? "rgba(255,255,255,0.8)" : "var(--color-text-tertiary)" })}">70%: ${ssrInterpolate(Math.ceil(v.max_score * 0.7))}</span>`);
        } else {
          _push(`<!---->`);
        }
        _push(`<span>${ssrInterpolate(v.pangram_count)}pg</span></button>`);
      });
      _push(`<!--]--></div>`);
    };
  }
};
const _sfc_setup$3 = _sfc_main$3.setup;
_sfc_main$3.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("components/admin/KennoVariationsGrid.vue");
  return _sfc_setup$3 ? _sfc_setup$3(props, ctx) : void 0;
};
const WORDS_PER_COLUMN = 10;
const _sfc_main$2 = {
  __name: "KennoWordList",
  __ssrInlineRender: true,
  props: {
    words: { type: Array, required: true },
    letters: { type: Array, required: true },
    loading: { type: Boolean, default: false },
    error: { type: String, default: "" },
    emptyMessage: { type: String, default: "Ei sanoja tälle pelille." }
  },
  emits: ["block"],
  setup(__props, { emit: __emit }) {
    const props = __props;
    const sortedWords = computed(
      () => [...props.words].sort((a, b) => a.localeCompare(b) || a.length - b.length)
    );
    const wordColumns = computed(() => {
      const cols = [];
      for (let i = 0; i < sortedWords.value.length; i += WORDS_PER_COLUMN) {
        cols.push(sortedWords.value.slice(i, i + WORDS_PER_COLUMN));
      }
      return cols;
    });
    function isPangram(word) {
      return props.letters.every((l) => word.includes(l));
    }
    return (_ctx, _push, _parent, _attrs) => {
      if (__props.loading) {
        _push(`<div${ssrRenderAttrs(mergeProps({
          class: "text-sm py-2",
          style: { color: "var(--color-text-secondary)" }
        }, _attrs))}> Ladataan sanoja… </div>`);
      } else if (__props.error) {
        _push(`<div${ssrRenderAttrs(mergeProps({
          class: "text-sm py-2",
          style: { color: "#ef4444" }
        }, _attrs))}>${ssrInterpolate(__props.error)}</div>`);
      } else if (sortedWords.value.length > 0) {
        _push(`<div${ssrRenderAttrs(_attrs)}><p class="text-xs mb-2" style="${ssrRenderStyle({ color: "var(--color-text-tertiary)" })}">${ssrInterpolate(sortedWords.value.length)} sanaa — klikkaa × poistaaksesi sanan pysyvästi </p><div class="flex flex-wrap gap-x-6 gap-y-2"><!--[-->`);
        ssrRenderList(wordColumns.value, (col, ci) => {
          _push(`<ul><!--[-->`);
          ssrRenderList(col, (word) => {
            _push(`<li class="flex items-center gap-1 text-sm py-0.5"><span style="${ssrRenderStyle({ color: isPangram(word) ? "var(--color-accent)" : "var(--color-text-secondary)", fontFamily: "var(--font-mono)", fontWeight: isPangram(word) ? "600" : "normal" })}">${ssrInterpolate(word)}</span><button class="text-xs leading-none opacity-40 hover:opacity-100" style="${ssrRenderStyle({ "color": "#ef4444", "background": "none", "border": "none", "cursor": "pointer", "padding": "0 2px" })}" aria-label="Block word">×</button></li>`);
          });
          _push(`<!--]--></ul>`);
        });
        _push(`<!--]--></div></div>`);
      } else {
        _push(`<div${ssrRenderAttrs(mergeProps({
          class: "text-sm py-2",
          style: { color: "var(--color-text-tertiary)" }
        }, _attrs))}>${ssrInterpolate(__props.emptyMessage)}</div>`);
      }
    };
  }
};
const _sfc_setup$2 = _sfc_main$2.setup;
_sfc_main$2.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("components/admin/KennoWordList.vue");
  return _sfc_setup$2 ? _sfc_setup$2(props, ctx) : void 0;
};
const _sfc_main$1 = {
  __name: "AdminKennoPuzzleTool",
  __ssrInlineRender: true,
  setup(__props) {
    const FINNISH_LETTERS = new Set("abcdefghijklmnopqrstuvwxyzäö");
    const totalPuzzles = ref(null);
    const currentSlot = ref(0);
    const savedLetters = ref(null);
    const savedCenter = ref(null);
    const lettersInput = ref("");
    const selectedCenter = ref("");
    const schedule = ref([]);
    const scheduleLoading = ref(false);
    ref(null);
    const variations = ref([]);
    const variationsLoading = ref(false);
    const variationsError = ref("");
    const words = ref([]);
    const wordsLoading = ref(false);
    const wordsError = ref("");
    const centerSaving = ref(false);
    const saving = ref(false);
    const saveError = ref("");
    const swapSlotInput = ref(null);
    const swapLoading = ref(false);
    const swapError = ref("");
    const swapSuccess = ref("");
    const deleteLoading = ref(false);
    const deleteError = ref("");
    const deleteSuccess = ref("");
    const parsedLetters = computed(() => {
      const raw = lettersInput.value.toLowerCase().replace(/[^a-zäö]/g, "");
      return [...new Set(raw.split(""))].slice(0, 7);
    });
    const lettersValid = computed(() => {
      const letters = parsedLetters.value;
      if (letters.length !== 7) return false;
      return letters.every((l) => l.length === 1 && FINNISH_LETTERS.has(l));
    });
    const duplicates = computed(() => {
      const raw = lettersInput.value.toLowerCase().replace(/[^a-zäö]/g, "");
      const seen = /* @__PURE__ */ new Set();
      const dupes = /* @__PURE__ */ new Set();
      for (const c of raw) {
        if (seen.has(c)) dupes.add(c);
        seen.add(c);
      }
      return [...dupes];
    });
    const invalidChars = computed(() => {
      const raw = lettersInput.value;
      const inv = /* @__PURE__ */ new Set();
      for (const c of raw) {
        if (c === " ") continue;
        if (!FINNISH_LETTERS.has(c.toLowerCase())) inv.add(c);
      }
      return [...inv];
    });
    const validationMessage = computed(() => {
      if (invalidChars.value.length > 0) return `Virheelliset merkit: ${invalidChars.value.join(", ")}`;
      if (duplicates.value.length > 0) return `Tuplat: ${duplicates.value.join(", ")}`;
      const count = parsedLetters.value.length;
      if (count < 7) return `${count}/7 eri kirjainta`;
      return "7 eri kirjainta";
    });
    const validationOk = computed(
      () => lettersValid.value && duplicates.value.length === 0 && invalidChars.value.length === 0
    );
    const isDirty = computed(() => {
      if (savedLetters.value === null) return true;
      const sorted = [...parsedLetters.value].sort();
      if (sorted.length !== 7) return true;
      return sorted.join(",") !== [...savedLetters.value].sort().join(",");
    });
    const todaySlot = computed(() => {
      const entry = schedule.value.find((e) => e.is_today);
      return entry != null ? entry.slot : null;
    });
    const isToday = computed(
      () => todaySlot.value !== null && currentSlot.value === todaySlot.value
    );
    const displayNumber = computed(() => currentSlot.value + 1);
    const canSave = computed(() => {
      if (!validationOk.value) return false;
      if (!selectedCenter.value && isDirty.value) return false;
      if (isToday.value) return false;
      if (saving.value) return false;
      return isDirty.value;
    });
    const canSwap = computed(() => {
      if (swapSlotInput.value == null || swapSlotInput.value < 1) return false;
      const other = swapSlotInput.value - 1;
      if (other === currentSlot.value) return false;
      if (todaySlot.value !== null && (currentSlot.value === todaySlot.value || other === todaySlot.value)) return false;
      if (totalPuzzles.value && other >= totalPuzzles.value) return false;
      return true;
    });
    const canDelete = computed(() => !isToday.value);
    const slotNextDate = computed(() => {
      const map = /* @__PURE__ */ new Map();
      for (const entry of schedule.value) {
        if (!map.has(entry.slot)) {
          map.set(entry.slot, entry.date);
        }
      }
      return map;
    });
    function formatDateShort(isoDate) {
      return new Date(isoDate).toLocaleDateString("fi-FI", { weekday: "short", day: "numeric", month: "numeric" });
    }
    const allSlotRows = computed(() => {
      const total = totalPuzzles.value ?? 0;
      const rows = [];
      for (let i = 0; i < total; i++) {
        const dateStr = slotNextDate.value.get(i);
        rows.push({
          slot: i,
          displayNumber: i + 1,
          isToday: todaySlot.value === i,
          date: dateStr ? formatDateShort(dateStr) : null
        });
      }
      return rows;
    });
    async function loadSlot(slot) {
      currentSlot.value = slot;
      savedLetters.value = null;
      savedCenter.value = null;
      selectedCenter.value = "";
      variations.value = [];
      words.value = [];
      variationsError.value = "";
      wordsError.value = "";
      saveError.value = "";
      swapError.value = "";
      swapSuccess.value = "";
      deleteError.value = "";
      deleteSuccess.value = "";
      const [puzzleOk, variationsOk] = await Promise.all([
        fetchPuzzle(slot),
        fetchVariations(slot)
      ]);
    }
    async function fetchPuzzle(slot) {
      wordsLoading.value = true;
      wordsError.value = "";
      try {
        const res = await fetch(`/api/kenno?puzzle=${slot}`);
        if (!res.ok) throw new Error();
        const data = await res.json();
        const allLetters = [data.center, ...data.letters].sort();
        savedLetters.value = allLetters;
        savedCenter.value = data.center;
        lettersInput.value = allLetters.join("");
        words.value = data.words ?? [];
        totalPuzzles.value = data.total_puzzles;
        return true;
      } catch {
        wordsError.value = "Pelin lataus epäonnistui.";
        words.value = [];
        return false;
      } finally {
        wordsLoading.value = false;
      }
    }
    async function fetchVariations(slot) {
      variationsLoading.value = true;
      variationsError.value = "";
      try {
        const res = await fetch(`/api/kenno/variations?puzzle=${slot}`);
        if (!res.ok) throw new Error();
        const data = await res.json();
        variations.value = data.variations;
        return true;
      } catch {
        variationsError.value = "Variaatioiden lataus epäonnistui.";
        variations.value = [];
        return false;
      } finally {
        variationsLoading.value = false;
      }
    }
    async function setCenter(letter) {
      if (centerSaving.value) return;
      centerSaving.value = true;
      try {
        const res = await fetch("/api/kenno/center", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ puzzle: currentSlot.value, center: letter })
        });
        if (!res.ok) throw new Error();
        await loadSlot(currentSlot.value);
      } catch {
        variationsError.value = "Keskuskirjaimen vaihto epäonnistui.";
      } finally {
        centerSaving.value = false;
      }
    }
    async function blockWord(word) {
      if (!confirm(`Poista "${word}" sanalistalta pysyvästi?`)) return;
      try {
        const res = await fetch("/api/kenno/block", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ word })
        });
        if (!res.ok) throw new Error();
        if (isDirty.value && selectedCenter.value) {
          const center = selectedCenter.value;
          await fetchPreview();
          await selectPreviewCenter(center);
        } else {
          await loadSlot(currentSlot.value);
        }
      } catch {
        wordsError.value = "Sanan poisto epäonnistui.";
      }
    }
    async function fetchPreview() {
      if (!validationOk.value) return;
      variationsLoading.value = true;
      variationsError.value = "";
      selectedCenter.value = "";
      try {
        const res = await fetch("/api/kenno/preview", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ letters: parsedLetters.value })
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.error || "Esikatselu epäonnistui");
        }
        const data = await res.json();
        variations.value = data.variations.map((v) => ({ ...v, is_active: false }));
      } catch (e) {
        variationsError.value = e.message || "Esikatselu epäonnistui.";
        variations.value = [];
      } finally {
        variationsLoading.value = false;
      }
    }
    async function selectPreviewCenter(letter) {
      selectedCenter.value = letter;
      wordsLoading.value = true;
      wordsError.value = "";
      try {
        const res = await fetch("/api/kenno/preview", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ letters: parsedLetters.value, center: letter })
        });
        if (!res.ok) {
          if (res.status === 429) {
            wordsError.value = "Liian monta pyyntöä — odota hetki.";
          }
          throw new Error();
        }
        const data = await res.json();
        words.value = data.words ?? [];
      } catch {
        if (!wordsError.value) wordsError.value = "Sanalistan lataus epäonnistui.";
        words.value = [];
      } finally {
        wordsLoading.value = false;
      }
    }
    return (_ctx, _push, _parent, _attrs) => {
      _push(`<div${ssrRenderAttrs(_attrs)}><div class="flex flex-col md:flex-row gap-4"><div class="md:shrink-0" style="${ssrRenderStyle({ "width": "fit-content", "max-width": "11rem" })}"><div class="flex items-center gap-2 mb-1"><p class="text-xs font-semibold" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Pelit</p><button class="rounded text-xs px-2 py-0.5" style="${ssrRenderStyle({
        background: "var(--color-accent)",
        color: "white",
        border: "1px solid var(--color-accent)",
        cursor: "pointer"
      })}">Uusi</button></div>`);
      if (allSlotRows.value.length > 0) {
        _push(`<div style="${ssrRenderStyle([{ "max-height": "32rem", "overflow-y": "auto" }, { border: "1px solid var(--color-border)", borderRadius: "4px" }])}"><!--[-->`);
        ssrRenderList(allSlotRows.value, (row) => {
          _push(`<div${ssrRenderAttr("data-active", row.slot === currentSlot.value ? "true" : void 0)} class="flex items-center gap-1 px-0.5 py-0.5 text-xs cursor-pointer hover:opacity-80" style="${ssrRenderStyle({
            background: row.slot === currentSlot.value ? "rgba(255, 100, 62, 0.15)" : row.isToday ? "rgba(239, 68, 68, 0.1)" : "transparent"
          })}"><span style="${ssrRenderStyle({ color: "var(--color-text-primary)", fontFamily: "var(--font-mono)", minWidth: "1.25rem", textAlign: "right" })}">${ssrInterpolate(row.displayNumber)}</span>`);
          if (row.date) {
            _push(`<span class="truncate" style="${ssrRenderStyle({ color: "var(--color-text-tertiary)" })}">${ssrInterpolate(row.date)}</span>`);
          } else {
            _push(`<!---->`);
          }
          if (row.isToday) {
            _push(`<span class="px-1 rounded shrink-0" style="${ssrRenderStyle({ "background": "#ef4444", "color": "white", "font-size": "0.625rem", "line-height": "1.4" })}">tänään</span>`);
          } else {
            _push(`<!---->`);
          }
          if (row.slot === currentSlot.value) {
            _push(`<span class="shrink-0" style="${ssrRenderStyle({ color: "var(--color-accent)" })}">●</span>`);
          } else {
            _push(`<!---->`);
          }
          _push(`</div>`);
        });
        _push(`<!--]--></div>`);
      } else if (scheduleLoading.value) {
        _push(`<div class="text-xs" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}"> Ladataan… </div>`);
      } else {
        _push(`<!---->`);
      }
      _push(`</div><div class="flex-1 min-w-0"><div class="flex flex-wrap items-center gap-x-3 gap-y-2 mb-3"><div class="flex items-center gap-1"><label class="text-xs" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">Peli</label><input type="number"${ssrRenderAttr("value", displayNumber.value)} min="1"${ssrRenderAttr("max", totalPuzzles.value ?? 999)} class="rounded text-center" style="${ssrRenderStyle({ "width": "3.5rem", "background": "var(--color-bg-secondary)", "color": "var(--color-text-primary)", "border": "1px solid var(--color-border)", "padding": "2px 4px", "font-size": "0.875rem" })}"><span class="text-xs" style="${ssrRenderStyle({ color: "var(--color-text-tertiary)" })}">/${ssrInterpolate(totalPuzzles.value ?? "…")}</span></div><div class="flex items-center gap-1"><input type="text"${ssrRenderAttr("value", lettersInput.value)} placeholder="kirjaimet" maxlength="14" class="rounded" style="${ssrRenderStyle({ "width": "7rem", "background": "var(--color-bg-secondary)", "color": "var(--color-text-primary)", "border": "1px solid var(--color-border)", "padding": "2px 6px", "font-size": "0.875rem", "font-family": "var(--font-mono)" })}"><button class="rounded text-xs px-1.5 py-0.5" style="${ssrRenderStyle({ background: "var(--color-bg-secondary)", color: "var(--color-text-tertiary)", border: "1px solid var(--color-border)" })}">Tyhjennä</button>`);
      if (isDirty.value && savedLetters.value !== null) {
        _push(`<button class="rounded text-xs px-1.5 py-0.5" style="${ssrRenderStyle({ background: "var(--color-bg-secondary)", color: "var(--color-text-tertiary)", border: "1px solid var(--color-border)" })}">Palauta</button>`);
      } else {
        _push(`<!---->`);
      }
      _push(`</div><div class="flex items-center gap-1"><span class="text-xs" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}">↔</span><input type="number"${ssrRenderAttr("value", swapSlotInput.value)} min="1"${ssrRenderAttr("max", totalPuzzles.value ?? 999)} class="rounded text-center" style="${ssrRenderStyle({ "width": "3.5rem", "background": "var(--color-bg-secondary)", "color": "var(--color-text-primary)", "border": "1px solid var(--color-border)", "padding": "2px 4px", "font-size": "0.875rem" })}"><button${ssrIncludeBooleanAttr(!canSwap.value || swapLoading.value) ? " disabled" : ""} class="rounded text-xs px-1.5 py-0.5" style="${ssrRenderStyle({
        background: canSwap.value ? "var(--color-accent)" : "var(--color-bg-secondary)",
        color: canSwap.value ? "white" : "var(--color-text-tertiary)",
        border: "1px solid " + (canSwap.value ? "var(--color-accent)" : "var(--color-border)"),
        cursor: canSwap.value && !swapLoading.value ? "pointer" : "default",
        opacity: swapLoading.value ? "0.6" : "1"
      })}">${ssrInterpolate(swapLoading.value ? "…" : "Vaihda")}</button></div>`);
      if (canDelete.value) {
        _push(`<button${ssrIncludeBooleanAttr(deleteLoading.value) ? " disabled" : ""} class="rounded text-xs px-1.5 py-0.5" style="${ssrRenderStyle({
          background: "#ef4444",
          color: "white",
          border: "1px solid #ef4444",
          cursor: deleteLoading.value ? "wait" : "pointer",
          opacity: deleteLoading.value ? "0.6" : "1"
        })}">${ssrInterpolate(deleteLoading.value ? "…" : "Poista")}</button>`);
      } else {
        _push(`<!---->`);
      }
      _push(`</div>`);
      if (isToday.value) {
        _push(`<p class="text-xs mb-2" style="${ssrRenderStyle({ "color": "#ef4444" })}">Tämän päivän peliä ei voi muokata.</p>`);
      } else {
        _push(`<!---->`);
      }
      if (swapError.value) {
        _push(`<p class="text-xs mb-2" style="${ssrRenderStyle({ "color": "#ef4444" })}">${ssrInterpolate(swapError.value)}</p>`);
      } else {
        _push(`<!---->`);
      }
      if (swapSuccess.value) {
        _push(`<p class="text-xs mb-2" style="${ssrRenderStyle({ color: "var(--color-accent)" })}">${ssrInterpolate(swapSuccess.value)}</p>`);
      } else {
        _push(`<!---->`);
      }
      if (deleteError.value) {
        _push(`<p class="text-xs mb-2" style="${ssrRenderStyle({ "color": "#ef4444" })}">${ssrInterpolate(deleteError.value)}</p>`);
      } else {
        _push(`<!---->`);
      }
      if (deleteSuccess.value) {
        _push(`<p class="text-xs mb-2" style="${ssrRenderStyle({ color: "var(--color-accent)" })}">${ssrInterpolate(deleteSuccess.value)}</p>`);
      } else {
        _push(`<!---->`);
      }
      _push(`<div class="flex gap-1 mb-2"><!--[-->`);
      ssrRenderList(7, (i) => {
        _push(`<div class="flex items-center justify-center rounded font-semibold text-sm" style="${ssrRenderStyle({
          width: "2rem",
          height: "2rem",
          background: parsedLetters.value[i - 1] ? "var(--color-accent)" : "var(--color-bg-secondary)",
          color: parsedLetters.value[i - 1] ? "white" : "var(--color-text-tertiary)",
          border: "1px solid " + (parsedLetters.value[i - 1] ? "var(--color-accent)" : "var(--color-border)")
        })}">${ssrInterpolate(parsedLetters.value[i - 1]?.toUpperCase() ?? "")}</div>`);
      });
      _push(`<!--]--></div><p class="text-xs mb-3" style="${ssrRenderStyle({ color: validationOk.value ? "var(--color-text-tertiary)" : "#ef4444" })}">${ssrInterpolate(validationMessage.value)}</p>`);
      if (isDirty.value) {
        _push(`<!--[--><button${ssrIncludeBooleanAttr(!validationOk.value || variationsLoading.value) ? " disabled" : ""} class="rounded text-xs px-3 py-1.5 mb-3" style="${ssrRenderStyle({
          background: validationOk.value ? "var(--color-accent)" : "var(--color-bg-secondary)",
          color: validationOk.value ? "white" : "var(--color-text-tertiary)",
          border: "1px solid " + (validationOk.value ? "var(--color-accent)" : "var(--color-border)"),
          cursor: validationOk.value && !variationsLoading.value ? "pointer" : "default",
          opacity: variationsLoading.value ? "0.6" : "1"
        })}">${ssrInterpolate(variationsLoading.value ? "Lasketaan…" : "Esikatsele")}</button>`);
        if (variationsError.value) {
          _push(`<div class="text-xs mb-3" style="${ssrRenderStyle({ color: "#ef4444" })}">${ssrInterpolate(variationsError.value)}</div>`);
        } else {
          _push(`<!---->`);
        }
        if (variations.value.length > 0) {
          _push(`<div class="mb-4"><p class="text-xs mb-2" style="${ssrRenderStyle({ color: "var(--color-text-tertiary)" })}"> Valitse keskuskirjain klikkaamalla. </p>`);
          _push(ssrRenderComponent(_sfc_main$3, {
            variations: variations.value,
            "active-center": selectedCenter.value,
            "show-target": true,
            onSelect: selectPreviewCenter
          }, null, _parent));
          _push(`</div>`);
        } else {
          _push(`<!---->`);
        }
        if (selectedCenter.value) {
          _push(`<div class="mb-3"><button${ssrIncludeBooleanAttr(!canSave.value) ? " disabled" : ""} class="rounded text-xs px-3 py-1.5" style="${ssrRenderStyle({
            background: canSave.value ? "var(--color-accent)" : "var(--color-bg-secondary)",
            color: canSave.value ? "white" : "var(--color-text-tertiary)",
            border: "1px solid " + (canSave.value ? "var(--color-accent)" : "var(--color-border)"),
            cursor: canSave.value ? "pointer" : "default",
            opacity: saving.value ? "0.6" : "1"
          })}">${ssrInterpolate(saving.value ? "Tallennetaan…" : `Tallenna peliin ${displayNumber.value}`)}</button></div>`);
        } else {
          _push(`<!---->`);
        }
        if (saveError.value) {
          _push(`<p class="text-xs mb-3" style="${ssrRenderStyle({ "color": "#ef4444" })}">${ssrInterpolate(saveError.value)}</p>`);
        } else {
          _push(`<!---->`);
        }
        if (selectedCenter.value) {
          _push(ssrRenderComponent(_sfc_main$2, {
            words: words.value,
            letters: parsedLetters.value,
            loading: wordsLoading.value,
            error: wordsError.value,
            onBlock: blockWord
          }, null, _parent));
        } else {
          _push(`<!---->`);
        }
        _push(`<!--]-->`);
      } else {
        _push(`<!--[-->`);
        if (variationsLoading.value) {
          _push(`<div class="text-sm py-2" style="${ssrRenderStyle({ color: "var(--color-text-secondary)" })}"> Ladataan variaatioita… </div>`);
        } else if (variationsError.value) {
          _push(`<div class="text-sm py-2" style="${ssrRenderStyle({ color: "#ef4444" })}">${ssrInterpolate(variationsError.value)}</div>`);
        } else if (variations.value.length > 0) {
          _push(`<div class="mb-4"><p class="text-xs mb-2" style="${ssrRenderStyle({ color: "var(--color-text-tertiary)" })}"> Keskuskirjain — klikkaa vaihtaaksesi. </p>`);
          _push(ssrRenderComponent(_sfc_main$3, {
            variations: variations.value,
            "active-center": savedCenter.value ?? "",
            disabled: centerSaving.value,
            onSelect: setCenter
          }, null, _parent));
          _push(`</div>`);
        } else {
          _push(`<!---->`);
        }
        if (variations.value.length > 0) {
          _push(ssrRenderComponent(_sfc_main$2, {
            words: words.value,
            letters: parsedLetters.value,
            loading: wordsLoading.value,
            error: wordsError.value,
            onBlock: blockWord
          }, null, _parent));
        } else {
          _push(`<!---->`);
        }
        _push(`<!--]-->`);
      }
      _push(`</div></div></div>`);
    };
  }
};
const _sfc_setup$1 = _sfc_main$1.setup;
_sfc_main$1.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("components/admin/AdminKennoPuzzleTool.vue");
  return _sfc_setup$1 ? _sfc_setup$1(props, ctx) : void 0;
};
const _sfc_main = {
  __name: "admin",
  __ssrInlineRender: true,
  setup(__props) {
    useHead({
      meta: [
        { name: "robots", content: "noindex" }
      ]
    });
    useRouter();
    const { isAdmin } = storeToRefs(useAuthStore());
    const { t } = useI18nStore();
    const tabs = [
      { key: "sections", labelKey: "admin.tab.sections", component: _sfc_main$8 },
      { key: "analytics", labelKey: "admin.tab.analytics", component: _sfc_main$7 },
      { key: "recipes", labelKey: "admin.tab.recipes", component: _sfc_main$6 },
      { key: "health", labelKey: "admin.tab.health", component: _sfc_main$5 },
      { key: "sanakenno", labelKey: "admin.tab.sanakenno", components: [resolveComponent("AdminKennoStats"), _sfc_main$4] },
      { key: "kennotyokalu", labelKey: "admin.tab.kennotyokalu", component: _sfc_main$1 }
    ];
    const activeTab = ref("sections");
    const mountedTabs = ref(/* @__PURE__ */ new Set(["sections"]));
    return (_ctx, _push, _parent, _attrs) => {
      _push(`<div${ssrRenderAttrs(mergeProps({ class: "max-w-3xl mx-auto mt-8" }, _attrs))}><h1 class="text-3xl font-light mb-8" style="${ssrRenderStyle({ color: "var(--color-text-primary)" })}">${ssrInterpolate(unref(t)("admin.heading"))}</h1><div class="flex flex-wrap gap-2 mb-6" role="tablist"><!--[-->`);
      ssrRenderList(tabs, (tab) => {
        _push(`<button role="tab"${ssrRenderAttr("aria-selected", unref(activeTab) === tab.key)}${ssrRenderAttr("id", `tab-${tab.key}`)}${ssrRenderAttr("aria-controls", `panel-${tab.key}`)} class="${ssrRenderClass([unref(activeTab) === tab.key ? "bg-accent text-white" : "hover:bg-white/10", "px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-200"])}" style="${ssrRenderStyle(unref(activeTab) === tab.key ? {} : { color: "var(--color-text-secondary)", border: "1px solid var(--color-border)" })}">${ssrInterpolate(unref(t)(tab.labelKey))}</button>`);
      });
      _push(`<!--]--></div><!--[-->`);
      ssrRenderList(tabs, (tab) => {
        _push(`<div role="tabpanel"${ssrRenderAttr("id", `panel-${tab.key}`)}${ssrRenderAttr("aria-labelledby", `tab-${tab.key}`)} style="${ssrRenderStyle(unref(activeTab) === tab.key ? null : { display: "none" })}">`);
        if (unref(mountedTabs).has(tab.key)) {
          _push(`<!--[-->`);
          if (tab.components) {
            _push(`<div class="space-y-6"><!--[-->`);
            ssrRenderList(tab.components, (comp, i) => {
              ssrRenderVNode(_push, createVNode(resolveDynamicComponent(comp), { key: i }, null), _parent);
            });
            _push(`<!--]--></div>`);
          } else {
            ssrRenderVNode(_push, createVNode(resolveDynamicComponent(tab.component), null, null), _parent);
          }
          _push(`<!--]-->`);
        } else {
          _push(`<!---->`);
        }
        _push(`</div>`);
      });
      _push(`<!--]--></div>`);
    };
  }
};
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("pages/admin.vue");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
export {
  _sfc_main as default
};
//# sourceMappingURL=admin-iLSzzwzd.js.map
