import React from "react";
import { Shield } from "lucide-react";
import { useFilteredIncidents, useStore, severityCounts } from "./store";
import type { CrimeTypeFilter, TimeRangeFilter } from "./store";

const CRIME_OPTIONS: { value: CrimeTypeFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "snatch_theft", label: "Snatch theft" },
  { value: "bike_theft", label: "Bike theft" },
  { value: "scam", label: "Scams" },
  { value: "vandalism", label: "Vandalism" },
  { value: "harassment", label: "Harassment" },
  { value: "theft", label: "Theft" },
  { value: "loan_shark", label: "Loan shark" },
];

const TIME_OPTIONS: { value: TimeRangeFilter; label: string }[] = [
  { value: "24h", label: "24h" },
  { value: "7d", label: "7d" },
  { value: "30d", label: "30d" },
  { value: "90d", label: "90d" },
];

export default function Header() {
  const filtered = useFilteredIncidents();
  const counts = severityCounts(filtered);
  const { crimeType, timeRange, setCrimeType, setTimeRange } = useStore();
  const total = filtered.length;

  return (
    <header className="absolute top-3 left-3 right-3 sm:top-4 sm:left-4 sm:right-4 z-[1100] flex flex-wrap items-center gap-2 sm:gap-3 pointer-events-none">
      {/* Logo / brand pill */}
      <div className="safewatch-glass-panel rounded-full pl-1.5 pr-3 sm:pr-4 py-1.5 flex items-center gap-2 pointer-events-auto h-9 shrink-0">
        <div className="w-6 h-6 rounded-full bg-blue-500/15 border border-blue-500/30 flex items-center justify-center shrink-0">
          <Shield className="w-3 h-3 text-blue-400" />
        </div>
        <div className="flex flex-col leading-none gap-0.5">
          <span className="text-[12px] font-bold text-white tracking-wide">
            SafeWatch
          </span>
          <span className="hidden sm:inline text-[8px] text-slate-500 font-mono uppercase tracking-widest">
            Singapore
          </span>
        </div>
      </div>

      {/* Counts pill */}
      <div className="safewatch-glass-panel rounded-full px-3 sm:px-4 flex items-center gap-2 sm:gap-3 pointer-events-auto h-9 shrink-0">
        <span className="hidden sm:inline text-[10px] font-mono uppercase text-slate-500">
          Active
        </span>
        <span className="text-sm font-bold text-white tabular-nums">
          {total}
        </span>
        <span className="w-px h-4 bg-white/10" />
        <Dot color="#ef4444" count={counts.critical} />
        <Dot color="#f97316" count={counts.high} />
        <Dot color="#eab308" count={counts.medium} />
        <Dot color="#22c55e" count={counts.low} />
      </div>

      {/* Filters pushed to right on wide, wrap to next line on narrow */}
      <div className="ml-auto safewatch-glass-panel rounded-full p-0.5 sm:p-1 flex items-center gap-0.5 sm:gap-1 pointer-events-auto h-8 sm:h-9 max-w-full">
        <div className="min-w-0 flex-1 sm:flex-none">
          <Select
            value={crimeType}
            onChange={(v) => setCrimeType(v as CrimeTypeFilter)}
            options={CRIME_OPTIONS}
          />
        </div>
        <span className="w-px h-4 bg-white/10 shrink-0" />
        <div className="flex shrink-0">
          {TIME_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setTimeRange(opt.value)}
              className={`text-[10px] sm:text-[11px] font-mono uppercase px-1.5 sm:px-2.5 py-0.5 sm:py-1 rounded-full transition-colors ${
                timeRange === opt.value
                  ? "bg-white/10 text-white"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}

function Dot({ color, count }: { color: string; count: number }) {
  return (
    <div className="flex items-center gap-1">
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}` }}
      />
      <span
        className="text-[11px] font-mono tabular-nums"
        style={{ color: count > 0 ? color : "#94a3b8" }}
      >
        {count}
      </span>
    </div>
  );
}

function Select<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as T)}
      className="bg-transparent border-0 px-1.5 sm:px-2.5 py-0.5 sm:py-1 text-[10px] sm:text-[11px] text-slate-200 font-mono hover:text-white focus:outline-none cursor-pointer max-w-[80px] sm:max-w-none truncate"
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value} className="bg-[#0a0e17]">
          {opt.label}
        </option>
      ))}
    </select>
  );
}
