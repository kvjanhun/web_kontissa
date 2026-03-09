
import type { DefineComponent, SlotsType } from 'vue'
type IslandComponent<T> = DefineComponent<{}, {refresh: () => Promise<void>}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, SlotsType<{ fallback: { error: unknown } }>> & T

type HydrationStrategies = {
  hydrateOnVisible?: IntersectionObserverInit | true
  hydrateOnIdle?: number | true
  hydrateOnInteraction?: keyof HTMLElementEventMap | Array<keyof HTMLElementEventMap> | true
  hydrateOnMediaQuery?: string
  hydrateAfter?: number
  hydrateWhen?: boolean
  hydrateNever?: true
}
type LazyComponent<T> = DefineComponent<HydrationStrategies, {}, {}, {}, {}, {}, {}, { hydrated: () => void }> & T

interface _GlobalComponents {
  AppFooter: typeof import("../../components/AppFooter.vue")['default']
  AppHeader: typeof import("../../components/AppHeader.vue")['default']
  LangToggle: typeof import("../../components/LangToggle.vue")['default']
  SanakennoRulesModal: typeof import("../../components/SanakennoRulesModal.vue")['default']
  SectionBlock: typeof import("../../components/SectionBlock.vue")['default']
  TerminalWindow: typeof import("../../components/TerminalWindow.vue")['default']
  ThemeToggle: typeof import("../../components/ThemeToggle.vue")['default']
  AdminBlockedWords: typeof import("../../components/admin/AdminBlockedWords.vue")['default']
  AdminHealth: typeof import("../../components/admin/AdminHealth.vue")['default']
  AdminKennoPuzzleTool: typeof import("../../components/admin/AdminKennoPuzzleTool.vue")['default']
  AdminKennoStats: typeof import("../../components/admin/AdminKennoStats.vue")['default']
  AdminPageViews: typeof import("../../components/admin/AdminPageViews.vue")['default']
  AdminRecipes: typeof import("../../components/admin/AdminRecipes.vue")['default']
  AdminSections: typeof import("../../components/admin/AdminSections.vue")['default']
  AdminKennoVariationsGrid: typeof import("../../components/admin/KennoVariationsGrid.vue")['default']
  AdminKennoWordList: typeof import("../../components/admin/KennoWordList.vue")['default']
  WeatherIcons: typeof import("../../components/weatherIcons")['default']
  NuxtWelcome: typeof import("../../node_modules/nuxt/dist/app/components/welcome.vue")['default']
  NuxtLayout: typeof import("../../node_modules/nuxt/dist/app/components/nuxt-layout")['default']
  NuxtErrorBoundary: typeof import("../../node_modules/nuxt/dist/app/components/nuxt-error-boundary.vue")['default']
  ClientOnly: typeof import("../../node_modules/nuxt/dist/app/components/client-only")['default']
  DevOnly: typeof import("../../node_modules/nuxt/dist/app/components/dev-only")['default']
  ServerPlaceholder: typeof import("../../node_modules/nuxt/dist/app/components/server-placeholder")['default']
  NuxtLink: typeof import("../../node_modules/nuxt/dist/app/components/nuxt-link")['default']
  NuxtLoadingIndicator: typeof import("../../node_modules/nuxt/dist/app/components/nuxt-loading-indicator")['default']
  NuxtTime: typeof import("../../node_modules/nuxt/dist/app/components/nuxt-time.vue")['default']
  NuxtRouteAnnouncer: typeof import("../../node_modules/nuxt/dist/app/components/nuxt-route-announcer")['default']
  NuxtImg: typeof import("../../node_modules/nuxt/dist/app/components/nuxt-stubs")['NuxtImg']
  NuxtPicture: typeof import("../../node_modules/nuxt/dist/app/components/nuxt-stubs")['NuxtPicture']
  NuxtPage: typeof import("../../node_modules/nuxt/dist/pages/runtime/page")['default']
  NoScript: typeof import("../../node_modules/nuxt/dist/head/runtime/components")['NoScript']
  Link: typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Link']
  Base: typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Base']
  Title: typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Title']
  Meta: typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Meta']
  Style: typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Style']
  Head: typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Head']
  Html: typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Html']
  Body: typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Body']
  NuxtIsland: typeof import("../../node_modules/nuxt/dist/app/components/nuxt-island")['default']
  LazyAppFooter: LazyComponent<typeof import("../../components/AppFooter.vue")['default']>
  LazyAppHeader: LazyComponent<typeof import("../../components/AppHeader.vue")['default']>
  LazyLangToggle: LazyComponent<typeof import("../../components/LangToggle.vue")['default']>
  LazySanakennoRulesModal: LazyComponent<typeof import("../../components/SanakennoRulesModal.vue")['default']>
  LazySectionBlock: LazyComponent<typeof import("../../components/SectionBlock.vue")['default']>
  LazyTerminalWindow: LazyComponent<typeof import("../../components/TerminalWindow.vue")['default']>
  LazyThemeToggle: LazyComponent<typeof import("../../components/ThemeToggle.vue")['default']>
  LazyAdminBlockedWords: LazyComponent<typeof import("../../components/admin/AdminBlockedWords.vue")['default']>
  LazyAdminHealth: LazyComponent<typeof import("../../components/admin/AdminHealth.vue")['default']>
  LazyAdminKennoPuzzleTool: LazyComponent<typeof import("../../components/admin/AdminKennoPuzzleTool.vue")['default']>
  LazyAdminKennoStats: LazyComponent<typeof import("../../components/admin/AdminKennoStats.vue")['default']>
  LazyAdminPageViews: LazyComponent<typeof import("../../components/admin/AdminPageViews.vue")['default']>
  LazyAdminRecipes: LazyComponent<typeof import("../../components/admin/AdminRecipes.vue")['default']>
  LazyAdminSections: LazyComponent<typeof import("../../components/admin/AdminSections.vue")['default']>
  LazyAdminKennoVariationsGrid: LazyComponent<typeof import("../../components/admin/KennoVariationsGrid.vue")['default']>
  LazyAdminKennoWordList: LazyComponent<typeof import("../../components/admin/KennoWordList.vue")['default']>
  LazyWeatherIcons: LazyComponent<typeof import("../../components/weatherIcons")['default']>
  LazyNuxtWelcome: LazyComponent<typeof import("../../node_modules/nuxt/dist/app/components/welcome.vue")['default']>
  LazyNuxtLayout: LazyComponent<typeof import("../../node_modules/nuxt/dist/app/components/nuxt-layout")['default']>
  LazyNuxtErrorBoundary: LazyComponent<typeof import("../../node_modules/nuxt/dist/app/components/nuxt-error-boundary.vue")['default']>
  LazyClientOnly: LazyComponent<typeof import("../../node_modules/nuxt/dist/app/components/client-only")['default']>
  LazyDevOnly: LazyComponent<typeof import("../../node_modules/nuxt/dist/app/components/dev-only")['default']>
  LazyServerPlaceholder: LazyComponent<typeof import("../../node_modules/nuxt/dist/app/components/server-placeholder")['default']>
  LazyNuxtLink: LazyComponent<typeof import("../../node_modules/nuxt/dist/app/components/nuxt-link")['default']>
  LazyNuxtLoadingIndicator: LazyComponent<typeof import("../../node_modules/nuxt/dist/app/components/nuxt-loading-indicator")['default']>
  LazyNuxtTime: LazyComponent<typeof import("../../node_modules/nuxt/dist/app/components/nuxt-time.vue")['default']>
  LazyNuxtRouteAnnouncer: LazyComponent<typeof import("../../node_modules/nuxt/dist/app/components/nuxt-route-announcer")['default']>
  LazyNuxtImg: LazyComponent<typeof import("../../node_modules/nuxt/dist/app/components/nuxt-stubs")['NuxtImg']>
  LazyNuxtPicture: LazyComponent<typeof import("../../node_modules/nuxt/dist/app/components/nuxt-stubs")['NuxtPicture']>
  LazyNuxtPage: LazyComponent<typeof import("../../node_modules/nuxt/dist/pages/runtime/page")['default']>
  LazyNoScript: LazyComponent<typeof import("../../node_modules/nuxt/dist/head/runtime/components")['NoScript']>
  LazyLink: LazyComponent<typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Link']>
  LazyBase: LazyComponent<typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Base']>
  LazyTitle: LazyComponent<typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Title']>
  LazyMeta: LazyComponent<typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Meta']>
  LazyStyle: LazyComponent<typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Style']>
  LazyHead: LazyComponent<typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Head']>
  LazyHtml: LazyComponent<typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Html']>
  LazyBody: LazyComponent<typeof import("../../node_modules/nuxt/dist/head/runtime/components")['Body']>
  LazyNuxtIsland: LazyComponent<typeof import("../../node_modules/nuxt/dist/app/components/nuxt-island")['default']>
}

declare module 'vue' {
  export interface GlobalComponents extends _GlobalComponents { }
}

export {}
