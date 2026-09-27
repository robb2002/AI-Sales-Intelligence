import { Check, Copy, ExternalLink } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "../../lib/cn";
import type {
  PersonaBlock,
  PersonaResponse,
  PersonaSource,
  PersonaSourceKind,
} from "../../types/api";

const RING =
  "focus-visible:ring-2 focus-visible:ring-focus-ring-ai focus-visible:outline-hidden";

const KIND_LABELS: Record<PersonaSourceKind, string> = {
  stored_evidence: "Stored evidence",
  official_website: "Official website",
  live_lookup: "Live lookup",
  system_data: "System data",
};

function prefersReducedMotion(): boolean {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

function LayerTag({ layer }: { layer?: string }) {
  if (layer === "interpretation") {
    return (
      <span className="mr-2 inline-flex rounded-full border border-indigo-400/50 px-2 py-px align-middle text-label text-indigo-200 uppercase">
        Interpretation
      </span>
    );
  }
  if (layer === "recommended_action") {
    return (
      <span className="mr-2 inline-flex rounded-full border border-amber-300/60 px-2 py-px align-middle text-label text-amber-300 uppercase">
        Next step
      </span>
    );
  }
  return null;
}

function RefChips({
  refs,
  sources,
  onSelect,
}: {
  refs?: number[];
  sources: PersonaSource[];
  onSelect: (ref: number) => void;
}) {
  const valid = (refs ?? []).filter((r) => sources.some((s) => s.ref === r));
  if (valid.length === 0) return null;
  return (
    <span className="ml-1 inline-flex flex-wrap gap-1 align-middle">
      {valid.map((ref) => (
        <button
          key={ref}
          type="button"
          onClick={() => onSelect(ref)}
          aria-label={`Show source ${ref}`}
          className={cn(
            "inline-flex size-5 items-center justify-center rounded-full border border-indigo-400/50 text-label text-indigo-200",
            "hover:bg-indigo-500/25",
            RING,
          )}
        >
          {ref}
        </button>
      ))}
    </span>
  );
}

function EmailCard({ subject, body }: { subject: string; body: string }) {
  const [copied, setCopied] = useState<"idle" | "copied" | "failed">("idle");
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  async function copy() {
    let next: "copied" | "failed" = "copied";
    try {
      await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
    } catch {
      next = "failed";
    }
    setCopied(next);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setCopied("idle"), 2000);
  }

  return (
    <div className="rounded-lg border border-indigo-400/40 bg-navy-800 p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-label text-on-ai-muted uppercase">
          Draft — nothing is sent
        </p>
        <button
          type="button"
          onClick={() => void copy()}
          className={cn(
            "inline-flex h-7 items-center gap-1.5 rounded-md border border-indigo-400/50 px-2 text-caption font-medium text-indigo-200 hover:bg-indigo-500/25",
            RING,
          )}
        >
          {copied === "copied" ? (
            <Check aria-hidden className="size-3.5" strokeWidth={1.75} />
          ) : (
            <Copy aria-hidden className="size-3.5" strokeWidth={1.75} />
          )}
          Copy email
        </button>
      </div>
      <p className="mt-3 text-body-sm text-on-ai">
        <span className="font-semibold">Subject: </span>
        {subject}
      </p>
      <p className="mt-2 border-t border-indigo-500/30 pt-2 text-body-sm whitespace-pre-wrap text-on-ai">
        {body}
      </p>
      <p role="status" className="mt-2 min-h-4 text-caption text-on-ai-muted">
        {copied === "copied"
          ? "Copied to clipboard"
          : copied === "failed"
            ? "Copy failed. Select the text and copy it manually."
            : ""}
      </p>
    </div>
  );
}

function Block({
  block,
  sources,
  onSelectRef,
}: {
  block: PersonaBlock;
  sources: PersonaSource[];
  onSelectRef: (ref: number) => void;
}) {
  switch (block.type) {
    case "heading":
      return (
        <h4 className="text-body-sm font-semibold text-on-ai">{block.text}</h4>
      );
    case "paragraph":
      return (
        <p className="text-body-sm text-on-ai">
          <LayerTag layer={block.layer} />
          {block.text}
          <RefChips
            refs={block.refs}
            sources={sources}
            onSelect={onSelectRef}
          />
        </p>
      );
    case "bullets":
      return (
        <ul className="list-disc space-y-1.5 pl-5 text-body-sm text-on-ai marker:text-indigo-400">
          {block.items.map((item, index) => (
            <li key={index}>
              <LayerTag layer={item.layer} />
              {item.text}
              <RefChips
                refs={item.refs}
                sources={sources}
                onSelect={onSelectRef}
              />
            </li>
          ))}
        </ul>
      );
    case "email":
      return <EmailCard subject={block.subject} body={block.body} />;
    default:
      return null;
  }
}

export function PersonaAnswer({
  messageId,
  response,
  showFollowUps,
  onFollowUp,
}: {
  messageId: string;
  response: PersonaResponse;
  showFollowUps: boolean;
  onFollowUp: (text: string) => void;
}) {
  const [highlight, setHighlight] = useState<number | null>(null);
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const sourceId = (ref: number) => `persona-${messageId}-src-${ref}`;

  function selectRef(ref: number) {
    const el = document.getElementById(sourceId(ref));
    el?.scrollIntoView({
      block: "nearest",
      behavior: prefersReducedMotion() ? "auto" : "smooth",
    });
    setHighlight(ref);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setHighlight(null), 2000);
  }

  if (response.status === "unavailable") {
    return (
      <div className="rounded-lg border border-indigo-500/30 bg-navy-800 p-3">
        <p className="text-body-sm font-medium text-on-ai">
          Sales Persona is unavailable right now
        </p>
        <p className="mt-1 text-body-sm text-on-ai-muted">
          {response.answer.text ||
            "The assistant could not answer this time. Nothing was lost, so please try again in a little while."}
        </p>
      </div>
    );
  }

  const blocks = response.answer.blocks ?? [];
  const sources = response.sources ?? [];
  const followUps = (response.follow_ups ?? []).slice(0, 3);

  return (
    <div className="space-y-3">
      {response.data_origin === "cached" && (
        <p className="text-caption text-on-ai-muted">
          Some of this answer uses cached data.
        </p>
      )}

      {blocks.length === 0 ? (
        <p className="text-body-sm whitespace-pre-wrap text-on-ai">
          {response.answer.text}
        </p>
      ) : (
        blocks.map((block, index) => (
          <Block
            key={index}
            block={block}
            sources={sources}
            onSelectRef={selectRef}
          />
        ))
      )}

      {sources.length > 0 && (
        <div className="border-t border-indigo-500/30 pt-3">
          <p className="text-label text-on-ai-muted uppercase">Sources</p>
          <ol className="mt-2 space-y-1.5">
            {sources.map((source) => {
              const safeUrl =
                source.url && source.url.startsWith("https://")
                  ? source.url
                  : null;
              return (
                <li
                  key={source.ref}
                  id={sourceId(source.ref)}
                  className={cn(
                    "flex gap-2 rounded-md px-2 py-1.5 text-caption transition-colors duration-200",
                    highlight === source.ref
                      ? "bg-indigo-500/30 ring-1 ring-indigo-400"
                      : "bg-navy-800",
                  )}
                >
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-full border border-indigo-400/50 text-label text-indigo-200">
                    {source.ref}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                      {safeUrl ? (
                        <a
                          href={safeUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={cn(
                            "inline-flex items-center gap-1 font-medium text-indigo-200 underline-offset-2 hover:underline",
                            RING,
                          )}
                        >
                          {source.label}
                          <ExternalLink
                            aria-hidden
                            className="size-3"
                            strokeWidth={1.75}
                          />
                          <span className="sr-only">(opens in a new tab)</span>
                        </a>
                      ) : (
                        <span className="font-medium text-on-ai">
                          {source.label}
                        </span>
                      )}
                      <span className="rounded-full border border-indigo-500/40 px-1.5 text-label text-on-ai-muted">
                        {KIND_LABELS[source.kind] ?? source.kind}
                      </span>
                    </div>
                    {source.snippet && (
                      <p className="mt-0.5 line-clamp-2 text-on-ai-muted">
                        {source.snippet}
                      </p>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      )}

      {showFollowUps && followUps.length > 0 && (
        <div
          className="flex flex-wrap gap-2 pt-1"
          aria-label="Suggested follow-up questions"
          role="group"
        >
          {followUps.map((text) => (
            <button
              key={text}
              type="button"
              onClick={() => onFollowUp(text)}
              className={cn(
                "rounded-full border border-indigo-400/50 px-3 py-1 text-left text-caption text-indigo-200 hover:bg-indigo-500/25",
                RING,
              )}
            >
              {text}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
