import { useMemo, useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { X, ChevronDown, Search } from "lucide-react";
import { useStore, timeAgo } from "./store";
import {
  DECISION_COLOR,
  type AgentDecision,
  type AgentLog,
} from "./mockData";

const FILTERS: { label: string; value: "ALL" | AgentDecision }[] = [
  { label: "All", value: "ALL" },
  { label: "Accepted", value: "ACCEPTED" },
  { label: "Rejected", value: "REJECTED" },
];

export default function AgentLogsPanel() {
  const open = useStore((s) => s.agentLogsOpen);
  const setOpen = useStore((s) => s.setAgentLogsOpen);
  const logs = useStore((s) => s.agentLogs);
  const selectIncident = useStore((s) => s.selectIncident);

  const [decisionFilter, setDecisionFilter] = useState<"ALL" | AgentDecision>(
    "ALL",
  );
  const [searchTerm, setSearchTerm] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const baseFiltered = useMemo(
    () => logs.filter((log) => matchesSearch(log, searchTerm)),
    [logs, searchTerm],
  );

  const counts = useMemo(() => {
    const c: Record<string, number> = { ALL: baseFiltered.length };
    for (const log of baseFiltered) {
      c[log.decision] = (c[log.decision] ?? 0) + 1;
    }
    return c;
  }, [baseFiltered]);

  const filtered = useMemo(
    () =>
      decisionFilter === "ALL"
        ? baseFiltered
        : baseFiltered.filter((log) => log.decision === decisionFilter),
    [baseFiltered, decisionFilter],
  );

  useEffect(() => {
    if (openId && !filtered.some((log) => log.id === openId)) {
      setOpenId(null);
    }
  }, [filtered, openId]);

  if (!mounted) return null;

  return createPortal(
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="fixed inset-0 z-[1150] bg-black/50 backdrop-blur-[2px]"
            onClick={() => setOpen(false)}
          />

          <motion.div
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 240 }}
            className="fixed top-0 left-0 bottom-0 z-[1200] w-full sm:w-[470px] flex flex-col overflow-hidden"
            style={{
              background: "rgba(8, 11, 18, 0.78)",
              backdropFilter: "blur(40px) saturate(150%)",
              WebkitBackdropFilter: "blur(40px) saturate(150%)",
              border: "1px solid rgba(255,255,255,0.06)",
              boxShadow:
                "0 24px 60px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.02) inset, 0 1px 0 rgba(255,255,255,0.04) inset",
            }}
          >
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0"
              style={{
                background:
                  "radial-gradient(120% 60% at 0% 0%, rgba(59,130,246,0.10), transparent 55%), radial-gradient(80% 40% at 100% 100%, rgba(20,184,166,0.08), transparent 60%)",
              }}
            />

            <div className="relative px-5 py-4 border-b border-white/[0.08] shrink-0 bg-[#0b1220]/80 backdrop-blur-xl">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-base font-semibold text-white tracking-tight">
                    Agent Logs
                  </div>
                  <div className="text-[11px] text-slate-300 mt-0.5 font-mono uppercase tracking-wider">
                    {filtered.length} of {logs.length} reports
                  </div>
                </div>
                <button
                  onClick={() => setOpen(false)}
                  className="p-1.5 rounded-md text-slate-300 hover:text-white hover:bg-white/[0.08] transition-colors"
                  aria-label="Close"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="relative px-5 py-3 border-b border-white/[0.08] shrink-0 bg-[#0b1220]/70 backdrop-blur-xl space-y-2.5">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search id, source, reason, or message text"
                  className="w-full h-8 pl-8 pr-2 text-xs text-slate-100 placeholder:text-slate-400 bg-white/[0.04] border border-white/[0.08] rounded-md focus:outline-none focus:ring-1 focus:ring-blue-400/50 focus:border-blue-300/40"
                />
              </div>

              <div className="flex gap-1.5 overflow-x-auto safewatch-scroll">
                {FILTERS.map((filter) => {
                  const active = decisionFilter === filter.value;
                  const count = counts[filter.value] ?? 0;
                  const accent =
                    filter.value === "ALL" ? "#93c5fd" : DECISION_COLOR[filter.value];

                  return (
                    <button
                      key={filter.value}
                      onClick={() => setDecisionFilter(filter.value)}
                      className="text-xs px-3 py-1 rounded-full whitespace-nowrap transition-all flex items-center gap-1.5 border"
                      style={
                        active
                          ? {
                              backgroundColor: `${accent}22`,
                              color: accent,
                              borderColor: `${accent}66`,
                              boxShadow: `0 0 0 1px ${accent}26, 0 6px 16px ${accent}1f`,
                            }
                          : {
                              backgroundColor: "rgba(255,255,255,0.03)",
                              color: "#cbd5e1",
                              borderColor: "rgba(255,255,255,0.08)",
                            }
                      }
                    >
                      <span>{filter.label}</span>
                      <span
                        className="text-[10px] tabular-nums"
                        style={{ color: active ? accent : "#94a3b8" }}
                      >
                        {count}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="relative flex-1 overflow-y-auto safewatch-scroll p-3 space-y-2">
              {filtered.length === 0 ? (
                <div className="text-center text-slate-300 text-sm py-12">
                  No reports match these filters.
                </div>
              ) : (
                filtered.map((log) => (
                  <LogCard
                    key={log.id}
                    log={log}
                    expanded={openId === log.id}
                    onToggle={() =>
                      setOpenId((prev) => (prev === log.id ? null : log.id))
                    }
                    onJumpToIncident={(id) => {
                      selectIncident(id);
                      setOpen(false);
                    }}
                  />
                ))
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>,
    document.body,
  );
}

function LogCard({
  log,
  expanded,
  onToggle,
  onJumpToIncident,
}: {
  log: AgentLog;
  expanded: boolean;
  onToggle: () => void;
  onJumpToIncident: (id: string) => void;
}) {
  const color = DECISION_COLOR[log.decision];

  return (
    <div
      className="relative rounded-xl overflow-hidden transition-all"
      style={{
        background:
          "linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)",
        border: "1px solid rgba(255,255,255,0.08)",
        boxShadow: expanded
          ? `0 0 0 1px ${color}33, 0 12px 28px rgba(0,0,0,0.35), 0 0 24px ${color}1f`
          : "0 4px 12px rgba(0,0,0,0.18)",
      }}
    >
      <div
        aria-hidden
        className="absolute left-0 top-0 bottom-0 w-[3px]"
        style={{ background: `linear-gradient(180deg, ${color}cc, ${color}33)` }}
      />

      <button
        onClick={onToggle}
        className="w-full text-left p-3.5 pl-4 hover:bg-white/[0.03] transition-colors"
      >
        <div className="flex items-center justify-between mb-2">
          <span
            className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded"
            style={{
              backgroundColor: `${color}22`,
              color,
              border: `1px solid ${color}40`,
            }}
          >
            {log.decision}
          </span>
          <ChevronDown
            className={`w-3.5 h-3.5 shrink-0 transition-transform duration-200 text-slate-300 ${
              expanded ? "rotate-180" : ""
            }`}
          />
        </div>

        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-slate-300 font-mono mb-2">
          {log.incident_id && (
            <span className="px-1.5 py-0.5 rounded bg-white/[0.04] border border-white/[0.08]">
              {log.incident_id}
            </span>
          )}
          <span>{log.source}</span>
          <span className="text-slate-500">|</span>
          <span>{timeAgo(log.scraped_at)}</span>
          <span className="text-slate-500">({formatDateTime(log.scraped_at)})</span>
        </div>

        <p className="text-sm text-slate-100 leading-relaxed line-clamp-3 mb-2.5">
          {log.raw_text || "No raw report text."}
        </p>

        <div className="flex items-center justify-between text-[11px] text-slate-300">
          <span className="truncate pr-2">
            {log.messages.length} messages | {log.decision_reason ? "has reason" : "no reason"}
          </span>
          <span className="text-slate-400">Expand details</span>
        </div>
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="overflow-hidden"
            style={{ borderTop: `1px solid ${color}22` }}
          >
            <div className="px-4 py-3.5 space-y-3">
              {log.decision_reason && (
                <div
                  className="rounded-md p-2.5 text-xs leading-relaxed border"
                  style={{
                    backgroundColor: `${color}15`,
                    borderColor: `${color}3d`,
                    color: `${color}e6`,
                  }}
                >
                  {log.decision_reason}
                </div>
              )}

              {log.messages.map((message, index) => (
                <div
                  key={`${log.id}-message-${index}`}
                  className="rounded-md border border-white/[0.08] bg-black/20 p-2.5 space-y-1.5"
                >
                  <div className="text-[10px] font-mono text-slate-300 uppercase tracking-wide">
                    {message.agent}
                  </div>
                  <MessageContent content={message.content} />
                </div>
              ))}

              {log.incident_id && (
                <button
                  onClick={() => onJumpToIncident(log.incident_id!)}
                  className="text-xs font-medium transition-opacity hover:opacity-80"
                  style={{ color }}
                >
                  View incident {log.incident_id}
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function MessageContent({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);
  const lines = useMemo(
    () =>
      content
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean),
    [content],
  );

  useEffect(() => {
    setExpanded(false);
  }, [content]);

  if (!lines.length) {
    return <div className="text-xs text-slate-500">No message content.</div>;
  }

  const hasOverflow = lines.length > 5;
  const visibleLines = expanded ? lines : lines.slice(0, 5);

  return (
    <div className="space-y-1">
      {visibleLines.map((rawLine, index) => {
        const line = normalizeMessageLine(rawLine);
        const tone = getLineTone(line);
        return (
          <p
            key={`line-${index}`}
            className={`text-xs leading-relaxed break-words ${tone.className}`}
          >
            {line}
          </p>
        );
      })}

      {hasOverflow && (
        <button
          onClick={() => setExpanded((prev) => !prev)}
          className="text-[11px] font-mono text-sky-300 hover:text-sky-200 transition-colors"
        >
          {expanded ? "Show less" : `Show ${lines.length - 5} more lines`}
        </button>
      )}
    </div>
  );
}

function matchesSearch(log: AgentLog, searchTerm: string): boolean {
  const query = searchTerm.trim().toLowerCase();
  if (!query) return true;

  const haystacks = [
    log.id,
    log.incident_id ?? "",
    log.source,
    log.decision,
    log.raw_text ?? "",
    log.decision_reason ?? "",
    ...log.messages.map((message) => `${message.agent} ${message.content}`),
  ];

  return haystacks.some((value) => value.toLowerCase().includes(query));
}

function normalizeMessageLine(line: string): string {
  return line
    .replace(/^\u00e2\u0153\u201c\s*/i, "CHECK: ")
    .replace(/^\u00e2\u0153\u2014\s*/i, "FLAG: ")
    .replace(/^\u2713\s*/i, "CHECK: ")
    .replace(/^\u2717\s*/i, "FLAG: ")
    .replace(/\u00c2\u00b7/g, " | ");
}

function getLineTone(line: string): { className: string } {
  const lower = line.toLowerCase();
  if (lower.startsWith("check:")) return { className: "text-emerald-300" };
  if (lower.startsWith("flag:")) return { className: "text-rose-300" };
  if (lower.startsWith("scores:") || lower.startsWith("used:")) {
    return { className: "text-sky-200/90 font-mono" };
  }
  return { className: "text-slate-200" };
}

function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "Unknown date";
  return date.toLocaleString("en-SG", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
