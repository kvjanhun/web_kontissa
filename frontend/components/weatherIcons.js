// Inline SVG weather icons (16x16, fill="currentColor")
// Used by the interactive terminal weather command

export const WEATHER_ICONS = {
  sun: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><circle cx="8" cy="8" r="3.5"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',

  partlyCloudy: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><circle cx="6" cy="5" r="2.5"/><path d="M6 1v1M2 5H1M11 5h-1M3.17 2.17l.71.71M8.83 2.17l-.71.71" stroke="currentColor" stroke-width="1" stroke-linecap="round"/><path d="M4 10a3 3 0 0 1 2.83-3h.34A3 3 0 0 1 10 10a2 2 0 0 1 2 2H4a2 2 0 0 1 0-4z"/></svg>',

  cloud: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M4 12a3 3 0 0 1-.18-6A4 4 0 0 1 11.5 5 3.5 3.5 0 0 1 12 12H4z"/></svg>',

  rain: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M4 9a3 3 0 0 1-.18-6A4 4 0 0 1 11.5 2 3.5 3.5 0 0 1 12 9H4z"/><path d="M5 11v3M8 11v3M11 11v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',

  snow: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M4 9a3 3 0 0 1-.18-6A4 4 0 0 1 11.5 2 3.5 3.5 0 0 1 12 9H4z"/><circle cx="5" cy="11.5" r="1"/><circle cx="8" cy="13" r="1"/><circle cx="11" cy="11.5" r="1"/></svg>',

  fog: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M2 5h12M2 8h12M2 11h10M4 14h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" fill="none"/></svg>',

  thunderstorm: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M4 8a3 3 0 0 1-.18-6A4 4 0 0 1 11.5 1 3.5 3.5 0 0 1 12 8H4z"/><path d="M9 9l-2 4h3l-2 3" stroke="#facc15" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>',

  wind: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 16 16"><path d="M2 5h8a2 2 0 1 0-2-2M2 8h10a2 2 0 1 1-2 2M2 11h6a2 2 0 1 0-2-2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',

  thermometer: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M9 1a2 2 0 0 0-2 2v6.27A3.5 3.5 0 1 0 11 13a3.48 3.48 0 0 0-2-3.17V3a2 2 0 0 0-2-2zm0 2a.5.5 0 0 1 .5.5v7.08a.5.5 0 0 1-.25.43A2 2 0 1 1 7 13a2 2 0 0 0 1.25-1.99.5.5 0 0 1-.25-.43V3.5A.5.5 0 0 1 9 3z"/></svg>',
}

/**
 * Map a WAWA weather code to an SVG icon string.
 * Returns the most appropriate icon for the given code.
 */
export function wawaToIcon(code) {
  if (code == null) return WEATHER_ICONS.thermometer
  code = Number(code)

  if (code === 0) return WEATHER_ICONS.sun
  if (code >= 1 && code <= 3) return WEATHER_ICONS.partlyCloudy
  if (code >= 4 && code <= 5) return WEATHER_ICONS.fog
  if (code >= 10 && code <= 12) return WEATHER_ICONS.fog
  if (code === 18) return WEATHER_ICONS.wind
  if (code >= 20 && code <= 26) return WEATHER_ICONS.cloud
  if (code >= 27 && code <= 29) return WEATHER_ICONS.wind
  if (code >= 30 && code <= 49) return WEATHER_ICONS.fog
  if (code >= 50 && code <= 59) return WEATHER_ICONS.rain
  if (code >= 60 && code <= 69) return WEATHER_ICONS.rain
  if (code >= 70 && code <= 79) return WEATHER_ICONS.snow
  if (code >= 80 && code <= 84) return WEATHER_ICONS.rain
  if (code >= 85 && code <= 89) return WEATHER_ICONS.snow
  if (code >= 90 && code <= 99) return WEATHER_ICONS.thunderstorm

  return WEATHER_ICONS.cloud
}
