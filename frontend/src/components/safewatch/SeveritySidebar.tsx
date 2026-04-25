import { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  Clock,
  ChevronDown,
  ChevronUp,
  MapPinOff,
} from "lucide-react";
import { getAreaCenter, useFilteredIncidents, useStore, timeAgo } from "./store";
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

const NO_LOCATION_COLOR = "#f59e0b";
const DASHBOARD_FLY_ZOOM = 14;

function toAreaLevelCoord(value: number): number {
  // ~1 km precision (privacy-friendly, less "exact pin" feel)
  return Math.round(value * 100) / 100;
}

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

  const sorted = useMemo(
    () =>
      [...filtered].sort((a, b) => {
        const s = SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity];
        if (s !== 0) return s;
        return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
      }),
    [filtered],
  );

  const visibleIncidents = useMemo(() => {
    if (severityFilter === "critical_only")
      return sorted.filter((i) => i.severity === "critical");
    if (severityFilter === "no_location")
      return sorted.filter((i) => !i.hasMapLocation);
    return sorted.filter((i) => i.hasMapLocation);
  }, [sorted, severityFilter]);

  const noLocationCount = useMemo(
    () => sorted.filter((i) => !i.hasMapLocation).length,
    [sorted],
  );
  const mappedLocationCount = useMemo(
    () => sorted.filter((i) => i.hasMapLocation).length,
    [sorted],
  );
  const criticalCount = useMemo(
    () => sorted.filter((i) => i.severity === "critical").length,
    [sorted],
  );

  return (
    <aside className="w-full h-full flex flex-col">
      {/* Header */}
      <button
        onClick={toggleSidebar}
        className="px-4 py-3.5 sm:py-3 flex items-center justify-between w-full hover:bg-white/[0.03] transition-colors"
      >
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-300" />
          <span className="text-xs font-bold text-white font-mono uppercase tracking-wider">
            Incidents
          </span>
          <span className="text-[10px] font-mono text-slate-300 tabular-nums">
            {sorted.length}
          </span>
        </div>
        {collapsed ? (
          <ChevronDown className="w-3.5 h-3.5 text-slate-300" />
        ) : (
          <ChevronUp className="w-3.5 h-3.5 text-slate-300" />
        )}
      </button>

      {!collapsed && (
        <>
          {/* Filter chips */}
          <div className="flex flex-nowrap items-center gap-1 px-3 pb-3 overflow-x-auto safewatch-scroll">
            {(
              [
                ["all",           "All",      mappedLocationCount],
                ["critical_only", "Critical", criticalCount],
              ] as const
            ).map(([v, label, count]) => (
              <button
                key={v}
                onClick={() => setSeverityFilter(v)}
                className={`h-8 shrink-0 text-[10px] font-mono uppercase px-2.5 rounded-full transition-colors whitespace-nowrap ${
                  severityFilter === v
                    ? "bg-white/12 text-blue-100 border border-blue-300/25"
                    : "bg-transparent text-slate-300 hover:text-blue-200"
                }`}
              >
                {label}
                <span
                  className={`ml-1 tabular-nums ${
                    severityFilter === v ? "text-blue-200" : "text-slate-400"
                  }`}
                >
                  {count}
                </span>
              </button>
            ))}

            {/* No Location chip — amber accent */}
            <button
              onClick={() => setSeverityFilter("no_location")}
              className={`h-8 shrink-0 flex items-center gap-1 text-[10px] font-mono uppercase px-2.5 rounded-full transition-colors whitespace-nowrap ${
                severityFilter === "no_location"
                  ? "text-amber-300 bg-amber-500/20 border border-amber-500/40"
                  : "text-slate-300 hover:text-amber-300 bg-transparent"
              }`}
            >
              <MapPinOff className="w-3 h-3" />
              No Location
              {noLocationCount > 0 && (
                <span
                  className={`ml-0.5 tabular-nums ${
                    severityFilter === "no_location"
                      ? "text-amber-400"
                      : "text-slate-400"
                  }`}
                >
                  {noLocationCount}
                </span>
              )}
            </button>
          </div>

          {/* No Location banner when filter is active */}
          {severityFilter === "no_location" && (
            <div className="mx-3 mb-2 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/25 flex items-center gap-2">
              <MapPinOff className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              <span className="text-[10px] font-mono text-amber-300">
                {noLocationCount} incident{noLocationCount !== 1 ? "s" : ""} with no mapped location
              </span>
            </div>
          )}

          {/* Cards list */}
          <div className="flex-1 overflow-y-auto safewatch-scroll px-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:pb-3 space-y-1.5">
            <AnimatePresence mode="popLayout">
              {visibleIncidents.map((inc) => (
                <IncidentCard
                  key={inc.id}
                  incident={inc}
                  noLocation={!inc.hasMapLocation}
                  onClick={() => {
                    selectIncident(inc.id);
                    const areaCenter = getAreaCenter(inc.location.area);
                    if (areaCenter) {
                      flyTo(
                        toAreaLevelCoord(areaCenter[0]),
                        toAreaLevelCoord(areaCenter[1]),
                        DASHBOARD_FLY_ZOOM,
                      );
                    }
                  }}
                />
              ))}
            </AnimatePresence>
            {visibleIncidents.length === 0 && (
              <div className="text-center text-xs text-slate-300 py-8 font-mono">
                {severityFilter === "critical_only"
                  ? "No critical incidents in the current filters."
                  : "No incidents match."}
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
  noLocation,
  onClick,
}: {
  incident: Incident;
  noLocation: boolean;
  onClick: () => void;
}) {
  const markerColor = noLocation ? NO_LOCATION_COLOR : SEVERITY_COLOR[incident.severity];
  const severityColor = SEVERITY_COLOR[incident.severity];
  return (
    <motion.button
      layout
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: 8 }}
      onClick={onClick}
      className="w-full text-left rounded-lg p-3 sm:p-2.5 hover:bg-white/[0.04] active:bg-white/[0.07] transition-colors block group flex items-start gap-2.5"
    >
      <span
        className="w-2 h-2 rounded-full mt-1.5 shrink-0"
        style={{
          backgroundColor: markerColor,
          boxShadow: `0 0 8px ${markerColor}`,
        }}
      />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-white group-hover:text-blue-300 transition-colors line-clamp-2 sm:truncate">
          {incident.title}
        </div>
        <div className="flex items-center gap-1 text-[11px] font-mono truncate">
          {noLocation ? (
            <>
              <MapPinOff className="w-2.5 h-2.5 text-amber-400 shrink-0" />
              <span className="text-amber-400/80">No location</span>
            </>
          ) : (
            <span className="text-slate-300">{incident.location.area}</span>
          )}
        </div>
        <div className="text-[10px] text-slate-400 font-mono flex items-center gap-1 mt-0.5">
          <Clock className="w-2.5 h-2.5" />
          {timeAgo(incident.timestamp)}
          <span className="ml-auto font-bold" style={{ color: severityColor }}>
            {SEVERITY_LABEL[incident.severity]}
          </span>
        </div>
      </div>
    </motion.button>
  );
}
