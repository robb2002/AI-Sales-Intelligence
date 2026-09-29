/** Conversions between an ISO UTC timestamp and an <input type="datetime-local"> value
 * (which represents the browser's local wall-clock time with no timezone offset). */

/** UTC ISO string -> value for <input type="datetime-local">. */
export function isoToLocalInputValue(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** <input type="datetime-local"> value (local wall time, no offset) -> UTC ISO string, or null. */
export function localInputValueToIso(value: string): string | null {
  if (!value) return null
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? null : d.toISOString()
}
