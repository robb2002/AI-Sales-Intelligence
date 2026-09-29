import { useEffect, useState, type FormEvent } from 'react'
import { isApiError } from '../../api/client'
import { updateScanAllSchedule } from '../../api/scanAllTrigger'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { FieldLabel, Input } from '../../components/ui/Input'
import { isoToLocalInputValue, localInputValueToIso } from '../../lib/datetimeLocal'

type Props = {
  open: boolean
  currentScheduledAt: string | null
  onClose: () => void
  onSaved: (scheduledAt: string | null) => void
}

export function ScanAllSchedulerModal({ open, currentScheduledAt, onClose, onSaved }: Props) {
  const [localValue, setLocalValue] = useState('')
  const [minLocal, setMinLocal] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setError(null)
    setMinLocal(isoToLocalInputValue(new Date().toISOString()))
    setLocalValue(currentScheduledAt ? isoToLocalInputValue(currentScheduledAt) : '')
  }, [open, currentScheduledAt])

  if (!open) return null

  async function save(iso: string | null) {
    setError(null)
    setSaving(true)
    try {
      const result = await updateScanAllSchedule(iso)
      onSaved(result.scheduled_at)
      onClose()
    } catch (err) {
      setError(isApiError(err) ? err.message : 'The schedule could not be saved.')
    } finally {
      setSaving(false)
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    void save(localInputValueToIso(localValue))
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-navy-900/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="scan-all-schedule-title"
    >
      <div className="w-full max-w-md rounded-lg border border-default bg-surface p-6 shadow-md">
        <h2 id="scan-all-schedule-title" className="text-h3 font-semibold text-navy-700">
          Schedule Scan All
        </h2>
        <p className="mt-1 text-body-sm text-secondary">
          Set a future date and time to automatically start Scan All (every active tracked
          organization) once.
        </p>

        <form className="mt-5 space-y-4" onSubmit={onSubmit}>
          {error && (
            <Alert variant="error" title="Could not save">
              {error}
            </Alert>
          )}

          <div>
            <FieldLabel htmlFor="scan-all-schedule-input">Trigger Scan All at</FieldLabel>
            <Input
              id="scan-all-schedule-input"
              type="datetime-local"
              value={localValue}
              min={minLocal}
              onChange={(e) => setLocalValue(e.target.value)}
              disabled={saving}
            />
            <p className="mt-1.5 text-caption text-muted">
              Your local time zone. Stored and checked in UTC. Fires once, then clears.
            </p>
          </div>

          <div className="flex flex-wrap justify-end gap-2 pt-2">
            {currentScheduledAt && (
              <Button
                type="button"
                variant="tertiary"
                onClick={() => void save(null)}
                disabled={saving}
              >
                Clear schedule
              </Button>
            )}
            <Button type="button" variant="tertiary" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={saving} disabled={!localValue}>
              Save
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
