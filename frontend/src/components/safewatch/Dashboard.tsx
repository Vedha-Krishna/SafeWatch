import { useEffect } from "react";
import Header from "./Header";
import MapView from "./MapView";
import IncidentDetailPanel from "./IncidentDetailPanel";
import SeveritySidebar from "./SeveritySidebar";
import { useStore } from "./store";

export default function Dashboard() {
  const loadIncidents = useStore((s) => s.loadIncidents);

  useEffect(() => {
    loadIncidents();
  }, [loadIncidents]);

  return (
    <div className="h-screen w-screen flex flex-col bg-[#0a0e17] text-slate-100 overflow-hidden">
      <Header />
      <div className="relative flex-1 min-h-0">
        <div className="absolute inset-0">
          <MapView />
        </div>
        <SidebarContainer />
        <IncidentDetailPanel />
      </div>
    </div>
  );
}

function SidebarContainer() {
  const collapsed = useStore((s) => s.sidebarCollapsed);
  return (
    <div
      className={`absolute z-[1050] flex pointer-events-none right-3 sm:right-4
        ${collapsed
          ? "bottom-12 sm:bottom-auto sm:top-20 w-auto"
          : "left-3 sm:left-auto top-[8.5rem] sm:top-20 w-auto sm:w-[300px] max-w-[calc(100%-1.5rem)] sm:max-w-[calc(100%-2rem)] bottom-3 sm:bottom-16"
        }`}
    >
      <div className="safewatch-glass-panel w-full pointer-events-auto rounded-2xl overflow-hidden flex flex-col">
        <SeveritySidebar />
      </div>
    </div>
  );
}
