// Inline SVG weather icons (Solar 'bold' set, fill=currentColor) for the interactive
// terminal weather command. Injected as HTML strings via pushLine (v-html), so they
// are inlined here rather than rendered through the <Icon> component.

export const WEATHER_ICONS = {
  // solar:sun-bold
  sun: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path fill="currentColor" d="M18 12a6 6 0 1 1-12 0a6 6 0 0 1 12 0"/><path fill="currentColor" fill-rule="evenodd" d="M12 1.25a.75.75 0 0 1 .75.75v1a.75.75 0 0 1-1.5 0V2a.75.75 0 0 1 .75-.75M4.399 4.399a.75.75 0 0 1 1.06 0l.393.392a.75.75 0 0 1-1.06 1.061l-.393-.393a.75.75 0 0 1 0-1.06m15.202 0a.75.75 0 0 1 0 1.06l-.393.393a.75.75 0 0 1-1.06-1.06l.393-.393a.75.75 0 0 1 1.06 0M1.25 12a.75.75 0 0 1 .75-.75h1a.75.75 0 0 1 0 1.5H2a.75.75 0 0 1-.75-.75m19 0a.75.75 0 0 1 .75-.75h1a.75.75 0 0 1 0 1.5h-1a.75.75 0 0 1-.75-.75m-2.102 6.148a.75.75 0 0 1 1.06 0l.393.393a.75.75 0 1 1-1.06 1.06l-.393-.393a.75.75 0 0 1 0-1.06m-12.296 0a.75.75 0 0 1 0 1.06l-.393.393a.75.75 0 1 1-1.06-1.06l.392-.393a.75.75 0 0 1 1.061 0M12 20.25a.75.75 0 0 1 .75.75v1a.75.75 0 0 1-1.5 0v-1a.75.75 0 0 1 .75-.75" clip-rule="evenodd"/></svg>',

  // solar:cloud-sun-bold
  partlyCloudy: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path fill="currentColor" d="M16.286 20C19.442 20 22 17.472 22 14.353c0-2.472-1.607-4.573-3.845-5.338C17.837 6.194 15.415 4 12.476 4C9.32 4 6.762 6.528 6.762 9.647c0 .69.125 1.35.354 1.962a4.4 4.4 0 0 0-.83-.08C3.919 11.53 2 13.426 2 15.765S3.919 20 6.286 20z"/><path fill="currentColor" d="M9.94 2.955a5 5 0 0 0-6.327 7.723a5.8 5.8 0 0 1 1.664-.561a7 7 0 0 1-.015-.47c0-3.073 1.951-5.677 4.678-6.692"/></svg>',

  // solar:clouds-bold
  cloud: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path fill="currentColor" d="M18.286 22C20.337 22 22 20.42 22 18.47c0-1.544-1.045-2.857-2.5-3.336C19.295 13.371 17.72 12 15.81 12c-2.052 0-3.715 1.58-3.715 3.53c0 .43.082.844.23 1.226a3 3 0 0 0-.54-.05C10.248 16.706 9 17.89 9 19.353S10.247 22 11.786 22z"/><path fill="currentColor" d="M21.551 14.55a5 5 0 0 0-.751-.486c-.66-2.101-2.686-3.564-4.99-3.564c-2.754 0-5.124 2.1-5.212 4.87c-1.321.37-2.41 1.342-2.867 2.63H6.286C3.919 18 2 16.104 2 13.765s1.919-4.236 4.286-4.236q.427.001.83.08a5.6 5.6 0 0 1-.354-1.962C6.762 4.528 9.32 2 12.476 2c2.94 0 5.361 2.194 5.68 5.015C20.392 7.78 22 9.881 22 12.353c0 .78-.16 1.522-.449 2.197"/></svg>',

  // solar:cloud-rain-bold
  rain: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path fill="currentColor" fill-rule="evenodd" d="M12.03 14.97a.75.75 0 0 1 0 1.06l-2 2a.75.75 0 1 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0m4.5 0a.75.75 0 0 1 0 1.06l-2 2a.75.75 0 1 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0m-8.5 3.5a.75.75 0 0 1 0 1.06l-2 2a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0m9.5 0a.75.75 0 0 1 0 1.06l-2 2a.75.75 0 1 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0m-5 1a.75.75 0 0 1 0 1.06l-2 2a.75.75 0 1 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0" clip-rule="evenodd"/><path fill="currentColor" d="M19.124 18.255a2.24 2.24 0 0 0-1.351-1.369a2.25 2.25 0 0 0-3.364-2.977l-.802.801a2.25 2.25 0 0 0-3.698-.801l-2 2a2.24 2.24 0 0 0-.532.844c-.534.03-1.06.248-1.468.656l-1.268 1.268C3.091 18.04 2 16.528 2 14.765c0-2.34 1.919-4.236 4.286-4.236q.427.001.83.08a5.6 5.6 0 0 1-.354-1.962C6.762 5.528 9.32 3 12.476 3c2.94 0 5.361 2.194 5.68 5.015C20.392 8.78 22 10.881 22 13.353c0 2.098-1.158 3.929-2.876 4.902"/><path fill="currentColor" d="M12.03 14.97a.75.75 0 0 1 0 1.06l-2 2a.746.746 0 0 1-1.06 0a.746.746 0 0 1 0-1.06l2-2a.75.75 0 0 1 1.06 0m3.44 0l-2 2a.75.75 0 1 0 1.06 1.06l2-2a.75.75 0 1 0-1.06-1.06"/></svg>',

  // solar:cloud-snowfall-minimalistic-bold
  snow: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path fill="currentColor" d="M13 18a1 1 0 1 1-2 0a1 1 0 0 1 2 0m0 3a1 1 0 1 1-2 0a1 1 0 0 1 2 0m3-1.5a1 1 0 1 1-2 0a1 1 0 0 1 2 0m0-3a1 1 0 1 1-2 0a1 1 0 0 1 2 0m-6 3a1 1 0 1 1-2 0a1 1 0 0 1 2 0m0-3a1 1 0 1 1-2 0a1 1 0 0 1 2 0"/><path fill="currentColor" d="M12 19a1 1 0 0 0 .781-.376a.997.997 0 0 0-.182-1.425a.995.995 0 0 0-1.198 0A.999.999 0 0 0 12 19"/><path fill="currentColor" d="M22 13.353c0 2.733-1.965 5.013-4.576 5.535A2.5 2.5 0 0 0 17 18a2.5 2.5 0 1 0-4.33-2.41a2.5 2.5 0 0 0-1.34 0A2.501 2.501 0 1 0 7 18c-.219.29-.375.63-.45 1h-.264C3.919 19 2 17.104 2 14.765s1.919-4.236 4.286-4.236q.427.001.83.08a5.6 5.6 0 0 1-.354-1.962C6.762 5.528 9.32 3 12.476 3c2.94 0 5.361 2.194 5.68 5.015C20.392 8.78 22 10.881 22 13.353"/><path fill="currentColor" d="M15 17.5a1 1 0 0 1-.781-.376A1 1 0 1 1 15 17.5m-6-2a1 1 0 1 1 0 2a1 1 0 0 1 0-2"/></svg>',

  // solar:fog-bold
  fog: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path fill="currentColor" d="M6.762 7.647C6.762 4.528 9.32 2 12.476 2c2.94 0 5.361 2.194 5.68 5.015C20.392 7.78 22 9.881 22 12.353a5.57 5.57 0 0 1-.808 2.897H22a.75.75 0 0 1 0 1.5H2a.75.75 0 0 1 0-1.5h.271A4.2 4.2 0 0 1 2 13.765c0-2.34 1.919-4.236 4.286-4.236q.427.001.83.08a5.6 5.6 0 0 1-.354-1.962M5 18.25a.75.75 0 0 0 0 1.5h14a.75.75 0 0 0 0-1.5zm3 3a.75.75 0 0 0 0 1.5h8a.75.75 0 0 0 0-1.5z"/></svg>',

  // solar:cloud-bolt-bold
  thunderstorm: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path fill="currentColor" d="m9.626 17.465l1.148-1.555c.743-1.005 1.114-1.508 1.46-1.401s.346.722.346 1.955v.116c0 .445 0 .667.142.806l.008.008c.145.136.376.136.838.136c.832 0 1.249 0 1.39.252l.006.013c.133.257-.108.583-.59 1.235l-1.148 1.555c-.743 1.005-1.114 1.507-1.46 1.401s-.346-.723-.346-1.955v-.116c0-.445 0-.667-.142-.806l-.008-.008c-.145-.136-.376-.136-.838-.136c-.832 0-1.248 0-1.39-.253l-.006-.012c-.133-.257.108-.583.59-1.235"/><path fill="currentColor" d="M7.578 18.011c.059-.207.14-.375.199-.486c.157-.296.398-.622.6-.896l1.241-1.68c.327-.442.656-.887.954-1.197c.218-.227.997-1.018 2.102-.679c1.138.35 1.308 1.48 1.35 1.79c.044.334.054.745.056 1.169a6 6 0 0 1 .65.043c.334.047 1.107.203 1.537.977l.029.053c.165.319.215.627.204.902c3.057-.111 5.5-2.597 5.5-5.647c0-2.473-1.607-4.576-3.845-5.342C17.837 4.195 15.415 2 12.476 2C9.32 2 6.762 4.53 6.762 7.651c0 .69.125 1.352.354 1.963a4.4 4.4 0 0 0-.83-.08C3.919 9.535 2 11.433 2 13.774c0 2.34 1.919 4.238 4.286 4.238z"/></svg>',

  // solar:wind-bold
  wind: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path fill="currentColor" fill-rule="evenodd" d="M6.25 5.5A3.25 3.25 0 1 1 9.5 8.75H3a.75.75 0 0 1 0-1.5h6.5A1.75 1.75 0 1 0 7.75 5.5v.357a.75.75 0 1 1-1.5 0zm8 2a4.25 4.25 0 1 1 4.25 4.25H2a.75.75 0 0 1 0-1.5h16.5a2.75 2.75 0 1 0-2.75-2.75V8a.75.75 0 0 1-1.5 0zm-11 6.5a.75.75 0 0 1 .75-.75h14.5a4.25 4.25 0 1 1-4.25 4.25V17a.75.75 0 0 1 1.5 0v.5a2.75 2.75 0 1 0 2.75-2.75H4a.75.75 0 0 1-.75-.75" clip-rule="evenodd"/></svg>',

  // solar:temperature-bold
  thermometer: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path fill="currentColor" fill-rule="evenodd" d="M17.5 16.5a5.5 5.5 0 1 1-8.939-4.293c.264-.211.439-.521.439-.86V5a3 3 0 1 1 6 0v6.348c0 .338.175.648.439.86A5.49 5.49 0 0 1 17.5 16.5M12 4.25a.75.75 0 0 1 .75.75v8.38c0 .437.297.808.658 1.054a2.5 2.5 0 1 1-2.816 0c.36-.246.658-.617.658-1.054V5a.75.75 0 0 1 .75-.75" clip-rule="evenodd"/></svg>',

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
