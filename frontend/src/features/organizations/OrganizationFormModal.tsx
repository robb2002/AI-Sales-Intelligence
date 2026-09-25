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
import type { OrganizationSummary } from '../../types/api'

const ORG_TYPES = [
  { value: 'university', label: 'University' },
  { value: 'college', label: 'College' },
  { value: 'k12_district', label: 'K-12 district' },
  { value: 'public_sector_education', label: 'Public-sector education' },
] as const

const MARKET_ROLES = [
  { value: 'target', label: 'Target' },
  { value: 'competitor', label: 'Competitor' },
] as const

type Props = {
  mode: 'create' | 'edit'
  initial?: OrganizationSummary | null
  open: boolean
  onClose: () => void
  onSaved: (organizationId: string) => void
}

export function OrganizationFormModal({ mode, initial, open, onClose, onSaved }: Props) {
  const [name, setName] = useState('')
  const [organizationType, setOrganizationType] = useState('university')
  const [marketRole, setMarketRole] = useState('target')
  const [stateCode, setStateCode] = useState('')
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setError(null)
    if (mode === 'edit' && initial) {
      setName(initial.name)
      setOrganizationType(initial.organization_type)
      setMarketRole(initial.market_role)
      setStateCode(initial.state_code ?? '')
      setWebsiteUrl(initial.website_url ?? '')
    } else {
      setName('')
      setOrganizationType('university')
      setMarketRole('target')
      setStateCode('')
      setWebsiteUrl('')
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
        const updated = await updateOrganization(initial.organization_id, body)
        onSaved(updated.organization_id)
      }
      onClose()
    } catch (err) {
      if (isApiError(err)) {
        const websiteDetail = err.details.website_url
        setError(
          typeof websiteDetail === 'string' && err.code === 'VALIDATION_ERROR'
            ? err.message
            : err.message,
        )
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
          The official website is live-checked before save. New organizations start inactive until
          you activate tracking.
        </p>

        <form className="mt-6 space-y-4" onSubmit={(e) => void onSubmit(e)}>
          {error && (
            <Alert variant="error" title="Could not save">
              {error}
            </Alert>
          )}

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
