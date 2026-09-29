import { useEffect, useState, type FormEvent } from 'react'
import { isApiError } from '../../api/client'
import {
  createOrganization,
  updateOrganization,
  type OrganizationPatchBody,
  type OrganizationWriteBody,
} from '../../api/organizations'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { FieldLabel, Input, Select } from '../../components/ui/Input'
import { isoToLocalInputValue, localInputValueToIso } from '../../lib/datetimeLocal'
import type { OrganizationSummary } from '../../types/api'

const ORG_TYPES = [
  { value: 'university', label: 'University' },
  { value: 'college', label: 'College' },
  { value: 'k12_district', label: 'K-12 district' },
  { value: 'public_sector_education', label: 'Public-sector education' },
  { value: 'edtech_company', label: 'EdTech company' },
] as const

const MARKET_ROLES = [
  { value: 'target', label: 'Target' },
  { value: 'competitor', label: 'Competitor' },
] as const

type Tab = 'details' | 'schedule'

type Props = {
  mode: 'create' | 'edit'
  initial?: OrganizationSummary | null
  open: boolean
  onClose: () => void
  onSaved: (organizationId: string) => void
  /** From GET /api/v1/me — only a Sales Manager may see/use the Schedule tab. */
  isManager: boolean
}

export function OrganizationFormModal({ mode, initial, open, onClose, onSaved, isManager }: Props) {
  const [tab, setTab] = useState<Tab>('details')
  const [name, setName] = useState('')
  const [organizationType, setOrganizationType] = useState('university')
  const [marketRole, setMarketRole] = useState('target')
  const [stateCode, setStateCode] = useState('')
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [scheduleLocal, setScheduleLocal] = useState('')
  const [minLocal, setMinLocal] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const showScheduleTab = mode === 'edit' && isManager

  useEffect(() => {
    if (!open) return
    setError(null)
    setTab('details')
    setMinLocal(isoToLocalInputValue(new Date().toISOString()))
    if (mode === 'edit' && initial) {
      setName(initial.name)
      setOrganizationType(initial.organization_type)
      setMarketRole(initial.market_role)
      setStateCode(initial.state_code ?? '')
      setWebsiteUrl(initial.website_url ?? '')
      setScheduleLocal(initial.scheduled_scan_at ? isoToLocalInputValue(initial.scheduled_scan_at) : '')
    } else {
      setName('')
      setOrganizationType('university')
      setMarketRole('target')
      setStateCode('')
      setWebsiteUrl('')
      setScheduleLocal('')
    }
  }, [open, mode, initial])

  if (!open) return null

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSaving(true)
    try {
      if (mode === 'create') {
        const body: OrganizationWriteBody = {
          name: name.trim(),
          organization_type: organizationType,
          market_role: marketRole,
          state_code: stateCode.trim() ? stateCode.trim().toUpperCase() : null,
          website_url: websiteUrl.trim(),
        }
        const created = await createOrganization(body)
        onSaved(created.organization_id)
      } else if (initial) {
        const body: OrganizationPatchBody = {
          name: name.trim(),
          organization_type: organizationType,
          market_role: marketRole,
          state_code: stateCode.trim() ? stateCode.trim().toUpperCase() : null,
          website_url: websiteUrl.trim(),
        }
        if (showScheduleTab) {
          body.scheduled_scan_at = localInputValueToIso(scheduleLocal)
        }
        const updated = await updateOrganization(initial.organization_id, body)
        onSaved(updated.organization_id)
      }
      onClose()
    } catch (err) {
      if (isApiError(err)) {
        setError(err.message)
        if (err.details.scheduled_scan_at) setTab('schedule')
      } else {
        setError('The organization could not be saved.')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-navy-900/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="org-form-title"
    >
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-default bg-surface p-6 shadow-md">
        <h2 id="org-form-title" className="text-h3 font-semibold text-navy-700">
          {mode === 'create' ? 'Add organization' : 'Edit organization'}
        </h2>
        <p className="mt-1 text-body-sm text-secondary">
          {tab === 'details'
            ? 'The official website is live-checked before save. New organizations start inactive until you activate tracking.'
            : 'Set a future date and time to automatically start Scan Now for this organization once.'}
        </p>

        {showScheduleTab && (
          <div role="tablist" aria-label="Edit organization" className="mt-4 flex gap-4 border-b border-default">
            <button
              type="button"
              role="tab"
              id="org-form-tab-details"
              aria-selected={tab === 'details'}
              aria-controls="org-form-panel-details"
              onClick={() => setTab('details')}
              className={
                tab === 'details'
                  ? 'border-b-2 border-navy-600 pb-2 text-body font-medium text-navy-600'
                  : 'pb-2 text-body font-medium text-secondary hover:text-navy-600'
              }
            >
              Details
            </button>
            <button
              type="button"
              role="tab"
              id="org-form-tab-schedule"
              aria-selected={tab === 'schedule'}
              aria-controls="org-form-panel-schedule"
              onClick={() => setTab('schedule')}
              className={
                tab === 'schedule'
                  ? 'border-b-2 border-navy-600 pb-2 text-body font-medium text-navy-600'
                  : 'pb-2 text-body font-medium text-secondary hover:text-navy-600'
              }
            >
              Schedule
            </button>
          </div>
        )}

        <form className="mt-6 space-y-4" onSubmit={(e) => void onSubmit(e)}>
          {error && (
            <Alert variant="error" title="Could not save">
              {error}
            </Alert>
          )}

          <div
            id="org-form-panel-details"
            role="tabpanel"
            aria-labelledby="org-form-tab-details"
            hidden={tab !== 'details'}
            className="space-y-4"
          >
            <div>
              <FieldLabel htmlFor="org-name">Name</FieldLabel>
              <Input
                id="org-name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={saving}
                maxLength={200}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <FieldLabel htmlFor="org-type">Type</FieldLabel>
                <Select
                  id="org-type"
                  value={organizationType}
                  onChange={(e) => setOrganizationType(e.target.value)}
                  disabled={saving}
                >
                  {ORG_TYPES.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <FieldLabel htmlFor="org-role">Market role</FieldLabel>
                <Select
                  id="org-role"
                  value={marketRole}
                  onChange={(e) => setMarketRole(e.target.value)}
                  disabled={saving}
                >
                  {MARKET_ROLES.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </Select>
              </div>
            </div>

            <div>
              <FieldLabel htmlFor="org-state">US state (optional)</FieldLabel>
              <Input
                id="org-state"
                value={stateCode}
                onChange={(e) => setStateCode(e.target.value.toUpperCase())}
                disabled={saving}
                maxLength={2}
                placeholder="AZ"
                className="max-w-24"
              />
            </div>

            <div>
              <FieldLabel htmlFor="org-website">Official website</FieldLabel>
              <Input
                id="org-website"
                required
                value={websiteUrl}
                onChange={(e) => setWebsiteUrl(e.target.value)}
                disabled={saving}
                placeholder="https://example.edu"
              />
            </div>
          </div>

          {showScheduleTab && (
            <div
              id="org-form-panel-schedule"
              role="tabpanel"
              aria-labelledby="org-form-tab-schedule"
              hidden={tab !== 'schedule'}
              className="space-y-3"
            >
              <div>
                <FieldLabel htmlFor="org-schedule">Trigger scan at</FieldLabel>
                <Input
                  id="org-schedule"
                  type="datetime-local"
                  value={scheduleLocal}
                  min={minLocal}
                  onChange={(e) => setScheduleLocal(e.target.value)}
                  disabled={saving}
                />
                <p className="mt-1.5 text-caption text-muted">
                  Your local time zone. Stored and checked in UTC. Fires Scan Now for this
                  organization once, then clears.
                </p>
              </div>
              {scheduleLocal && (
                <Button
                  type="button"
                  variant="tertiary"
                  onClick={() => setScheduleLocal('')}
                  disabled={saving}
                >
                  Clear schedule
                </Button>
              )}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="tertiary" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={saving}>
              {saving ? 'Verifying website…' : mode === 'create' ? 'Add organization' : 'Save changes'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
