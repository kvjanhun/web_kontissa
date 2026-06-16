---
name: i18n-check
description: Diff the en/fi locale files in frontend/locales and report any keys missing from either side, plus keys referenced in code but absent from both. Use after adding translatable copy, before pushing, or when the user reports a missing translation.
---

# /i18n-check

The i18n store (`frontend/stores/i18n.js`) reads flat key-value JSON from `frontend/locales/en.json` and `frontend/locales/fi.json`. The runtime fallback chain is **locale → English → raw key**, so a missing Finnish translation silently leaks English copy. This skill catches drift before it ships.

## Process

1. **Diff the two files.** Both are flat (no nesting). Report:
   - Keys in `en.json` missing from `fi.json` (English-only — most common drift).
   - Keys in `fi.json` missing from `en.json` (rare; usually a typo).
   - Total key count for each side and whether they match.

   The cleanest way is a small Python one-liner:
   ```bash
   python3 -c "
   import json
   en = json.load(open('frontend/locales/en.json'))
   fi = json.load(open('frontend/locales/fi.json'))
   missing_fi = sorted(set(en) - set(fi))
   missing_en = sorted(set(fi) - set(en))
   print(f'en: {len(en)} keys, fi: {len(fi)} keys')
   if missing_fi: print('Missing in fi:', *missing_fi, sep='\n  ')
   if missing_en: print('Missing in en:', *missing_en, sep='\n  ')
   if not missing_fi and not missing_en: print('In sync.')
   "
   ```

2. **Optional: scan code for orphan keys.** Find `t('...')` calls in `frontend/` (Vue/JS files) that don't resolve to any key in either locale. These render as the raw key string at runtime — a visible bug. Use ripgrep:
   ```bash
   rg -oN "t\(['\"]([a-zA-Z0-9._-]+)['\"]" frontend/ -r '$1' --no-filename | sort -u
   ```
   then diff against the union of `en.json` keys.

   Note: dynamic keys (e.g. `t(`section.${type}`)`) won't be caught by static analysis — flag them as "skipped" in the report rather than as missing.

3. **Report.** On full success: `i18n-check: 140/140 keys in sync, no orphans`. On drift: list the offending keys grouped by category (missing_fi / missing_en / orphans).

## Notes

- Do **not** auto-translate. Missing Finnish copy needs a human (the user is a native Finnish speaker; machine translation here is worse than nothing).
- If the user added new English copy and wants Finnish stubs added with TODO markers, do that explicitly only on request — the file should never be committed with placeholder strings as live translations.
- Locale files are sorted by convention but not enforced. If the diff is large, mention sort order at the end (don't reorder without permission — diffs become unreadable).
