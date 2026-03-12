import { describe, it, expect } from 'vitest'
import { levenshtein, findClosestCommand, parseCowArgs } from '~/composables/useTerminal.js'

describe('useTerminal - pure functions', () => {
  describe('levenshtein', () => {
    it('returns 0 for identical strings', () => {
      expect(levenshtein('test', 'test')).toBe(0)
    })

    it('returns length of string if other is empty', () => {
      expect(levenshtein('test', '')).toBe(4)
      expect(levenshtein('', 'test')).toBe(4)
    })

    it('calculates distance correctly for single letter changes', () => {
      expect(levenshtein('help', 'halp')).toBe(1)
      expect(levenshtein('fetch', 'fetxh')).toBe(1)
    })

    it('calculates distance for additions and deletions', () => {
      expect(levenshtein('about', 'bout')).toBe(1)
      expect(levenshtein('clear', 'clearr')).toBe(1)
    })

    it('calculates larger distances', () => {
      expect(levenshtein('weather', 'what')).toBe(4)
    })
  })

  describe('findClosestCommand', () => {
    it('returns null if the input is too far from any command', () => {
      expect(findClosestCommand('completelyrandom')).toBeNull()
      expect(findClosestCommand('asdfghjkl')).toBeNull()
    })

    it('returns exact match', () => {
      expect(findClosestCommand('fetch')).toBe('fetch')
      expect(findClosestCommand('weather')).toBe('weather')
    })

    it('returns closest command within threshold (max 2)', () => {
      // 1 distance
      expect(findClosestCommand('halp')).toBe('help')
      expect(findClosestCommand('fethc')).toBe('fetch')
      expect(findClosestCommand('clera')).toBe('clear')
      
      // 2 distance
      expect(findClosestCommand('cwosay')).toBe('cowsay')
      expect(findClosestCommand('hlpe')).toBe('help')
    })
    
    it('favors closest command when multiple are possible', () => {
      // both cowthink and cowsay are somewhat similar, testing edge cases isn't strict,
      // but it should pick cowsay over cowthink if it's closer to cowsay.
      expect(findClosestCommand('cowsya')).toBe('cowsay')
    })
  })

  describe('parseCowArgs', () => {
    it('defaults to character "cow" and message "moo"', () => {
      const result = parseCowArgs([])
      expect(result).toEqual({ character: 'cow', message: 'moo' })
    })

    it('parses message correctly', () => {
      const result = parseCowArgs(['hello', 'world'])
      expect(result).toEqual({ character: 'cow', message: 'hello world' })
    })

    it('parses character flag -f correctly', () => {
      const result = parseCowArgs(['-f', 'tux'])
      expect(result).toEqual({ character: 'tux', message: 'moo' })
    })

    it('parses character flag -f and message together', () => {
      const result = parseCowArgs(['-f', 'tux', 'hello', 'linux'])
      expect(result).toEqual({ character: 'tux', message: 'hello linux' })
    })

    it('parses list flag -l correctly', () => {
      const result = parseCowArgs(['-l'])
      expect(result).toEqual({ list: true })
    })

    it('prioritizes list flag -l over other args', () => {
      const result = parseCowArgs(['-f', 'tux', '-l', 'hello'])
      expect(result).toEqual({ list: true })
    })

    it('handles incomplete -f flag gracefully', () => {
      // -f at the end without a character falls through and becomes the message
      const result = parseCowArgs(['-f'])
      expect(result).toEqual({ character: 'cow', message: '-f' })
    })
  })
})
