import process from 'node:process';globalThis._importMeta_=globalThis._importMeta_||{url:"file:///_entry.js",env:process.env};import { ref, computed, watch, hasInjectionContext, inject, getCurrentInstance, defineComponent, createElementBlock, shallowRef, provide, cloneVNode, h, defineAsyncComponent, unref, shallowReactive, Suspense, Fragment, createApp, onErrorCaptured, onServerPrefetch, createVNode, resolveDynamicComponent, reactive, effectScope, mergeProps, withCtx, getCurrentScope, toRef, nextTick, isReadonly, toRaw, useSSRContext, isRef, isShallow, isReactive } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/index.mjs';
import { $fetch } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ofetch/dist/node.mjs';
import { b as baseURL } from '../_/renderer.mjs';
import { createHooks } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/hookable/dist/index.mjs';
import { getContext, executeAsync } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unctx/dist/index.mjs';
import { sanitizeStatusCode, createError as createError$1, appendHeader } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/h3/dist/index.mjs';
import { defineStore, setActivePinia, createPinia, shouldHydrate, storeToRefs } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/pinia/dist/pinia.prod.cjs';
import { defu } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/defu/dist/defu.mjs';
import { useRoute as useRoute$1, RouterView, createMemoryHistory, createRouter, START_LOCATION } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue-router/vue-router.node.mjs';
import { parseURL, encodePath, decodePath, hasProtocol, isScriptProtocol, joinURL, withQuery } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ufo/dist/index.mjs';
import { ssrRenderSuspense, ssrRenderComponent, ssrRenderVNode } from 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue/server-renderer/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/vue-bundle-renderer/dist/runtime.mjs';
import '../nitro/nitro.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/destr/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/node-mock-http/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unstorage/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unstorage/drivers/fs.mjs';
import 'node:crypto';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unstorage/drivers/fs-lite.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unstorage/drivers/lru-cache.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/ohash/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/klona/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/scule/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/radix3/dist/index.mjs';
import 'node:fs';
import 'node:url';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/pathe/dist/index.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unhead/dist/server.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/devalue/index.js';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unhead/dist/utils.mjs';
import 'file:///Users/erezac/Projects/web_kontissa/frontend-nuxt/node_modules/unhead/dist/plugins.mjs';

if (!globalThis.$fetch) {
  globalThis.$fetch = $fetch.create({
    baseURL: baseURL()
  });
}
if (!("global" in globalThis)) {
  globalThis.global = globalThis;
}
const appLayoutTransition = false;
const nuxtLinkDefaults = { "componentName": "NuxtLink" };
const appId = "nuxt-app";
const crawlLinks = true;
function getNuxtAppCtx(id = appId) {
  return getContext(id, {
    asyncContext: false
  });
}
const NuxtPluginIndicator = "__nuxt_plugin";
function createNuxtApp(options) {
  let hydratingCount = 0;
  const nuxtApp = {
    _id: options.id || appId || "nuxt-app",
    _scope: effectScope(),
    provide: void 0,
    globalName: "nuxt",
    versions: {
      get nuxt() {
        return "3.21.1";
      },
      get vue() {
        return nuxtApp.vueApp.version;
      }
    },
    payload: shallowReactive({
      ...options.ssrContext?.payload || {},
      data: shallowReactive({}),
      state: reactive({}),
      once: /* @__PURE__ */ new Set(),
      _errors: shallowReactive({})
    }),
    static: {
      data: {}
    },
    runWithContext(fn) {
      if (nuxtApp._scope.active && !getCurrentScope()) {
        return nuxtApp._scope.run(() => callWithNuxt(nuxtApp, fn));
      }
      return callWithNuxt(nuxtApp, fn);
    },
    isHydrating: false,
    deferHydration() {
      if (!nuxtApp.isHydrating) {
        return () => {
        };
      }
      hydratingCount++;
      let called = false;
      return () => {
        if (called) {
          return;
        }
        called = true;
        hydratingCount--;
        if (hydratingCount === 0) {
          nuxtApp.isHydrating = false;
          return nuxtApp.callHook("app:suspense:resolve");
        }
      };
    },
    _asyncDataPromises: {},
    _asyncData: shallowReactive({}),
    _payloadRevivers: {},
    ...options
  };
  {
    nuxtApp.payload.serverRendered = true;
  }
  if (nuxtApp.ssrContext) {
    nuxtApp.payload.path = nuxtApp.ssrContext.url;
    nuxtApp.ssrContext.nuxt = nuxtApp;
    nuxtApp.ssrContext.payload = nuxtApp.payload;
    nuxtApp.ssrContext.config = {
      public: nuxtApp.ssrContext.runtimeConfig.public,
      app: nuxtApp.ssrContext.runtimeConfig.app
    };
  }
  nuxtApp.hooks = createHooks();
  nuxtApp.hook = nuxtApp.hooks.hook;
  {
    const contextCaller = async function(hooks, args) {
      for (const hook of hooks) {
        await nuxtApp.runWithContext(() => hook(...args));
      }
    };
    nuxtApp.hooks.callHook = (name, ...args) => nuxtApp.hooks.callHookWith(contextCaller, name, ...args);
  }
  nuxtApp.callHook = nuxtApp.hooks.callHook;
  nuxtApp.provide = (name, value) => {
    const $name = "$" + name;
    defineGetter(nuxtApp, $name, value);
    defineGetter(nuxtApp.vueApp.config.globalProperties, $name, value);
  };
  defineGetter(nuxtApp.vueApp, "$nuxt", nuxtApp);
  defineGetter(nuxtApp.vueApp.config.globalProperties, "$nuxt", nuxtApp);
  const runtimeConfig = options.ssrContext.runtimeConfig;
  nuxtApp.provide("config", runtimeConfig);
  return nuxtApp;
}
function registerPluginHooks(nuxtApp, plugin2) {
  if (plugin2.hooks) {
    nuxtApp.hooks.addHooks(plugin2.hooks);
  }
}
async function applyPlugin(nuxtApp, plugin2) {
  if (typeof plugin2 === "function") {
    const { provide: provide2 } = await nuxtApp.runWithContext(() => plugin2(nuxtApp)) || {};
    if (provide2 && typeof provide2 === "object") {
      for (const key in provide2) {
        nuxtApp.provide(key, provide2[key]);
      }
    }
  }
}
async function applyPlugins(nuxtApp, plugins2) {
  const resolvedPlugins = /* @__PURE__ */ new Set();
  const unresolvedPlugins = [];
  const parallels = [];
  let error = void 0;
  let promiseDepth = 0;
  async function executePlugin(plugin2) {
    const unresolvedPluginsForThisPlugin = plugin2.dependsOn?.filter((name) => plugins2.some((p) => p._name === name) && !resolvedPlugins.has(name)) ?? [];
    if (unresolvedPluginsForThisPlugin.length > 0) {
      unresolvedPlugins.push([new Set(unresolvedPluginsForThisPlugin), plugin2]);
    } else {
      const promise = applyPlugin(nuxtApp, plugin2).then(async () => {
        if (plugin2._name) {
          resolvedPlugins.add(plugin2._name);
          await Promise.all(unresolvedPlugins.map(async ([dependsOn, unexecutedPlugin]) => {
            if (dependsOn.has(plugin2._name)) {
              dependsOn.delete(plugin2._name);
              if (dependsOn.size === 0) {
                promiseDepth++;
                await executePlugin(unexecutedPlugin);
              }
            }
          }));
        }
      }).catch((e) => {
        if (!plugin2.parallel && !nuxtApp.payload.error) {
          throw e;
        }
        error ||= e;
      });
      if (plugin2.parallel) {
        parallels.push(promise);
      } else {
        await promise;
      }
    }
  }
  for (const plugin2 of plugins2) {
    if (nuxtApp.ssrContext?.islandContext && plugin2.env?.islands === false) {
      continue;
    }
    registerPluginHooks(nuxtApp, plugin2);
  }
  for (const plugin2 of plugins2) {
    if (nuxtApp.ssrContext?.islandContext && plugin2.env?.islands === false) {
      continue;
    }
    await executePlugin(plugin2);
  }
  await Promise.all(parallels);
  if (promiseDepth) {
    for (let i = 0; i < promiseDepth; i++) {
      await Promise.all(parallels);
    }
  }
  if (error) {
    throw nuxtApp.payload.error || error;
  }
}
// @__NO_SIDE_EFFECTS__
function defineNuxtPlugin(plugin2) {
  if (typeof plugin2 === "function") {
    return plugin2;
  }
  const _name = plugin2._name || plugin2.name;
  delete plugin2.name;
  return Object.assign(plugin2.setup || (() => {
  }), plugin2, { [NuxtPluginIndicator]: true, _name });
}
const definePayloadPlugin = defineNuxtPlugin;
function callWithNuxt(nuxt, setup, args) {
  const fn = () => setup();
  const nuxtAppCtx = getNuxtAppCtx(nuxt._id);
  {
    return nuxt.vueApp.runWithContext(() => nuxtAppCtx.callAsync(nuxt, fn));
  }
}
function tryUseNuxtApp(id) {
  let nuxtAppInstance;
  if (hasInjectionContext()) {
    nuxtAppInstance = getCurrentInstance()?.appContext.app.$nuxt;
  }
  nuxtAppInstance ||= getNuxtAppCtx(id).tryUse();
  return nuxtAppInstance || null;
}
function useNuxtApp(id) {
  const nuxtAppInstance = tryUseNuxtApp(id);
  if (!nuxtAppInstance) {
    {
      throw new Error("[nuxt] instance unavailable");
    }
  }
  return nuxtAppInstance;
}
// @__NO_SIDE_EFFECTS__
function useRuntimeConfig(_event) {
  return useNuxtApp().$config;
}
function defineGetter(obj, key, val) {
  Object.defineProperty(obj, key, { get: () => val });
}
const LayoutMetaSymbol = /* @__PURE__ */ Symbol("layout-meta");
const PageRouteSymbol = /* @__PURE__ */ Symbol("route");
function toArray$1(value) {
  return Array.isArray(value) ? value : [value];
}
globalThis._importMeta_.url.replace(/\/app\/.*$/, "/");
const useRouter = () => {
  return useNuxtApp()?.$router;
};
const useRoute = () => {
  if (hasInjectionContext()) {
    return inject(PageRouteSymbol, useNuxtApp()._route);
  }
  return useNuxtApp()._route;
};
// @__NO_SIDE_EFFECTS__
function defineNuxtRouteMiddleware(middleware) {
  return middleware;
}
const isProcessingMiddleware = () => {
  try {
    if (useNuxtApp()._processingMiddleware) {
      return true;
    }
  } catch {
    return false;
  }
  return false;
};
const URL_QUOTE_RE = /"/g;
const navigateTo = (to, options) => {
  to ||= "/";
  const toPath = typeof to === "string" ? to : "path" in to ? resolveRouteObject(to) : useRouter().resolve(to).href;
  const isExternalHost = hasProtocol(toPath, { acceptRelative: true });
  const isExternal = options?.external || isExternalHost;
  if (isExternal) {
    if (!options?.external) {
      throw new Error("Navigating to an external URL is not allowed by default. Use `navigateTo(url, { external: true })`.");
    }
    const { protocol } = new URL(toPath, "http://localhost");
    if (protocol && isScriptProtocol(protocol)) {
      throw new Error(`Cannot navigate to a URL with '${protocol}' protocol.`);
    }
  }
  const inMiddleware = isProcessingMiddleware();
  const router = useRouter();
  const nuxtApp = useNuxtApp();
  {
    if (nuxtApp.ssrContext) {
      const fullPath = typeof to === "string" || isExternal ? toPath : router.resolve(to).fullPath || "/";
      const location2 = isExternal ? toPath : joinURL((/* @__PURE__ */ useRuntimeConfig()).app.baseURL, fullPath);
      const redirect = async function(response) {
        await nuxtApp.callHook("app:redirected");
        const encodedLoc = location2.replace(URL_QUOTE_RE, "%22");
        const encodedHeader = encodeURL(location2, isExternalHost);
        nuxtApp.ssrContext["~renderResponse"] = {
          statusCode: sanitizeStatusCode(options?.redirectCode || 302, 302),
          body: `<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0; url=${encodedLoc}"></head></html>`,
          headers: { location: encodedHeader }
        };
        return response;
      };
      if (!isExternal && inMiddleware) {
        router.afterEach((final) => final.fullPath === fullPath ? redirect(false) : void 0);
        return to;
      }
      return redirect(!inMiddleware ? void 0 : (
        /* abort route navigation */
        false
      ));
    }
  }
  if (isExternal) {
    nuxtApp._scope.stop();
    if (options?.replace) {
      (void 0).replace(toPath);
    } else {
      (void 0).href = toPath;
    }
    if (inMiddleware) {
      if (!nuxtApp.isHydrating) {
        return false;
      }
      return new Promise(() => {
      });
    }
    return Promise.resolve();
  }
  const encodedTo = typeof to === "string" ? encodeRoutePath(to) : to;
  return options?.replace ? router.replace(encodedTo) : router.push(encodedTo);
};
function resolveRouteObject(to) {
  return withQuery(to.path || "", to.query || {}) + (to.hash || "");
}
function encodeURL(location2, isExternalHost = false) {
  const url = new URL(location2, "http://localhost");
  if (!isExternalHost) {
    return url.pathname + url.search + url.hash;
  }
  if (location2.startsWith("//")) {
    return url.toString().replace(url.protocol, "");
  }
  return url.toString();
}
function encodeRoutePath(url) {
  const parsed = parseURL(url);
  return encodePath(decodePath(parsed.pathname)) + parsed.search + parsed.hash;
}
const NUXT_ERROR_SIGNATURE = "__nuxt_error";
const useError = /* @__NO_SIDE_EFFECTS__ */ () => toRef(useNuxtApp().payload, "error");
const showError = (error) => {
  const nuxtError = createError(error);
  try {
    const error2 = /* @__PURE__ */ useError();
    if (false) ;
    error2.value ||= nuxtError;
  } catch {
    throw nuxtError;
  }
  return nuxtError;
};
const isNuxtError = (error) => !!error && typeof error === "object" && NUXT_ERROR_SIGNATURE in error;
const createError = (error) => {
  if (typeof error !== "string" && error.statusText) {
    error.message ??= error.statusText;
  }
  const nuxtError = createError$1(error);
  Object.defineProperty(nuxtError, NUXT_ERROR_SIGNATURE, {
    value: true,
    configurable: false,
    writable: false
  });
  Object.defineProperty(nuxtError, "status", {
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    get: () => nuxtError.statusCode,
    configurable: true
  });
  Object.defineProperty(nuxtError, "statusText", {
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    get: () => nuxtError.statusMessage,
    configurable: true
  });
  return nuxtError;
};
const matcher = (m, p) => {
  return [];
};
const _routeRulesMatcher = (path) => defu({}, ...matcher().map((r) => r.data).reverse());
const routeRulesMatcher$1 = _routeRulesMatcher;
function getRouteRules(arg) {
  const path = typeof arg === "string" ? arg : arg.path;
  try {
    return routeRulesMatcher$1(path);
  } catch (e) {
    console.error("[nuxt] Error matching route rules.", e);
    return {};
  }
}
function definePayloadReducer(name, reduce) {
  {
    useNuxtApp().ssrContext["~payloadReducers"][name] = reduce;
  }
}
const payloadPlugin = definePayloadPlugin(() => {
  definePayloadReducer(
    "skipHydrate",
    // We need to return something truthy to be treated as a match
    (data) => !shouldHydrate(data) && 1
  );
});
const unhead_k2P3m_ZDyjlr2mMYnoDPwavjsDN8hBlk9cFai0bbopU = /* @__PURE__ */ defineNuxtPlugin({
  name: "nuxt:head",
  enforce: "pre",
  setup(nuxtApp) {
    const head = nuxtApp.ssrContext.head;
    nuxtApp.vueApp.use(head);
  }
});
function toArray(value) {
  return Array.isArray(value) ? value : [value];
}
const __nuxt_page_meta$a = { titleKey: "title.about" };
const __nuxt_page_meta$9 = {
  titleKey: "title.admin",
  requiresAdmin: true
};
const __nuxt_page_meta$8 = { titleKey: "title.home" };
const __nuxt_page_meta$7 = { titleKey: "title.login" };
const __nuxt_page_meta$6 = { titleKey: "title.contact" };
const __nuxt_page_meta$5 = { titleKey: "title.notFound" };
const __nuxt_page_meta$4 = {
  layout: "standalone",
  titleKey: "title.sanakenno"
};
const __nuxt_page_meta$3 = {
  titleKey: "title.newRecipe",
  requiresAuth: true
};
const __nuxt_page_meta$2 = {
  titleKey: "title.recipes",
  requiresAuth: true
};
const __nuxt_page_meta$1 = {
  titleKey: "title.editRecipe",
  requiresAuth: true
};
const __nuxt_page_meta = {
  titleKey: "title.recipe",
  requiresAuth: true
};
const _routes = [
  {
    name: "about",
    path: "/about",
    meta: __nuxt_page_meta$a || {},
    component: () => import('./about-B0Ltgr1U.mjs')
  },
  {
    name: "admin",
    path: "/admin",
    meta: __nuxt_page_meta$9 || {},
    component: () => import('./admin-iLSzzwzd.mjs')
  },
  {
    name: "index",
    path: "/",
    meta: __nuxt_page_meta$8 || {},
    component: () => import('./index-B3TpyDW1.mjs')
  },
  {
    name: "login",
    path: "/login",
    meta: __nuxt_page_meta$7 || {},
    component: () => import('./login-CANAQbyH.mjs')
  },
  {
    name: "contact",
    path: "/contact",
    meta: __nuxt_page_meta$6 || {},
    component: () => import('./contact-DXbSgFNz.mjs')
  },
  {
    name: "slug",
    path: "/:slug(.*)*",
    meta: __nuxt_page_meta$5 || {},
    component: () => import('./_...slug_-74uzxZeM.mjs')
  },
  {
    name: "sanakenno",
    path: "/sanakenno",
    meta: __nuxt_page_meta$4 || {},
    component: () => import('./sanakenno-BL0jKzWC.mjs')
  },
  {
    name: "recipes-new",
    path: "/recipes/new",
    meta: __nuxt_page_meta$3 || {},
    component: () => import('./new-BBMQhN-_.mjs')
  },
  {
    name: "recipes",
    path: "/recipes",
    meta: __nuxt_page_meta$2 || {},
    component: () => import('./index-tLlAB6c6.mjs')
  },
  {
    name: "recipes-slug",
    path: "/recipes/:slug()",
    meta: __nuxt_page_meta || {},
    component: () => import('./_slug_-dQIpVxCD.mjs'),
    children: [
      {
        name: "recipes-slug-edit",
        path: "edit",
        meta: __nuxt_page_meta$1 || {},
        component: () => import('./edit-CwCKk62k.mjs')
      }
    ]
  }
];
const _wrapInTransition = (props, children) => {
  return { default: () => children.default?.() };
};
const ROUTE_KEY_PARENTHESES_RE = /(:\w+)\([^)]+\)/g;
const ROUTE_KEY_SYMBOLS_RE = /(:\w+)[?+*]/g;
const ROUTE_KEY_NORMAL_RE = /:\w+/g;
function generateRouteKey(route) {
  const source = route?.meta.key ?? route.path.replace(ROUTE_KEY_PARENTHESES_RE, "$1").replace(ROUTE_KEY_SYMBOLS_RE, "$1").replace(ROUTE_KEY_NORMAL_RE, (r) => route.params[r.slice(1)]?.toString() || "");
  return typeof source === "function" ? source(route) : source;
}
function isChangingPage(to, from) {
  if (to === from || from === START_LOCATION) {
    return false;
  }
  if (generateRouteKey(to) !== generateRouteKey(from)) {
    return true;
  }
  const areComponentsSame = to.matched.every(
    (comp, index) => comp.components && comp.components.default === from.matched[index]?.components?.default
  );
  if (areComponentsSame) {
    return false;
  }
  return true;
}
const routerOptions0 = {
  scrollBehavior(to, from, savedPosition) {
    const nuxtApp = useNuxtApp();
    const hashScrollBehaviour = useRouter().options?.scrollBehaviorType ?? "auto";
    if (to.path.replace(/\/$/, "") === from.path.replace(/\/$/, "")) {
      if (from.hash && !to.hash) {
        return { left: 0, top: 0 };
      }
      if (to.hash) {
        return { el: to.hash, top: _getHashElementScrollMarginTop(to.hash), behavior: hashScrollBehaviour };
      }
      return false;
    }
    const routeAllowsScrollToTop = typeof to.meta.scrollToTop === "function" ? to.meta.scrollToTop(to, from) : to.meta.scrollToTop;
    if (routeAllowsScrollToTop === false) {
      return false;
    }
    const hookToWait = nuxtApp._runningTransition ? "page:transition:finish" : "page:loading:end";
    return new Promise((resolve) => {
      if (from === START_LOCATION) {
        resolve(_calculatePosition(to, from, savedPosition, hashScrollBehaviour));
        return;
      }
      nuxtApp.hooks.hookOnce(hookToWait, () => {
        requestAnimationFrame(() => resolve(_calculatePosition(to, from, savedPosition, hashScrollBehaviour)));
      });
    });
  }
};
function _getHashElementScrollMarginTop(selector) {
  try {
    const elem = (void 0).querySelector(selector);
    if (elem) {
      return (Number.parseFloat(getComputedStyle(elem).scrollMarginTop) || 0) + (Number.parseFloat(getComputedStyle((void 0).documentElement).scrollPaddingTop) || 0);
    }
  } catch {
  }
  return 0;
}
function _calculatePosition(to, from, savedPosition, defaultHashScrollBehaviour) {
  if (savedPosition) {
    return savedPosition;
  }
  const isPageNavigation = isChangingPage(to, from);
  if (to.hash) {
    return {
      el: to.hash,
      top: _getHashElementScrollMarginTop(to.hash),
      behavior: isPageNavigation ? defaultHashScrollBehaviour : "instant"
    };
  }
  return {
    left: 0,
    top: 0
  };
}
const configRouterOptions = {
  hashMode: false,
  scrollBehaviorType: "auto"
};
const routerOptions = {
  ...configRouterOptions,
  ...routerOptions0
};
const validate = /* @__PURE__ */ defineNuxtRouteMiddleware(async (to, from) => {
  let __temp, __restore;
  if (!to.meta?.validate) {
    return;
  }
  const result = ([__temp, __restore] = executeAsync(() => Promise.resolve(to.meta.validate(to))), __temp = await __temp, __restore(), __temp);
  if (result === true) {
    return;
  }
  const error = createError({
    fatal: false,
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    status: result && (result.status || result.statusCode) || 404,
    // eslint-disable-next-line @typescript-eslint/no-deprecated
    statusText: result && (result.statusText || result.statusMessage) || `Page Not Found: ${to.fullPath}`,
    data: {
      path: to.fullPath
    }
  });
  return error;
});
const useAuthStore = defineStore("auth", () => {
  const user = ref(null);
  const isAdmin = computed(() => user.value?.role === "admin");
  const isAuthenticated = computed(() => user.value !== null);
  async function login(email, password) {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Login failed");
    user.value = data;
    return data;
  }
  async function logout() {
    try {
      const res = await fetch("/api/logout", { method: "POST" });
      if (res.ok) user.value = null;
    } catch {
      user.value = null;
    }
  }
  async function checkAuth() {
    try {
      const res = await fetch("/api/me");
      if (res.ok) {
        user.value = await res.json();
      } else {
        user.value = null;
      }
    } catch {
      user.value = null;
    }
  }
  return { user, isAdmin, isAuthenticated, login, logout, checkAuth };
});
defineComponent({
  name: "ServerPlaceholder",
  render() {
    return createElementBlock("div");
  }
});
const clientOnlySymbol = /* @__PURE__ */ Symbol.for("nuxt:client-only");
defineComponent({
  name: "ClientOnly",
  inheritAttrs: false,
  props: ["fallback", "placeholder", "placeholderTag", "fallbackTag"],
  ...false,
  setup(props, { slots, attrs }) {
    const mounted = shallowRef(false);
    const vm = getCurrentInstance();
    if (vm) {
      vm._nuxtClientOnly = true;
    }
    provide(clientOnlySymbol, true);
    return () => {
      if (mounted.value) {
        const vnodes = slots.default?.();
        if (vnodes && vnodes.length === 1) {
          return [cloneVNode(vnodes[0], attrs)];
        }
        return vnodes;
      }
      const slot = slots.fallback || slots.placeholder;
      if (slot) {
        return h(slot);
      }
      const fallbackStr = props.fallback || props.placeholder || "";
      const fallbackTag = props.fallbackTag || props.placeholderTag || "span";
      return createElementBlock(fallbackTag, attrs, fallbackStr);
    };
  }
});
function useRequestEvent(nuxtApp) {
  nuxtApp ||= useNuxtApp();
  return nuxtApp.ssrContext?.event;
}
function prerenderRoutes(path) {
  const paths = toArray$1(path);
  appendHeader(useRequestEvent(), "x-nitro-prerender", paths.map((p) => encodeURIComponent(p)).join(", "));
}
const auth_45global = /* @__PURE__ */ defineNuxtRouteMiddleware(async (to) => {
  let __temp, __restore;
  if (!to.meta.requiresAdmin && !to.meta.requiresAuth) return;
  const authStore = useAuthStore();
  const { isAdmin, isAuthenticated } = storeToRefs(authStore);
  if (!isAuthenticated.value) [__temp, __restore] = executeAsync(() => authStore.checkAuth()), __temp = await __temp, __restore();
  if (to.meta.requiresAdmin && !isAdmin.value) {
    return navigateTo("/login");
  }
  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return navigateTo("/login");
  }
});
const en = {
  "nav.about": "About",
  "nav.contact": "Contact",
  "nav.sanakenno": "Sanakenno",
  "nav.recipes": "Recipes",
  "nav.admin": "Admin",
  "nav.login": "Login",
  "nav.logout": "Logout",
  "nav.toggleMenu": "Toggle menu",
  "theme.switchToLight": "Switch to light mode",
  "theme.switchToDark": "Switch to dark mode",
  "footer.lastUpdated": "Last updated: {date}",
  "home.heading": "Konsta Janhunen",
  "home.subtitle": "Developer & tinkerer",
  "home.aboutMe": "About me",
  "home.getInTouch": "Get in touch",
  "home.metaTitle": "erez.ac — Konsta Janhunen",
  "home.metaDescription": "Konsta Janhunen — Developer & tinkerer. Integration developer, CS student, and technology enthusiast.",
  "about.heading": "About",
  "about.metaTitle": "About — erez.ac",
  "about.metaDescription": "About Konsta Janhunen — Integration developer at Digia, CS student, and technology enthusiast.",
  "about.loadError": "Failed to load content.",
  "about.loadErrorHint": "Please try refreshing the page.",
  "contact.heading": "Contact",
  "contact.metaTitle": "Contact — erez.ac",
  "contact.metaDescription": "Get in touch with Konsta Janhunen — email, GitHub, and LinkedIn.",
  "login.heading": "Login",
  "login.loggedIn": "Logged in",
  "login.signedInAs": "Signed in as",
  "login.email": "Email",
  "login.password": "Password",
  "login.signingIn": "Signing in...",
  "login.signIn": "Sign in",
  "notFound.heading": "Page not found",
  "notFound.backHome": "Back to home",
  "admin.heading": "Admin",
  "admin.tab.sections": "Sections",
  "admin.tab.analytics": "Analytics",
  "admin.tab.recipes": "Recipes",
  "admin.tab.health": "Health",
  "admin.tab.sanakenno": "Sanakenno",
  "admin.tab.kennotyokalu": "Kenno Tool",
  "admin.addSection": "Add Section",
  "admin.title": "Title",
  "admin.slug": "slug",
  "admin.contentHtml": "Content (HTML)",
  "admin.edit": "Edit",
  "admin.delete": "Delete",
  "admin.save": "Save",
  "admin.cancel": "Cancel",
  "admin.noSections": "No sections yet. Add one above.",
  "admin.confirmDelete": "Delete this section?",
  "admin.created": "Section created",
  "admin.updated": "Section updated",
  "admin.deleted": "Section deleted",
  "recipes.heading": "Recipes",
  "recipes.newRecipe": "New Recipe",
  "recipes.searchPlaceholder": "Search recipes or ingredients...",
  "recipes.allCategories": "All categories",
  "recipes.loading": "Loading...",
  "recipes.noResults": "No recipes found.",
  "recipes.loadError": "Failed to load recipes",
  "recipe.edit": "Edit",
  "recipe.delete": "Delete",
  "recipe.ingredients": "Ingredients",
  "recipe.steps": "Steps",
  "recipe.backToRecipes": "← Back to recipes",
  "recipe.confirmDelete": "Delete this recipe?",
  "recipe.notFound": "Recipe not found",
  "recipe.loadError": "Failed to load recipe",
  "recipe.deleteError": "Failed to delete",
  "recipeForm.editHeading": "Edit Recipe",
  "recipeForm.newHeading": "New Recipe",
  "recipeForm.title": "Title",
  "recipeForm.category": "Category",
  "recipeForm.none": "None",
  "recipeForm.ingredients": "Ingredients",
  "recipeForm.amount": "Amount",
  "recipeForm.unit": "Unit",
  "recipeForm.ingredientName": "Ingredient name",
  "recipeForm.addIngredient": "+ Add ingredient",
  "recipeForm.steps": "Steps",
  "recipeForm.stepPlaceholder": "Describe this step...",
  "recipeForm.addStep": "+ Add step",
  "recipeForm.saving": "Saving...",
  "recipeForm.update": "Update Recipe",
  "recipeForm.create": "Create Recipe",
  "recipeForm.cancel": "Cancel",
  "recipeForm.notFound": "Recipe not found",
  "recipeForm.saveError": "Failed to save recipe",
  "title.home": "erez.ac",
  "title.about": "About - erez.ac",
  "title.contact": "Contact - erez.ac",
  "title.login": "Login - erez.ac",
  "title.admin": "Admin - erez.ac",
  "title.recipes": "Recipes - erez.ac",
  "title.newRecipe": "New Recipe - erez.ac",
  "title.recipe": "Recipe - erez.ac",
  "title.editRecipe": "Edit Recipe - erez.ac",
  "title.sanakenno": "Sanakenno - erez.ac",
  "title.notFound": "404 - erez.ac"
};
const fi = {
  "nav.about": "Tietoa",
  "nav.contact": "Yhteystiedot",
  "nav.sanakenno": "Sanakenno",
  "nav.recipes": "Reseptit",
  "nav.admin": "Hallinta",
  "nav.login": "Kirjaudu",
  "nav.logout": "Kirjaudu ulos",
  "nav.toggleMenu": "Vaihda valikko",
  "theme.switchToLight": "Vaihda vaaleaan tilaan",
  "theme.switchToDark": "Vaihda tummaan tilaan",
  "footer.lastUpdated": "Päivitetty: {date}",
  "home.heading": "Konsta Janhunen",
  "home.subtitle": "Kehittäjä & puuhastelija",
  "home.aboutMe": "Tietoa minusta",
  "home.getInTouch": "Ota yhteyttä",
  "home.metaTitle": "erez.ac — Konsta Janhunen",
  "home.metaDescription": "Konsta Janhunen — Kehittäjä & puuhastelija. Integraatiokehittäjä, tietojenkäsittelytieteen opiskelija ja teknologiaintoilija.",
  "about.heading": "Tietoa",
  "about.metaTitle": "Tietoa — erez.ac",
  "about.metaDescription": "Tietoa Konsta Janhusesta — Integraatiokehittäjä Digialla, tietojenkäsittelytieteen opiskelija ja teknologiaintoilija.",
  "about.loadError": "Sisällön lataaminen epäonnistui.",
  "about.loadErrorHint": "Yritä päivittää sivu.",
  "contact.heading": "Yhteystiedot",
  "contact.metaTitle": "Yhteystiedot — erez.ac",
  "contact.metaDescription": "Ota yhteyttä Konsta Janhuseen — sähköposti, GitHub ja LinkedIn.",
  "login.heading": "Kirjaudu",
  "login.loggedIn": "Kirjautunut",
  "login.signedInAs": "Kirjautuneena käyttäjänä",
  "login.email": "Sähköposti",
  "login.password": "Salasana",
  "login.signingIn": "Kirjaudutaan...",
  "login.signIn": "Kirjaudu sisään",
  "notFound.heading": "Sivua ei löytynyt",
  "notFound.backHome": "Takaisin etusivulle",
  "admin.heading": "Hallinta",
  "admin.tab.sections": "Osiot",
  "admin.tab.analytics": "Analytiikka",
  "admin.tab.recipes": "Reseptit",
  "admin.tab.health": "Terveys",
  "admin.tab.sanakenno": "Sanakenno",
  "admin.tab.kennotyokalu": "Kennotyökalu",
  "admin.addSection": "Lisää osio",
  "admin.title": "Otsikko",
  "admin.slug": "polku",
  "admin.contentHtml": "Sisältö (HTML)",
  "admin.edit": "Muokkaa",
  "admin.delete": "Poista",
  "admin.save": "Tallenna",
  "admin.cancel": "Peruuta",
  "admin.noSections": "Ei osioita. Lisää uusi yllä.",
  "admin.confirmDelete": "Poistetaanko tämä osio?",
  "admin.created": "Osio luotu",
  "admin.updated": "Osio päivitetty",
  "admin.deleted": "Osio poistettu",
  "recipes.heading": "Reseptit",
  "recipes.newRecipe": "Uusi resepti",
  "recipes.searchPlaceholder": "Hae reseptejä tai ainesosia...",
  "recipes.allCategories": "Kaikki kategoriat",
  "recipes.loading": "Ladataan...",
  "recipes.noResults": "Reseptejä ei löytynyt.",
  "recipes.loadError": "Reseptien lataaminen epäonnistui",
  "recipe.edit": "Muokkaa",
  "recipe.delete": "Poista",
  "recipe.ingredients": "Ainekset",
  "recipe.steps": "Vaiheet",
  "recipe.backToRecipes": "← Takaisin resepteihin",
  "recipe.confirmDelete": "Poistetaanko tämä resepti?",
  "recipe.notFound": "Reseptiä ei löytynyt",
  "recipe.loadError": "Reseptin lataaminen epäonnistui",
  "recipe.deleteError": "Poistaminen epäonnistui",
  "recipeForm.editHeading": "Muokkaa reseptiä",
  "recipeForm.newHeading": "Uusi resepti",
  "recipeForm.title": "Otsikko",
  "recipeForm.category": "Kategoria",
  "recipeForm.none": "Ei mitään",
  "recipeForm.ingredients": "Ainekset",
  "recipeForm.amount": "Määrä",
  "recipeForm.unit": "Yksikkö",
  "recipeForm.ingredientName": "Ainesosan nimi",
  "recipeForm.addIngredient": "+ Lisää ainesosa",
  "recipeForm.steps": "Vaiheet",
  "recipeForm.stepPlaceholder": "Kuvaile tämä vaihe...",
  "recipeForm.addStep": "+ Lisää vaihe",
  "recipeForm.saving": "Tallennetaan...",
  "recipeForm.update": "Päivitä resepti",
  "recipeForm.create": "Luo resepti",
  "recipeForm.cancel": "Peruuta",
  "recipeForm.notFound": "Reseptiä ei löytynyt",
  "recipeForm.saveError": "Reseptin tallentaminen epäonnistui",
  "title.home": "erez.ac",
  "title.about": "Tietoa - erez.ac",
  "title.contact": "Yhteystiedot - erez.ac",
  "title.login": "Kirjaudu - erez.ac",
  "title.admin": "Hallinta - erez.ac",
  "title.recipes": "Reseptit - erez.ac",
  "title.newRecipe": "Uusi resepti - erez.ac",
  "title.recipe": "Resepti - erez.ac",
  "title.editRecipe": "Muokkaa reseptiä - erez.ac",
  "title.sanakenno": "Sanakenno - erez.ac",
  "title.notFound": "404 - erez.ac"
};
const messages = { en, fi };
const supportedLocales = ["en", "fi"];
function detectLocale() {
  return "en";
}
const useI18nStore = defineStore("i18n", () => {
  const locale = ref(detectLocale());
  function t(key, params) {
    let str = messages[locale.value]?.[key] || messages.en[key] || key;
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        str = str.replace(`{${k}}`, v);
      }
    }
    return str;
  }
  function setLocale(lang) {
    if (!supportedLocales.includes(lang)) return;
    locale.value = lang;
  }
  return { locale, t, setLocale };
});
const pageview_45global = /* @__PURE__ */ defineNuxtRouteMiddleware((to, from) => {
  return;
});
const manifest_45route_45rule = /* @__PURE__ */ defineNuxtRouteMiddleware((to) => {
  {
    return;
  }
});
const globalMiddleware = [
  validate,
  auth_45global,
  pageview_45global,
  manifest_45route_45rule
];
const namedMiddleware = {};
const plugin$1 = /* @__PURE__ */ defineNuxtPlugin({
  name: "nuxt:router",
  enforce: "pre",
  async setup(nuxtApp) {
    let __temp, __restore;
    let routerBase = (/* @__PURE__ */ useRuntimeConfig()).app.baseURL;
    const history = routerOptions.history?.(routerBase) ?? createMemoryHistory(routerBase);
    const routes2 = routerOptions.routes ? ([__temp, __restore] = executeAsync(() => routerOptions.routes(_routes)), __temp = await __temp, __restore(), __temp) ?? _routes : _routes;
    let startPosition;
    const router = createRouter({
      ...routerOptions,
      scrollBehavior: (to, from, savedPosition) => {
        if (from === START_LOCATION) {
          startPosition = savedPosition;
          return;
        }
        if (routerOptions.scrollBehavior) {
          router.options.scrollBehavior = routerOptions.scrollBehavior;
          if ("scrollRestoration" in (void 0).history) {
            const unsub = router.beforeEach(() => {
              unsub();
              (void 0).history.scrollRestoration = "manual";
            });
          }
          return routerOptions.scrollBehavior(to, START_LOCATION, startPosition || savedPosition);
        }
      },
      history,
      routes: routes2
    });
    nuxtApp.vueApp.use(router);
    const previousRoute = shallowRef(router.currentRoute.value);
    router.afterEach((_to, from) => {
      previousRoute.value = from;
    });
    Object.defineProperty(nuxtApp.vueApp.config.globalProperties, "previousRoute", {
      get: () => previousRoute.value
    });
    const initialURL = nuxtApp.ssrContext.url;
    const _route = shallowRef(router.currentRoute.value);
    const syncCurrentRoute = () => {
      _route.value = router.currentRoute.value;
    };
    router.afterEach((to, from) => {
      if (to.matched.at(-1)?.components?.default === from.matched.at(-1)?.components?.default) {
        syncCurrentRoute();
      }
    });
    const route = { sync: syncCurrentRoute };
    for (const key in _route.value) {
      Object.defineProperty(route, key, {
        get: () => _route.value[key],
        enumerable: true
      });
    }
    nuxtApp._route = shallowReactive(route);
    nuxtApp._middleware ||= {
      global: [],
      named: {}
    };
    const error = /* @__PURE__ */ useError();
    if (!nuxtApp.ssrContext?.islandContext) {
      router.afterEach(async (to, _from, failure) => {
        delete nuxtApp._processingMiddleware;
        if (failure) {
          await nuxtApp.callHook("page:loading:end");
        }
        if (failure?.type === 4) {
          return;
        }
        if (to.redirectedFrom && to.fullPath !== initialURL) {
          await nuxtApp.runWithContext(() => navigateTo(to.fullPath || "/"));
        }
      });
    }
    try {
      if (true) {
        ;
        [__temp, __restore] = executeAsync(() => router.push(initialURL)), await __temp, __restore();
        ;
      }
      ;
      [__temp, __restore] = executeAsync(() => router.isReady()), await __temp, __restore();
      ;
    } catch (error2) {
      [__temp, __restore] = executeAsync(() => nuxtApp.runWithContext(() => showError(error2))), await __temp, __restore();
    }
    const resolvedInitialRoute = router.currentRoute.value;
    syncCurrentRoute();
    if (nuxtApp.ssrContext?.islandContext) {
      return { provide: { router } };
    }
    const initialLayout = nuxtApp.payload.state._layout;
    router.beforeEach(async (to, from) => {
      await nuxtApp.callHook("page:loading:start");
      to.meta = reactive(to.meta);
      if (nuxtApp.isHydrating && initialLayout && !isReadonly(to.meta.layout)) {
        to.meta.layout = initialLayout;
      }
      nuxtApp._processingMiddleware = true;
      if (!nuxtApp.ssrContext?.islandContext) {
        const middlewareEntries = /* @__PURE__ */ new Set([...globalMiddleware, ...nuxtApp._middleware.global]);
        for (const component of to.matched) {
          const componentMiddleware = component.meta.middleware;
          if (!componentMiddleware) {
            continue;
          }
          for (const entry2 of toArray(componentMiddleware)) {
            middlewareEntries.add(entry2);
          }
        }
        const routeRules = getRouteRules({ path: to.path });
        if (routeRules.appMiddleware) {
          for (const key in routeRules.appMiddleware) {
            if (routeRules.appMiddleware[key]) {
              middlewareEntries.add(key);
            } else {
              middlewareEntries.delete(key);
            }
          }
        }
        for (const entry2 of middlewareEntries) {
          const middleware = typeof entry2 === "string" ? nuxtApp._middleware.named[entry2] || await namedMiddleware[entry2]?.().then((r) => r.default || r) : entry2;
          if (!middleware) {
            throw new Error(`Unknown route middleware: '${entry2}'.`);
          }
          try {
            if (false) ;
            const result = await nuxtApp.runWithContext(() => middleware(to, from));
            if (true) {
              if (result === false || result instanceof Error) {
                const error2 = result || createError({
                  status: 404,
                  statusText: `Page Not Found: ${initialURL}`
                });
                await nuxtApp.runWithContext(() => showError(error2));
                return false;
              }
            }
            if (result === true) {
              continue;
            }
            if (result === false) {
              return result;
            }
            if (result) {
              if (isNuxtError(result) && result.fatal) {
                await nuxtApp.runWithContext(() => showError(result));
              }
              return result;
            }
          } catch (err) {
            const error2 = createError(err);
            if (error2.fatal) {
              await nuxtApp.runWithContext(() => showError(error2));
            }
            return error2;
          }
        }
      }
    });
    router.onError(async () => {
      delete nuxtApp._processingMiddleware;
      await nuxtApp.callHook("page:loading:end");
    });
    router.afterEach((to) => {
      if (to.matched.length === 0 && !error.value) {
        return nuxtApp.runWithContext(() => showError(createError({
          status: 404,
          fatal: false,
          statusText: `Page not found: ${to.fullPath}`,
          data: {
            path: to.fullPath
          }
        })));
      }
    });
    nuxtApp.hooks.hookOnce("app:created", async () => {
      try {
        if ("name" in resolvedInitialRoute) {
          resolvedInitialRoute.name = void 0;
        }
        await router.replace({
          ...resolvedInitialRoute,
          force: true
        });
        router.options.scrollBehavior = routerOptions.scrollBehavior;
      } catch (error2) {
        await nuxtApp.runWithContext(() => showError(error2));
      }
    });
    return { provide: { router } };
  }
});
const reducers = [
  ["NuxtError", (data) => isNuxtError(data) && data.toJSON()],
  ["EmptyShallowRef", (data) => isRef(data) && isShallow(data) && !data.value && (typeof data.value === "bigint" ? "0n" : JSON.stringify(data.value) || "_")],
  ["EmptyRef", (data) => isRef(data) && !data.value && (typeof data.value === "bigint" ? "0n" : JSON.stringify(data.value) || "_")],
  ["ShallowRef", (data) => isRef(data) && isShallow(data) && data.value],
  ["ShallowReactive", (data) => isReactive(data) && isShallow(data) && toRaw(data)],
  ["Ref", (data) => isRef(data) && data.value],
  ["Reactive", (data) => isReactive(data) && toRaw(data)]
];
const revive_payload_server_MVtmlZaQpj6ApFmshWfUWl5PehCebzaBf2NuRMiIbms = /* @__PURE__ */ defineNuxtPlugin({
  name: "nuxt:revive-payload:server",
  setup() {
    for (const [reducer, fn] of reducers) {
      definePayloadReducer(reducer, fn);
    }
  }
});
const plugin = /* @__PURE__ */ defineNuxtPlugin({
  name: "pinia",
  setup(nuxtApp) {
    const pinia = createPinia();
    nuxtApp.vueApp.use(pinia);
    setActivePinia(pinia);
    if (nuxtApp.payload && nuxtApp.payload.pinia) {
      pinia.state.value = nuxtApp.payload.pinia;
    }
    return {
      provide: {
        pinia
      }
    };
  },
  hooks: {
    "app:rendered"() {
      const nuxtApp = useNuxtApp();
      nuxtApp.payload.pinia = toRaw(nuxtApp.$pinia).state.value;
      setActivePinia(void 0);
    }
  }
});
const components_plugin_z4hgvsiddfKkfXTP6M8M4zG5Cb7sGnDhcryKVM45Di4 = /* @__PURE__ */ defineNuxtPlugin({
  name: "nuxt:global-components"
});
let routes;
const prerender_server_sqIxOBipVr4FbVMA9kqWL0wT8FPop6sKAXLVfifsJzk = /* @__PURE__ */ defineNuxtPlugin(async () => {
  let __temp, __restore;
  if (routes && !routes.length) {
    return;
  }
  routes ||= Array.from(processRoutes(([__temp, __restore] = executeAsync(() => routerOptions.routes?.(_routes)), __temp = await __temp, __restore(), __temp) ?? _routes));
  const batch = routes.splice(0, 10);
  prerenderRoutes(batch);
});
const OPTIONAL_PARAM_RE = /^\/?:.*(?:\?|\(\.\*\)\*)$/;
function shouldPrerender(path) {
  return crawlLinks;
}
function processRoutes(routes2, currentPath = "/", routesToPrerender = /* @__PURE__ */ new Set()) {
  for (const route of routes2) {
    if (OPTIONAL_PARAM_RE.test(route.path) && !route.children?.length && shouldPrerender()) {
      routesToPrerender.add(currentPath);
    }
    if (route.path.includes(":")) {
      continue;
    }
    const fullPath = joinURL(currentPath, route.path);
    {
      routesToPrerender.add(fullPath);
    }
    if (route.children) {
      processRoutes(route.children, fullPath, routesToPrerender);
    }
  }
  return routesToPrerender;
}
const plugins = [
  payloadPlugin,
  unhead_k2P3m_ZDyjlr2mMYnoDPwavjsDN8hBlk9cFai0bbopU,
  plugin$1,
  revive_payload_server_MVtmlZaQpj6ApFmshWfUWl5PehCebzaBf2NuRMiIbms,
  plugin,
  components_plugin_z4hgvsiddfKkfXTP6M8M4zG5Cb7sGnDhcryKVM45Di4,
  prerender_server_sqIxOBipVr4FbVMA9kqWL0wT8FPop6sKAXLVfifsJzk
];
const layouts = {
  default: defineAsyncComponent(() => import('./default-C_uaB0rx.mjs').then((m) => m.default || m)),
  standalone: defineAsyncComponent(() => import('./standalone-BQ_TM55x.mjs').then((m) => m.default || m))
};
const routeRulesMatcher = _routeRulesMatcher;
const LayoutLoader = defineComponent({
  name: "LayoutLoader",
  inheritAttrs: false,
  props: {
    name: String,
    layoutProps: Object
  },
  setup(props, context) {
    return () => h(layouts[props.name], props.layoutProps, context.slots);
  }
});
const nuxtLayoutProps = {
  name: {
    type: [String, Boolean, Object],
    default: null
  },
  fallback: {
    type: [String, Object],
    default: null
  }
};
const __nuxt_component_0 = defineComponent({
  name: "NuxtLayout",
  inheritAttrs: false,
  props: nuxtLayoutProps,
  setup(props, context) {
    const nuxtApp = useNuxtApp();
    const injectedRoute = inject(PageRouteSymbol);
    const shouldUseEagerRoute = !injectedRoute || injectedRoute === useRoute();
    const route = shouldUseEagerRoute ? useRoute$1() : injectedRoute;
    const layout = computed(() => {
      let layout2 = unref(props.name) ?? route?.meta.layout ?? routeRulesMatcher(route?.path).appLayout ?? "default";
      if (layout2 && !(layout2 in layouts)) {
        if (props.fallback) {
          layout2 = unref(props.fallback);
        }
      }
      return layout2;
    });
    const layoutRef = shallowRef();
    context.expose({ layoutRef });
    const done = nuxtApp.deferHydration();
    let lastLayout;
    return () => {
      const hasLayout = layout.value && layout.value in layouts;
      const transitionProps = route?.meta.layoutTransition ?? appLayoutTransition;
      const previouslyRenderedLayout = lastLayout;
      lastLayout = layout.value;
      return _wrapInTransition(hasLayout && transitionProps, {
        default: () => h(Suspense, { suspensible: true, onResolve: () => {
          nextTick(done);
        } }, {
          default: () => h(
            LayoutProvider,
            {
              layoutProps: mergeProps(context.attrs, route.meta.layoutProps ?? {}, { ref: layoutRef }),
              key: layout.value || void 0,
              name: layout.value,
              shouldProvide: !props.name,
              isRenderingNewLayout: (name) => {
                return name !== previouslyRenderedLayout && name === layout.value;
              },
              hasTransition: !!transitionProps
            },
            context.slots
          )
        })
      }).default();
    };
  }
});
const LayoutProvider = defineComponent({
  name: "NuxtLayoutProvider",
  inheritAttrs: false,
  props: {
    name: {
      type: [String, Boolean]
    },
    layoutProps: {
      type: Object
    },
    hasTransition: {
      type: Boolean
    },
    shouldProvide: {
      type: Boolean
    },
    isRenderingNewLayout: {
      type: Function,
      required: true
    }
  },
  setup(props, context) {
    const name = props.name;
    if (props.shouldProvide) {
      provide(LayoutMetaSymbol, {
        // When name=false, always return true so NuxtPage doesn't skip rendering
        isCurrent: (route) => name === false || name === (route.meta.layout ?? routeRulesMatcher(route.path).appLayout ?? "default")
      });
    }
    const injectedRoute = inject(PageRouteSymbol);
    const isNotWithinNuxtPage = injectedRoute && injectedRoute === useRoute();
    if (isNotWithinNuxtPage) {
      const vueRouterRoute = useRoute$1();
      const reactiveChildRoute = {};
      for (const _key in vueRouterRoute) {
        const key = _key;
        Object.defineProperty(reactiveChildRoute, key, {
          enumerable: true,
          get: () => {
            return props.isRenderingNewLayout(props.name) ? vueRouterRoute[key] : injectedRoute[key];
          }
        });
      }
      provide(PageRouteSymbol, shallowReactive(reactiveChildRoute));
    }
    return () => {
      if (!name || typeof name === "string" && !(name in layouts)) {
        return context.slots.default?.();
      }
      return h(
        LayoutLoader,
        { key: name, layoutProps: props.layoutProps, name },
        context.slots
      );
    };
  }
});
const defineRouteProvider = (name = "RouteProvider") => defineComponent({
  name,
  props: {
    route: {
      type: Object,
      required: true
    },
    vnode: Object,
    vnodeRef: Object,
    renderKey: String,
    trackRootNodes: Boolean
  },
  setup(props) {
    const previousKey = props.renderKey;
    const previousRoute = props.route;
    const route = {};
    for (const key in props.route) {
      Object.defineProperty(route, key, {
        get: () => previousKey === props.renderKey ? props.route[key] : previousRoute[key],
        enumerable: true
      });
    }
    provide(PageRouteSymbol, shallowReactive(route));
    return () => {
      if (!props.vnode) {
        return props.vnode;
      }
      return h(props.vnode, { ref: props.vnodeRef });
    };
  }
});
const RouteProvider = defineRouteProvider();
const __nuxt_component_1 = defineComponent({
  name: "NuxtPage",
  inheritAttrs: false,
  props: {
    name: {
      type: String
    },
    transition: {
      type: [Boolean, Object],
      default: void 0
    },
    keepalive: {
      type: [Boolean, Object],
      default: void 0
    },
    route: {
      type: Object
    },
    pageKey: {
      type: [Function, String],
      default: null
    }
  },
  setup(props, { attrs, slots, expose }) {
    const nuxtApp = useNuxtApp();
    const pageRef = ref();
    inject(PageRouteSymbol, null);
    expose({ pageRef });
    inject(LayoutMetaSymbol, null);
    nuxtApp.deferHydration();
    return () => {
      return h(RouterView, { name: props.name, route: props.route, ...attrs }, {
        default: (routeProps) => {
          return h(Suspense, { suspensible: true }, {
            default() {
              return h(RouteProvider, {
                vnode: slots.default ? normalizeSlot(slots.default, routeProps) : routeProps.Component,
                route: routeProps.route,
                vnodeRef: pageRef
              });
            }
          });
        }
      });
    };
  }
});
function normalizeSlot(slot, data) {
  const slotContent = slot(data);
  return slotContent.length === 1 ? h(slotContent[0]) : h(Fragment, void 0, slotContent);
}
const useDarkModeStore = defineStore("darkMode", () => {
  const isDark = ref(false);
  function init() {
    const stored = localStorage.getItem("theme");
    if (stored) {
      isDark.value = stored === "dark";
    } else {
      isDark.value = (void 0).matchMedia("(prefers-color-scheme: dark)").matches;
    }
    applyClass();
  }
  function applyClass() {
    (void 0).documentElement.classList.toggle("dark", isDark.value);
  }
  function toggleDark() {
    isDark.value = !isDark.value;
  }
  watch(isDark, (val) => {
    localStorage.setItem("theme", val ? "dark" : "light");
    applyClass();
  }, { flush: "sync" });
  return { isDark, toggleDark, init };
});
const _sfc_main$2 = {
  __name: "app",
  __ssrInlineRender: true,
  setup(__props) {
    useDarkModeStore();
    return (_ctx, _push, _parent, _attrs) => {
      const _component_NuxtLayout = __nuxt_component_0;
      const _component_NuxtPage = __nuxt_component_1;
      _push(ssrRenderComponent(_component_NuxtLayout, _attrs, {
        default: withCtx((_, _push2, _parent2, _scopeId) => {
          if (_push2) {
            _push2(ssrRenderComponent(_component_NuxtPage, null, null, _parent2, _scopeId));
          } else {
            return [
              createVNode(_component_NuxtPage)
            ];
          }
        }),
        _: 1
      }, _parent));
    };
  }
};
const _sfc_setup$2 = _sfc_main$2.setup;
_sfc_main$2.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("app.vue");
  return _sfc_setup$2 ? _sfc_setup$2(props, ctx) : void 0;
};
const _sfc_main$1 = {
  __name: "nuxt-error-page",
  __ssrInlineRender: true,
  props: {
    error: Object
  },
  setup(__props) {
    const props = __props;
    const _error = props.error;
    const status = Number(_error.statusCode || 500);
    const is404 = status === 404;
    const statusText = _error.statusMessage ?? (is404 ? "Page Not Found" : "Internal Server Error");
    const description = _error.message || _error.toString();
    const stack = void 0;
    const _Error404 = defineAsyncComponent(() => import('./error-404-iLR9SE0Z.mjs'));
    const _Error = defineAsyncComponent(() => import('./error-500-BhyBcswN.mjs'));
    const ErrorTemplate = is404 ? _Error404 : _Error;
    return (_ctx, _push, _parent, _attrs) => {
      _push(ssrRenderComponent(unref(ErrorTemplate), mergeProps({ status: unref(status), statusText: unref(statusText), statusCode: unref(status), statusMessage: unref(statusText), description: unref(description), stack: unref(stack) }, _attrs), null, _parent));
    };
  }
};
const _sfc_setup$1 = _sfc_main$1.setup;
_sfc_main$1.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("node_modules/nuxt/dist/app/components/nuxt-error-page.vue");
  return _sfc_setup$1 ? _sfc_setup$1(props, ctx) : void 0;
};
const _sfc_main = {
  __name: "nuxt-root",
  __ssrInlineRender: true,
  setup(__props) {
    const IslandRenderer = () => null;
    const nuxtApp = useNuxtApp();
    nuxtApp.deferHydration();
    nuxtApp.ssrContext.url;
    const SingleRenderer = false;
    provide(PageRouteSymbol, useRoute());
    nuxtApp.hooks.callHookWith((hooks) => hooks.map((hook) => hook()), "vue:setup");
    const error = /* @__PURE__ */ useError();
    const abortRender = error.value && !nuxtApp.ssrContext.error;
    onErrorCaptured((err, target, info) => {
      nuxtApp.hooks.callHook("vue:error", err, target, info).catch((hookError) => console.error("[nuxt] Error in `vue:error` hook", hookError));
      {
        const p = nuxtApp.runWithContext(() => showError(err));
        onServerPrefetch(() => p);
        return false;
      }
    });
    const islandContext = nuxtApp.ssrContext.islandContext;
    return (_ctx, _push, _parent, _attrs) => {
      ssrRenderSuspense(_push, {
        default: () => {
          if (unref(abortRender)) {
            _push(`<div></div>`);
          } else if (unref(error)) {
            _push(ssrRenderComponent(unref(_sfc_main$1), { error: unref(error) }, null, _parent));
          } else if (unref(islandContext)) {
            _push(ssrRenderComponent(unref(IslandRenderer), { context: unref(islandContext) }, null, _parent));
          } else if (unref(SingleRenderer)) {
            ssrRenderVNode(_push, createVNode(resolveDynamicComponent(unref(SingleRenderer)), null, null), _parent);
          } else {
            _push(ssrRenderComponent(unref(_sfc_main$2), null, null, _parent));
          }
        },
        _: 1
      });
    };
  }
};
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("node_modules/nuxt/dist/app/components/nuxt-root.vue");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
let entry;
{
  entry = async function createNuxtAppServer(ssrContext) {
    const vueApp = createApp(_sfc_main);
    const nuxt = createNuxtApp({ vueApp, ssrContext });
    try {
      await applyPlugins(nuxt, plugins);
      await nuxt.hooks.callHook("app:created", vueApp);
    } catch (error) {
      await nuxt.hooks.callHook("app:error", error);
      nuxt.payload.error ||= createError(error);
    }
    if (ssrContext && (ssrContext["~renderResponse"] || ssrContext._renderResponse)) {
      throw new Error("skipping render");
    }
    return vueApp;
  };
}
const entry_default = ((ssrContext) => entry(ssrContext));

export { useRouter as a, useAuthStore as b, useDarkModeStore as c, useRoute as d, entry_default as default, encodeRoutePath as e, useNuxtApp as f, useRuntimeConfig as g, nuxtLinkDefaults as h, navigateTo as n, resolveRouteObject as r, tryUseNuxtApp as t, useI18nStore as u };
//# sourceMappingURL=server.mjs.map
