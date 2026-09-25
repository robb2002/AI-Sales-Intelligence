import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import { listOrganizations } from '../../api/organizations'
import { AdvisorPanel } from '../../components/intelligence/AdvisorPanel'
import { EmptyState } from '../../components/ui/EmptyState'
import { FieldLabel, Select } from '../../components/ui/Input'
import { Skeleton } from '../../components/ui/Skeleton'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import { Sparkles } from 'lucide-react'

export function AdvisorPage() {
  useDocumentTitle('AI Sales Advisor')
  const [params, setParams] = useSearchParams()
  const orgFromUrl = params.get('organization_id') ?? ''
  const [selectedId, setSelectedId] = useState(orgFromUrl)

  const orgsQuery = useQuery({
    queryKey: ['organizations', 'advisor-scope'],
    queryFn: () => listOrganizations({ limit: 100, sort: 'name', direction: 'asc' }),
  })

  const organizations = orgsQuery.data?.data ?? []
  const selected = useMemo(
    () => organizations.find((o) => o.organization_id === (selectedId || orgFromUrl)),
    [organizations, selectedId, orgFromUrl],
  )

  const activeId = selected?.organization_id ?? ''

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="text-h1 text-primary">AI Sales Advisor</h1>
        <p className="mt-2 text-body text-secondary">
          Answers only from documents collected for one organization. No open-web search.
        </p>
      </div>

      <div className="max-w-md">
        <FieldLabel htmlFor="advisor-org">Organization scope</FieldLabel>
        {orgsQuery.isLoading ? (
          <Skeleton className="mt-2 h-10 w-full" />
        ) : (
          <Select
            id="advisor-org"
            value={activeId}
            onChange={(e) => {
              const id = e.target.value
              setSelectedId(id)
              if (id) setParams({ organization_id: id })
              else setParams({})
            }}
          >
            <option value="">Select an organization…</option>
            {organizations.map((org) => (
              <option key={org.organization_id} value={org.organization_id}>
                {org.name}
              </option>
            ))}
          </Select>
        )}
      </div>

      {!activeId && (
        <EmptyState
          icon={Sparkles}
          title="Choose an organization"
          description="The Advisor is scoped to one organization at a time. Select a tracked organization to ask about its collected evidence."
        />
      )}

      {activeId && selected && (
        <AdvisorPanel
          key={activeId}
          scopeType="organization"
          scopeId={activeId}
          scopeLabel={selected.name}
        />
      )}
    </div>
  )
}
