import { useEffect, useState } from 'react'
import { isApiError } from '../../api/client'
import { deleteOrganization } from '../../api/organizations'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { FieldLabel, Input } from '../../components/ui/Input'

type Props = {
  open: boolean
  organizationId: string
  organizationName: string
  marketRole: string
  onClose: () => void
  onDeleted: () => void
}

export function DeleteOrganizationModal({
  open,
  organizationId,
  organizationName,
  marketRole,
  onClose,
  onDeleted,
}: Props) {
  const [confirmName, setConfirmName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (!open) return
    setConfirmName('')
    setError(null)
    setDeleting(false)
  }, [open, organizationId])

  if (!open) return null

  const label = marketRole === 'competitor' ? 'competitor / vendor' : 'organization'
  const nameMatches = confirmName.trim() === organizationName

  async function onConfirm() {
    if (!nameMatches || deleting) return
    setError(null)
    setDeleting(true)
    try {
      await deleteOrganization(organizationId)
      onDeleted()
    } catch (err) {
      setError(
        isApiError(err)
          ? err.message
          : 'The organization could not be deleted. Try again in a moment.',
      )
      setDeleting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-navy-900/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-org-title"
    >
      <div className="w-full max-w-lg rounded-lg border border-default bg-surface p-6 shadow-md">
        <h2 id="delete-org-title" className="text-h3 font-semibold text-navy-700">
          Delete {label}?
        </h2>
        <p className="mt-2 text-body-sm text-secondary">
          This permanently removes <span className="font-medium text-primary">{organizationName}</span>{' '}
          and all of its signals, opportunities, evidence, documents, page sources, scans, and Advisor
          history. Other organizations are not changed. This cannot be undone.
        </p>
        <div className="mt-4">
          <FieldLabel htmlFor="delete-org-confirm">Type the full name to confirm</FieldLabel>
          <Input
            id="delete-org-confirm"
            value={confirmName}
            onChange={(e) => setConfirmName(e.target.value)}
            disabled={deleting}
            autoComplete="off"
          />
        </div>

        {error && (
          <div className="mt-4">
            <Alert variant="error" title="Delete failed">
              {error}
            </Alert>
          </div>
        )}

        <div className="mt-6 flex flex-wrap justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={deleting}>
            Cancel
          </Button>
          <Button
            variant="danger"
            loading={deleting}
            disabled={!nameMatches || deleting}
            onClick={() => void onConfirm()}
          >
            Delete permanently
          </Button>
        </div>
      </div>
    </div>
  )
}
