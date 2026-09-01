// A project's reach: how far down the stack it went, not where it runs.
//
// Every project on this site runs on all seven layers — same box, same nginx, same
// CI, same Grafana — so "which layers does this touch" would give every project an
// identical set and say nothing. Reach is the question worth answering: which
// layers did this project require building something at.
//
// Reach is naturally contiguous, so the tokens are collapsed into ranges. "L2–L7"
// reads as depth on sight, where a loose set like "L2 L3 L4 L5 L6 L7" makes the
// reader reverse-engineer the rule. Gaps are still possible via the admin, so a
// non-contiguous selection renders as several ranges rather than one dishonest one.
export function useLayerReach() {
  function reachRanges(tokens) {
    const levels = [...new Set(
      (tokens || [])
        .map((token) => Number.parseInt(String(token).slice(1), 10))
        .filter((n) => Number.isInteger(n) && n >= 1 && n <= 7),
    )].sort((a, b) => a - b)

    const ranges = []
    let start = null
    let prev = null

    const flush = () => {
      if (start === null) return
      ranges.push(start === prev ? `L${start}` : `L${start}–L${prev}`)
    }

    for (const level of levels) {
      if (start === null) {
        start = prev = level
      } else if (level === prev + 1) {
        prev = level
      } else {
        flush()
        start = prev = level
      }
    }
    flush()

    return ranges
  }

  return { reachRanges }
}
