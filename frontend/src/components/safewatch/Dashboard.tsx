import { useEffect } from "react";
import Header from "./Header";
import MapView from "./MapView";
import IncidentDetailPanel from "./IncidentDetailPanel";
import SeveritySidebar from "./SeveritySidebar";
import { useStore } from "./store";

export default function Dashboard() {
  const loadIncidents = useStore((s) => s.loadIncidents);
  const loadAgentLogs = useStore((s) => s.loadAgentLogs);

  useEffect(() => {
    loadIncidents();
    loadAgentLogs();
  }, [loadIncidents, loadAgentLogs]);

  return (
    <div className="h-dvh min-h-dvh w-screen flex flex-col bg-[#0a0e17] text-slate-100 overflow-hidden">
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
      className={`absolute z-[1050] flex pointer-events-none
        ${collapsed
          ? "right-2 bottom-[calc(1rem+env(safe-area-inset-bottom))] sm:right-4 sm:bottom-auto sm:top-20 w-auto"
          : "left-0 right-0 bottom-0 top-auto max-h-[46dvh] sm:left-auto sm:right-4 sm:top-20 sm:bottom-16 sm:w-[300px] sm:max-w-[calc(100%-2rem)]"
        }`}
    >
      <div
        className={`safewatch-glass-panel w-full pointer-events-auto overflow-hidden flex flex-col max-h-full ${
          collapsed ? "rounded-full sm:rounded-2xl" : "rounded-t-2xl sm:rounded-2xl"
        }`}
      >
        <SeveritySidebar />
      </div>
    </div>
  );
}
