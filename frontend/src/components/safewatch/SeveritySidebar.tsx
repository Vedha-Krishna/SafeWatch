import React, { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  Clock,
  ChevronDown,
  ChevronUp,
  Flame,
} from "lucide-react";
import { useFilteredIncidents, useStore, timeAgo } from "./store";
import {
  SEVERITY_COLOR,
  SEVERITY_LABEL,
  type Incident,
  type Severity,
} from "./mockData";

const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

export default function SeveritySidebar() {
  const filtered = useFilteredIncidents();
  const {
    severityFilter,
    setSeverityFilter,
    selectIncident,
    flyTo,
    sidebarCollapsed: collapsed,
    toggleSidebar,
  } = useStore();

  const visibleIncidents = useMemo(() => {
    let list = filtered;
    if (severityFilter === "critical_only") {
      list = list.filter((i) => i.severity === "critical");
    } else if (severityFilter === "clusters_only") {
      list = list.filter((i) => i.cluster_id !== null);
    }
    return [...list].sort((a, b) => {
      const s = SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity];
      if (s !== 0) return s;
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });
  }, [filtered, severityFilter]);

  return (
    <aside className="w-full h-full flex flex-col">
      {/* Compact header */}
      <button
        onClick={toggleSidebar}
        className="px-4 py-3 flex items-center justify-between w-full hover:bg-white/[0.03] transition-colors"
      >
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-xs font-bold text-white font-mono uppercase tracking-wider">
            Incidents
          </span>
          <span className="text-[10px] font-mono text-slate-500 tabular-nums">
            {visibleIncidents.length}
          </span>
        </div>
        {collapsed ? (
          <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
        ) : (
          <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
        )}
      </button>

      {!collapsed && (
        <>
          {/* Filter chips */}
          <div className="flex gap-1 px-4 pb-3">
            {(
              [
                ["all", "All"],
                ["critical_only", "Critical"],
                ["clusters_only", "Clusters"],
              ] as const
            ).map(([v, label]) => (
              <button
                key={v}
                onClick={() => setSeverityFilter(v)}
                className={`text-[10px] font-mono uppercase px-2.5 py-1 rounded-full transition-colors ${
                  severityFilter === v
                    ? "bg-white/10 text-white"
                    : "bg-transparent text-slate-500 hover:text-slate-300"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Cards list — minimal */}
          <div className="flex-1 overflow-y-auto safewatch-scroll px-3 pb-3 space-y-1.5">
            <AnimatePresence mode="popLayout">
              {visibleIncidents.map((inc) => (
                <IncidentCard
                  key={inc.id}
                  incident={inc}
                  onClick={() => {
                    selectIncident(inc.id);
                    flyTo(inc.location.lat, inc.location.lng, 16);
                  }}
                />
              ))}
            </AnimatePresence>
            {visibleIncidents.length === 0 && (
              <div className="text-center text-xs text-slate-500 py-8 font-mono">
                No incidents match.
              </div>
            )}
          </div>
        </>
      )}
    </aside>
  );
}

function IncidentCard({
  incident,
  onClick,
}: {
  incident: Incident;
  onClick: () => void;
}) {
  const color = SEVERITY_COLOR[incident.severity];
  return (
    <motion.button
      layout
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: 8 }}
      onClick={onClick}
      className="w-full text-left rounded-lg p-2.5 hover:bg-white/[0.04] transition-colors block group flex items-start gap-2.5"
    >
      <span
        className="w-2 h-2 rounded-full mt-1.5 shrink-0"
        style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}` }}
      />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <div className="text-sm font-medium text-white group-hover:text-blue-300 transition-colors truncate">
            {incident.title}
          </div>
          {incident.cluster_id && (
            <Flame className="w-3 h-3 text-orange-400 shrink-0" />
          )}
        </div>
        <div className="text-[11px] text-slate-300 font-mono truncate">
          {incident.location.area}
        </div>
        <div className="text-[10px] text-slate-400 font-mono flex items-center gap-1 mt-0.5">
          <Clock className="w-2.5 h-2.5" />
          {timeAgo(incident.timestamp)}
          <span className="ml-auto font-bold" style={{ color }}>
            {SEVERITY_LABEL[incident.severity]}
          </span>
        </div>
      </div>
    </motion.button>
  );
}
