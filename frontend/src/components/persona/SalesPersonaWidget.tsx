import { useQuery } from "@tanstack/react-query";
import { Bot, SendHorizontal, Sparkles, Trash2, X } from "lucide-react";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { matchPath, useLocation } from "react-router";
import { isApiError } from "../../api/client";
import { getOrganization } from "../../api/organizations";
import { sendPersonaMessage } from "../../api/persona";
import { cn } from "../../lib/cn";
import type {
  PersonaHistoryTurn,
  PersonaMode,
  PersonaResponse,
} from "../../types/api";
import { Skeleton } from "../ui/Skeleton";
import { PersonaAnswer } from "./PersonaAnswer";
import { PersonaScopeChooser, type PersonaScope } from "./PersonaScopeChooser";

const MAX_CHARS = 2000;
const MAX_STORED = 40;
const STORAGE_KEY = "asi.salesPersona.v2";
const RING =
  "focus-visible:ring-2 focus-visible:ring-focus-ring-ai focus-visible:outline-hidden";

type ChatMessage =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; response: PersonaResponse }
  | { id: string; role: "error"; text: string };

interface QuickAction {
  mode: Exclude<PersonaMode, "auto">;
  label: string;
  prompt: string;
  immediate?: boolean;
  generalOnly?: boolean;
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    mode: "daily_briefing",
    label: "Briefing",
    prompt:
      "Give me my daily briefing: what changed across my tracked organizations and what to look at first.",
    immediate: true,
  },
  {
    mode: "email",
    label: "Draft an email",
    prompt:
      "Draft a short outreach email to [contact name] at [organization]. What I want to say: [context].",
  },
  {
    mode: "call_prep",
    label: "Prep a call",
    prompt:
      "Help me prepare for a call with [organization]. Cover recent signals, likely priorities, and good questions to ask.",
  },
  {
    mode: "competitor",
    label: "Competitor update",
    generalOnly: true,
    prompt:
      "What have competitors or vendors been doing across my tracked organizations recently?",
  },
  {
    mode: "research",
    label: "Research an account",
    prompt:
      "Research [organization]: what does the collected evidence say about their assessment or technology plans?",
  },
];

let idCounter = 0;
function nextId(): string {
  idCounter += 1;
  return `${Date.now().toString(36)}${idCounter}`;
}

interface StoredConversation {
  scope: PersonaScope | null;
  messages: ChatMessage[];
}

function isScope(value: unknown): value is PersonaScope {
  if (typeof value !== "object" || value === null) return false;
  const v = value as {
    kind?: unknown;
    organizationId?: unknown;
    organizationName?: unknown;
  };
  if (v.kind === "general") return true;
  return (
    v.kind === "organization" &&
    typeof v.organizationId === "string" &&
    typeof v.organizationName === "string"
  );
}

function loadConversation(): StoredConversation {
  const empty: StoredConversation = { scope: null, messages: [] };
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return empty;
    const parsed = JSON.parse(raw) as {
      scope?: unknown;
      messages?: unknown;
    } | null;
    if (!parsed || !isScope(parsed.scope) || !Array.isArray(parsed.messages))
      return empty;
    const messages = (parsed.messages as unknown[]).filter(
      (m): m is ChatMessage =>
        typeof m === "object" &&
        m !== null &&
        typeof (m as ChatMessage).id === "string" &&
        ((m as ChatMessage).role === "user" ||
          (m as ChatMessage).role === "error" ||
          ((m as ChatMessage).role === "assistant" &&
            typeof (m as { response?: unknown }).response === "object")),
    );
    return { scope: parsed.scope, messages };
  } catch {
    return empty;
  }
}

function saveConversation(scope: PersonaScope | null, messages: ChatMessage[]) {
  try {
    window.sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ scope, messages: messages.slice(-MAX_STORED) }),
    );
  } catch {
    // Storage may be unavailable; the conversation still works in memory.
  }
}

function prefersReducedMotion(): boolean {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

export function SalesPersonaWidget() {
  const { pathname } = useLocation();
  const organizationId =
    matchPath("/organizations/:id/*", pathname)?.params.id ?? null;

  const [open, setOpen] = useState(false);
  const [initial] = useState(loadConversation);
  const [scope, setScope] = useState<PersonaScope | null>(initial.scope);
  const [messages, setMessages] = useState<ChatMessage[]>(initial.messages);
  // Organization id for which the user dismissed the route-based scope suggestion.
  const [dismissedOrgId, setDismissedOrgId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [mode, setMode] = useState<PersonaMode>("auto");
  const [pending, setPending] = useState(false);
  const [phase, setPhase] = useState<"searching" | "writing">("searching");

  const launcherRef = useRef<HTMLButtonElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const requestRef = useRef(0);
  const wasOpen = useRef(false);
  const scopeRef = useRef<PersonaScope | null>(scope);

  useEffect(() => {
    scopeRef.current = scope;
  }, [scope]);

  const suggestOrgId =
    open && !scope && organizationId && dismissedOrgId !== organizationId
      ? organizationId
      : null;
  const suggestion = useQuery({
    queryKey: ["organizations", "detail", suggestOrgId],
    queryFn: () => getOrganization(suggestOrgId as string),
    enabled: suggestOrgId !== null,
    staleTime: 60_000,
  });
  const suggestedName = suggestOrgId ? suggestion.data?.name : undefined;

  // Default suggestion: opening the panel on an organization page pre-selects that organization.
  useEffect(() => {
    if (suggestOrgId && suggestedName) {
      setScope({
        kind: "organization",
        organizationId: suggestOrgId,
        organizationName: suggestedName,
      });
    }
  }, [suggestOrgId, suggestedName]);
  const suggestionLoading = suggestOrgId !== null && suggestion.isLoading;

  useEffect(() => {
    saveConversation(scope, messages);
  }, [scope, messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      block: "end",
      behavior: prefersReducedMotion() ? "auto" : "smooth",
    });
  }, [messages, pending, open]);

  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 128)}px`;
  }, [draft, open]);

  function closePanel() {
    setOpen(false);
    setDismissedOrgId(null);
  }

  // Focus management: move focus into the panel on open, back to the launcher on close.
  useEffect(() => {
    if (open) {
      textareaRef.current?.focus();
    } else if (wasOpen.current) {
      launcherRef.current?.focus();
    }
    wasOpen.current = open;
  }, [open, scope]);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        setDismissedOrgId(null);
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  // Other pages can open the panel in a given mode with a prefilled (unsent) prompt.
  useEffect(() => {
    function onOpen(event: Event) {
      const detail = (
        event as CustomEvent<{ mode?: PersonaMode; prompt?: string }>
      ).detail;
      setOpen(true);
      if (scopeRef.current?.kind !== "general") {
        // Outside-data requests use general scope; a different scope starts a new conversation.
        requestRef.current += 1;
        setMessages([]);
        setPending(false);
        setScope({ kind: "general" });
      }
      if (detail?.mode) setMode(detail.mode);
      if (typeof detail?.prompt === "string")
        setDraft(detail.prompt.slice(0, MAX_CHARS));
      window.requestAnimationFrame(() => {
        const el = textareaRef.current;
        if (!el) return;
        el.focus();
        el.setSelectionRange(el.value.length, el.value.length);
      });
    }
    window.addEventListener("persona:open", onOpen);
    return () => window.removeEventListener("persona:open", onOpen);
  }, []);

  const send = useCallback(
    async (text: string, sendMode: PersonaMode) => {
      const message = text.trim().slice(0, MAX_CHARS);
      if (!message || pending || !scope) return;

      const history: PersonaHistoryTurn[] = messages
        .flatMap((m): PersonaHistoryTurn[] => {
          if (m.role === "user")
            return [{ role: "user" as const, text: m.text }];
          if (m.role === "assistant") {
            return [
              { role: "assistant" as const, text: m.response.answer.text },
            ];
          }
          return [];
        })
        .filter((turn) => turn.text.trim().length > 0)
        .slice(-6);

      const requestId = requestRef.current + 1;
      requestRef.current = requestId;

      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: "user", text: message },
      ]);
      setDraft("");
      setMode("auto");
      setPending(true);
      setPhase("searching");
      const phaseTimer = window.setTimeout(() => setPhase("writing"), 1200);

      try {
        const response = await sendPersonaMessage({
          message,
          history,
          organization_id:
            scope?.kind === "organization" ? scope.organizationId : null,
          mode: sendMode,
          scope: scope?.kind === "organization" ? "organization" : "general",
        });
        if (requestRef.current !== requestId) return;
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: "assistant", response },
        ]);
      } catch (error) {
        if (requestRef.current !== requestId) return;
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "error",
            text: isApiError(error)
              ? error.message
              : "Sales Persona could not answer. Try again.",
          },
        ]);
      } finally {
        window.clearTimeout(phaseTimer);
        if (requestRef.current === requestId) setPending(false);
      }
    },
    [messages, scope, pending],
  );

  function resetConversation() {
    requestRef.current += 1;
    setMessages([]);
    setDraft("");
    setMode("auto");
    setPending(false);
  }

  function selectScope(next: PersonaScope) {
    resetConversation();
    setScope(next);
  }

  // Clear and Change both return to the scope step and start a new conversation.
  function backToScopeStep() {
    resetConversation();
    setDismissedOrgId(organizationId);
    setScope(null);
  }

  function onQuickAction(action: QuickAction) {
    if (pending) return;
    if (action.immediate) {
      void send(action.prompt, action.mode);
      return;
    }
    if (mode === action.mode) {
      setMode("auto");
      return;
    }
    setMode(action.mode);
    setDraft(action.prompt);
    window.requestAnimationFrame(() => {
      const el = textareaRef.current;
      if (!el) return;
      el.focus();
      el.setSelectionRange(el.value.length, el.value.length);
    });
  }

  const lastAssistantId = [...messages]
    .reverse()
    .find((m) => m.role === "assistant")?.id;
  const lastMessageId = messages[messages.length - 1]?.id;
  const canSend = draft.trim().length > 0 && !pending;

  return (
    <>
      {open && (
        <section
          role="dialog"
          aria-label="Sales Persona"
          className={cn(
            // Full height: pinned to the top and to just above the launcher, so the conversation
            // area grows to use the whole screen instead of a 70vh cap.
            "fixed inset-x-0 top-0 bottom-22 z-50 flex flex-col overflow-hidden",
            "border border-indigo-500/40 bg-surface-ai text-on-ai shadow-lg",
            "sm:inset-x-auto sm:top-4 sm:right-6 sm:w-95 sm:rounded-xl",
          )}
        >
          <header className="flex items-start justify-between gap-2 border-b border-indigo-500/30 px-4 py-3">
            <div>
              <h2 className="flex items-center gap-1.5 text-h3 text-on-ai">
                <Sparkles
                  aria-hidden
                  className="size-4 text-indigo-400"
                  strokeWidth={1.75}
                />
                Sales Persona
              </h2>
              <p className="text-caption text-on-ai-muted">
                Your daily sales copilot
              </p>
            </div>
            <div className="flex items-center gap-1">
              {messages.length > 0 && (
                <button
                  type="button"
                  onClick={backToScopeStep}
                  className={cn(
                    "inline-flex h-8 items-center gap-1 rounded-md px-2 text-caption font-medium text-indigo-200 hover:bg-indigo-500/25",
                    RING,
                  )}
                >
                  <Trash2 aria-hidden className="size-3.5" strokeWidth={1.75} />
                  Clear
                </button>
              )}
              <button
                type="button"
                onClick={closePanel}
                aria-label="Close Sales Persona"
                className={cn(
                  "inline-flex size-8 items-center justify-center rounded-md text-indigo-200 hover:bg-indigo-500/25",
                  RING,
                )}
              >
                <X aria-hidden className="size-4" strokeWidth={1.75} />
              </button>
            </div>
          </header>

          {scope && (
            <div className="flex items-center justify-between gap-2 border-b border-indigo-500/30 px-4 py-1.5">
              <p className="min-w-0 truncate text-caption text-on-ai-muted">
                {scope.kind === "organization" ? (
                  <>
                    Working only with data about{" "}
                    <strong className="font-semibold text-on-ai">
                      {scope.organizationName}
                    </strong>
                  </>
                ) : (
                  "General and outside data"
                )}
              </p>
              <button
                type="button"
                onClick={backToScopeStep}
                className={cn(
                  "inline-flex h-7 shrink-0 items-center rounded-md px-2 text-caption font-medium text-indigo-200 hover:bg-indigo-500/25",
                  RING,
                )}
              >
                Change
              </button>
            </div>
          )}

          <div className="min-h-40 flex-1 space-y-4 overflow-y-auto px-4 py-4">
            {!scope && suggestionLoading && (
              <div
                className="space-y-2"
                role="status"
                aria-label="Loading organization"
              >
                <Skeleton tone="dark" className="h-5 w-3/4" />
                <Skeleton tone="dark" className="h-16 w-full" />
              </div>
            )}

            {!scope && !suggestionLoading && (
              <PersonaScopeChooser onSelect={selectScope} />
            )}

            {scope && messages.length === 0 && !pending && (
              <p className="text-body-sm text-on-ai-muted">
                {scope.kind === "organization"
                  ? `Ask about ${scope.organizationName}, or pick a quick action below. Answers come only from its collected evidence, and drafts are never sent.`
                  : "Ask about your tracked organizations, or pick a quick action below. Answers come from collected evidence, and drafts are never sent."}
              </p>
            )}

            {messages.map((m) => {
              if (m.role === "user") {
                return (
                  <div key={m.id} className="flex justify-end">
                    <div className="max-w-[85%] rounded-lg rounded-br-sm bg-navy-50 px-3 py-2 text-body-sm whitespace-pre-wrap text-navy-900">
                      {m.text}
                    </div>
                  </div>
                );
              }
              if (m.role === "error") {
                return (
                  <p
                    key={m.id}
                    role="alert"
                    className="text-body-sm text-red-100"
                  >
                    {m.text}
                  </p>
                );
              }
              return (
                <PersonaAnswer
                  key={m.id}
                  messageId={m.id}
                  response={m.response}
                  showFollowUps={
                    !pending &&
                    m.id === lastAssistantId &&
                    m.id === lastMessageId
                  }
                  onFollowUp={(text) => void send(text, "auto")}
                />
              );
            })}

            <div aria-live="polite" role="status">
              {pending && (
                <p className="flex items-center gap-2 text-body-sm text-indigo-300">
                  <span className="inline-flex gap-1" aria-hidden>
                    <span className="size-1.5 animate-pulse rounded-full bg-indigo-400" />
                    <span className="size-1.5 animate-pulse rounded-full bg-indigo-400 [animation-delay:150ms]" />
                    <span className="size-1.5 animate-pulse rounded-full bg-indigo-400 [animation-delay:300ms]" />
                  </span>
                  {phase === "searching"
                    ? "Searching stored evidence…"
                    : "Writing…"}
                </p>
              )}
            </div>
            <div ref={bottomRef} />
          </div>

          {scope && (
            <div className="border-t border-indigo-500/30 p-3">
              <div
                className="mb-2 flex flex-wrap gap-1.5"
                role="group"
                aria-label="Quick actions"
              >
                {QUICK_ACTIONS.filter(
                  (a) => !(scope.kind === "organization" && a.generalOnly),
                ).map((action) => (
                  <button
                    key={action.mode}
                    type="button"
                    disabled={pending}
                    aria-pressed={!action.immediate && mode === action.mode}
                    onClick={() => onQuickAction(action)}
                    className={cn(
                      "rounded-full border px-2.5 py-1 text-caption transition-colors",
                      "disabled:cursor-not-allowed disabled:opacity-50",
                      !action.immediate && mode === action.mode
                        ? "border-indigo-400 bg-indigo-500/30 text-on-ai"
                        : "border-indigo-400/50 text-indigo-200 hover:bg-indigo-500/25",
                      RING,
                    )}
                  >
                    {action.label}
                  </button>
                ))}
              </div>

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void send(draft, mode);
                }}
              >
                <div className="flex items-end gap-2">
                  <textarea
                    ref={textareaRef}
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (
                        e.key === "Enter" &&
                        !e.shiftKey &&
                        !e.nativeEvent.isComposing
                      ) {
                        e.preventDefault();
                        void send(draft, mode);
                      }
                    }}
                    rows={1}
                    maxLength={MAX_CHARS}
                    aria-label="Message to Sales Persona"
                    placeholder={
                      scope.kind === "organization"
                        ? `Ask about ${scope.organizationName}…`
                        : "Ask anything about your accounts or the market…"
                    }
                    className="max-h-32 min-h-10 flex-1 resize-none rounded-md border border-default bg-surface px-3 py-2 text-body text-primary placeholder:text-muted focus-visible:ring-2 focus-visible:ring-focus-ring-ai focus-visible:outline-hidden"
                  />
                  <button
                    type="submit"
                    disabled={!canSend}
                    aria-label="Send message"
                    className={cn(
                      "inline-flex size-10 shrink-0 items-center justify-center rounded-md bg-indigo-600 text-inverse hover:bg-indigo-700",
                      "disabled:cursor-not-allowed disabled:opacity-50",
                      RING,
                    )}
                  >
                    <SendHorizontal
                      aria-hidden
                      className="size-5"
                      strokeWidth={1.75}
                    />
                  </button>
                </div>
                <p className="mt-1 flex justify-between text-caption text-on-ai-muted">
                  <span>Enter to send, Shift+Enter for a new line</span>
                  {draft.length > MAX_CHARS - 200 && (
                    <span aria-live="polite">
                      {draft.length}/{MAX_CHARS}
                    </span>
                  )}
                </p>
              </form>
            </div>
          )}
        </section>
      )}

      <button
        ref={launcherRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close Sales Persona" : "Open Sales Persona"}
        aria-expanded={open}
        className={cn(
          "fixed right-6 bottom-6 z-50 flex size-14 items-center justify-center rounded-full",
          "bg-indigo-600 text-inverse shadow-lg transition-colors duration-120 hover:bg-indigo-700",
          "focus-visible:ring-2 focus-visible:ring-focus-ring-ai focus-visible:ring-offset-2 focus-visible:outline-hidden",
        )}
      >
        {open ? (
          <X aria-hidden className="size-6" strokeWidth={1.75} />
        ) : (
          <Bot aria-hidden className="size-6" strokeWidth={1.75} />
        )}
      </button>
    </>
  );
}
