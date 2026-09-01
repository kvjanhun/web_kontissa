// Turns the host uptime that /api/server-info reports into something the footer can
// render in either language.
//
// The mapping is deliberately coarse. The footer's job is to show that the box is
// up, not to report a precise figure — and a precise one invites the question of
// what happened the last time it reset.
export function useUptime() {
  // Returns { key, n } for the caller to pass through t(), or null when there is no
  // usable figure. Null is the "render the status line without a number" case, which
  // covers a failed fetch, a field the API omitted, and a nonsense value alike.
  function uptimeLabel(seconds) {
    if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds < 0) return null

    const days = Math.floor(seconds / 86400)
    if (days >= 1) {
      return { key: days === 1 ? 'home.footer.uptimeDay' : 'home.footer.uptimeDays', n: days }
    }

    // Floor to hours, but never to zero: a box rebooted twenty minutes ago reads
    // "1 hour" rather than "0 hours", which would look like a bug.
    const hours = Math.max(1, Math.floor(seconds / 3600))
    return { key: hours === 1 ? 'home.footer.uptimeHour' : 'home.footer.uptimeHours', n: hours }
  }

  return { uptimeLabel }
}
