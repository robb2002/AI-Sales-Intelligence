import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Building2, Globe2, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { listOrganizations } from "../../api/organizations";
import { ORG_TYPE_LABELS } from "../../features/intelligence/labels";
import { cn } from "../../lib/cn";
import type { OrganizationSummary } from "../../types/api";
import { Badge } from "../ui/Badge";
import { Skeleton } from "../ui/Skeleton";

const RING =
  "focus-visible:ring-2 focus-visible:ring-focus-ring-ai focus-visible:outline-hidden";

export type PersonaScope =
  | { kind: "organization"; organizationId: string; organizationName: string }
  | { kind: "general" };

interface PersonaScopeChooserProps {
  onSelect: (scope: PersonaScope) => void;
}

function orgMeta(org: OrganizationSummary): string {
  const parts = [
    org.state_code,
    ORG_TYPE_LABELS[org.organization_type] ??
      org.organization_type.replace(/_/g, " "),
  ].filter((part): part is string => Boolean(part));
  return parts.join(" · ");
}

export function PersonaScopeChooser({ onSelect }: PersonaScopeChooserProps) {
  const [step, setStep] = useState<"choose" | "pick">("choose");

  if (step === "pick") {
    return (
      <OrganizationPicker
        onBack={() => setStep("choose")}
        onPick={(org) =>
          onSelect({
            kind: "organization",
            organizationId: org.organization_id,
            organizationName: org.name,
          })
        }
      />
    );
  }

  const optionClass = cn(
    "flex min-h-16 w-full items-start gap-3 rounded-lg border border-indigo-400/40 px-3 py-3 text-left transition-colors",
    "hover:bg-indigo-500/25",
    RING,
  );

  return (
    <div className="space-y-3">
      <h3 className="text-h3 text-on-ai">What would you like to work on?</h3>
      <button
        type="button"
        autoFocus
        onClick={() => setStep("pick")}
        className={optionClass}
      >
        <Building2
          aria-hidden
          className="mt-0.5 size-5 shrink-0 text-indigo-300"
          strokeWidth={1.75}
        />
        <span>
          <span className="block text-body font-medium text-on-ai">
            A tracked organization
          </span>
          <span className="block text-caption text-on-ai-muted">
            Answers only from that organization&apos;s collected data
          </span>
        </span>
      </button>
      <button
        type="button"
        onClick={() => onSelect({ kind: "general" })}
        className={optionClass}
      >
        <Globe2
          aria-hidden
          className="mt-0.5 size-5 shrink-0 text-indigo-300"
          strokeWidth={1.75}
        />
        <span>
          <span className="block text-body font-medium text-on-ai">
            General or outside data
          </span>
          <span className="block text-caption text-on-ai-muted">
            Portfolio, competitors and general sales help
          </span>
        </span>
      </button>
    </div>
  );
}

function OrganizationPicker({
  onBack,
  onPick,
}: {
  onBack: () => void;
  onPick: (org: OrganizationSummary) => void;
}) {
  const [search, setSearch] = useState("");

  const query = useQuery({
    queryKey: ["organizations", "persona-picker"],
    queryFn: () =>
      listOrganizations({
        marketRole: ["target", "competitor"],
        sort: "name",
        limit: 100,
      }),
    staleTime: 60_000,
  });

  const rows = useMemo(() => {
    const term = search.trim().toLowerCase();
    const all = query.data?.data ?? [];
    if (!term) return all;
    return all.filter((org) =>
      `${org.name} ${orgMeta(org)}`.toLowerCase().includes(term),
    );
  }, [query.data, search]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onBack}
          className={cn(
            "inline-flex h-8 items-center gap-1 rounded-md px-2 text-caption font-medium text-indigo-200 hover:bg-indigo-500/25",
            RING,
          )}
        >
          <ArrowLeft aria-hidden className="size-3.5" strokeWidth={1.75} />
          Back
        </button>
        <h3 className="text-h3 text-on-ai">Choose an organization</h3>
      </div>

      <div className="relative">
        <Search
          aria-hidden
          className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted"
          strokeWidth={1.75}
        />
        <input
          type="search"
          autoFocus
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search organizations"
          placeholder="Search organizations…"
          className="h-10 w-full rounded-md border border-default bg-surface pr-3 pl-9 text-body text-primary placeholder:text-muted focus-visible:ring-2 focus-visible:ring-focus-ring-ai focus-visible:outline-hidden"
        />
      </div>

      {query.isLoading && (
        <div
          className="space-y-2"
          role="status"
          aria-label="Loading organizations"
        >
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} tone="dark" className="h-11 w-full" />
          ))}
        </div>
      )}

      {query.isError && (
        <div role="alert" className="space-y-2">
          <p className="text-body-sm text-red-100">
            Organizations could not be loaded.
          </p>
          <button
            type="button"
            onClick={() => void query.refetch()}
            className={cn(
              "inline-flex h-8 items-center rounded-md border border-indigo-400/50 px-3 text-caption font-medium text-indigo-200 hover:bg-indigo-500/25",
              RING,
            )}
          >
            Try again
          </button>
        </div>
      )}

      {query.isSuccess && rows.length === 0 && (
        <p className="text-body-sm text-on-ai-muted">No organizations match</p>
      )}

      {query.isSuccess && rows.length > 0 && (
        <ul className="space-y-1">
          {rows.map((org) => (
            <li key={org.organization_id}>
              <button
                type="button"
                onClick={() => onPick(org)}
                className={cn(
                  "flex min-h-11 w-full items-center justify-between gap-2 rounded-md px-3 py-1.5 text-left hover:bg-indigo-500/25",
                  RING,
                )}
              >
                <span className="min-w-0">
                  <span className="block truncate text-body-sm font-medium text-on-ai">
                    {org.name}
                  </span>
                  <span className="block truncate text-caption text-on-ai-muted">
                    {orgMeta(org)}
                  </span>
                </span>
                {org.market_role === "competitor" && (
                  <Badge variant="outline-navy-dark">Competitor</Badge>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
