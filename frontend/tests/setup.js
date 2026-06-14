function createMemoryStorage() {
  const data = new Map()
  return {
    get length() {
      return data.size
    },
    clear() {
      data.clear()
    },
    getItem(key) {
      return data.has(String(key)) ? data.get(String(key)) : null
    },
    key(index) {
      return Array.from(data.keys())[index] || null
    },
    removeItem(key) {
      data.delete(String(key))
    },
    setItem(key, value) {
      data.set(String(key), String(value))
    },
  }
}

function getStorage(name) {
  try {
    return window?.[name] || createMemoryStorage()
  } catch {
    return createMemoryStorage()
  }
}

Object.defineProperty(globalThis, 'localStorage', {
  value: getStorage('localStorage'),
  configurable: true,
})

Object.defineProperty(globalThis, 'sessionStorage', {
  value: getStorage('sessionStorage'),
  configurable: true,
})
