import React, { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Tooltip,
  Popup,
  Polygon,
  useMap,
} from "react-leaflet";
import { LatLngBounds, divIcon } from "leaflet";
import "leaflet/dist/leaflet.css";
import { useFilteredIncidents, useStore, timeAgo } from "./store";
import {
  SG_CENTER,
  SG_ZOOM,
  SEVERITY_COLOR,
  SEVERITY_LABEL,
  type Severity,
  type Incident,
} from "./mockData";
import { Crosshair, Map as MapIcon } from "lucide-react";

// Singapore bounding box — locks panning to this region
const SG_BOUNDS = new LatLngBounds([1.16, 103.6], [1.48, 104.1]);
const SG_MIN_ZOOM = 12;
const SG_MAX_ZOOM = 18;

type MapStyleId = "voyager" | "dark_matter" | "positron" | "satellite";
interface MapStyle {
  id: MapStyleId;
  label: string;
  url: string;
  attribution: string;
}

const MAP_STYLES: MapStyle[] = [
  {
    id: "voyager",
    label: "Voyager",
    url: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
  {
    id: "dark_matter",
    label: "Dark Matter",
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
  {
    id: "positron",
    label: "Positron",
    url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
  {
    id: "satellite",
    label: "Satellite",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution:
      "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics",
  },
];

// Heat ramp by incident count per area
interface HeatStop {
  fill: string;
  glow: string;
  ring: string;
  label: string;
  bounce: number; // seconds
}
function getHeat(count: number): HeatStop {
  if (count >= 10)
    return { fill: "#b91c1c", glow: "#ef4444", ring: "rgba(239,68,68,0.55)", label: "10+ incidents", bounce: 0.9 };
  if (count >= 7)
    return { fill: "#ef4444", glow: "#f87171", ring: "rgba(248,113,113,0.5)", label: "7–9 incidents", bounce: 1.1 };
  if (count >= 4)
    return { fill: "#f97316", glow: "#fb923c", ring: "rgba(251,146,60,0.45)", label: "4–6 incidents", bounce: 1.5 };
  if (count >= 2)
    return { fill: "#eab308", glow: "#facc15", ring: "rgba(250,204,21,0.4)", label: "2–3 incidents", bounce: 2.0 };
  return { fill: "#06b6d4", glow: "#22d3ee", ring: "rgba(34,211,238,0.4)", label: "1 incident", bounce: 2.6 };
}

const HEAT_LEGEND: { count: number; label: string }[] = [
  { count: 1, label: "1" },
  { count: 2, label: "2–3" },
  { count: 4, label: "4–6" },
  { count: 7, label: "7–9" },
  { count: 10, label: "10+" },
];

function FlyController() {
  const map = useMap();
  const flyTo = useStore((s) => s.mapFlyTo);
  useEffect(() => {
    if (flyTo) {
      map.flyTo([flyTo.lat, flyTo.lng], flyTo.zoom, {
        duration: 1.6,
        easeLinearity: 0.18,
      });
    }
  }, [flyTo, map]);
  return null;
}

export default function MapView() {
  const incidents = useFilteredIncidents();
  const { selectedIncidentId, selectIncident, flyTo } = useStore();
  const [styleId, setStyleId] = useState<MapStyleId>("voyager");
  const [styleMenuOpen, setStyleMenuOpen] = useState(false);
  const [hoveredArea, setHoveredArea] = useState<string | null>(null);
  const [openArea, setOpenArea] = useState<string | null>(null);
  const activeStyle = MAP_STYLES.find((s) => s.id === styleId) ?? MAP_STYLES[0];

  const { areas, unmatched } = useAreaAggregates(incidents);

  // Clear stale hover when the detail panel closes
  useEffect(() => {
    if (!selectedIncidentId) setHoveredArea(null);
  }, [selectedIncidentId]);

  return (
    <div className="relative w-full h-full overflow-hidden">
      <div
        className="safewatch-map-stage"
        style={{ width: "100%", height: "100%" }}
      >
        <MapContainer
          center={SG_CENTER}
          zoom={SG_ZOOM}
          minZoom={SG_MIN_ZOOM}
          maxZoom={SG_MAX_ZOOM}
          maxBounds={SG_BOUNDS}
          maxBoundsViscosity={1.0}
          scrollWheelZoom
          zoomControl={false}
          worldCopyJump={false}
          zoomSnap={0.25}
          zoomDelta={0.5}
          wheelPxPerZoomLevel={140}
          zoomAnimation
          fadeAnimation
          markerZoomAnimation
          className="w-full h-full bg-[#0a0e17]"
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            key={activeStyle.id}
            url={activeStyle.url}
            attribution={activeStyle.attribution}
          />
          <FlyController />

          {/* Polygon outline for the area currently hovered or open */}
          {areas
            .filter(
              (a) => a.areaName === hoveredArea || a.areaName === openArea,
            )
            .map((a) => (
              <PolygonOutline
                key={`outline-${a.areaName}`}
                geom={a.geom}
                color={getHeat(a.incidents.length).fill}
              />
            ))}

          {/* One pin per planning area */}
          {areas.map((a) => (
            <AreaPin
              key={a.areaName}
              area={a}
              open={openArea === a.areaName}
              onOpen={() => setOpenArea(a.areaName)}
              onClose={() => setOpenArea(null)}
              onHover={(h) => setHoveredArea(h ? a.areaName : null)}
              onIncidentClick={(inc) => {
                selectIncident(inc.id);
                flyTo(a.centroid[0], a.centroid[1], 15);
                setOpenArea(null);
              }}
            />
          ))}

          {/* Fallback: incidents we couldn't match to any area
              (e.g. "Online — multiple victims") — rendered with the
              original sharp pushpin so nothing is lost. */}
          {unmatched.map((inc) => (
            <FallbackPin
              key={inc.id}
              incident={inc}
              selected={inc.id === selectedIncidentId}
              onClick={() => {
                selectIncident(inc.id);
                flyTo(inc.location.lat, inc.location.lng, 16);
              }}
            />
          ))}
        </MapContainer>
      </div>

      <div className="safewatch-vignette pointer-events-none absolute inset-0" />

      <div className="absolute top-16 left-3 z-[1000] flex flex-col gap-2">
        <RecenterStandalone />
        <div className="relative">
          <button
            onClick={() => setStyleMenuOpen((v) => !v)}
            className={`safewatch-control-btn ${styleMenuOpen ? "is-active" : ""}`}
            title="Change map style"
          >
            <MapIcon className="w-4 h-4" />
          </button>
          {styleMenuOpen && (
            <div className="absolute left-12 top-0 z-[1100] safewatch-glass-panel rounded-lg p-1.5 min-w-[160px]">
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 px-2 py-1">
                Map Style
              </div>
              {MAP_STYLES.map((s) => (
                <button
                  key={s.id}
                  onClick={() => {
                    setStyleId(s.id);
                    setStyleMenuOpen(false);
                  }}
                  className={`w-full text-left text-xs font-mono px-2.5 py-1.5 rounded transition-colors ${
                    s.id === styleId
                      ? "bg-blue-500/20 text-blue-300"
                      : "text-slate-300 hover:bg-white/5"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Heatmap legend — count-based */}
      <div className="absolute bottom-3 left-3 z-[1000] safewatch-glass-panel rounded-2xl sm:rounded-full px-2.5 py-2 sm:px-3 sm:py-1.5 flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-3 text-[10px] font-mono">
        <span className="text-slate-400 uppercase tracking-wider">Density</span>
        {HEAT_LEGEND.map((h) => {
          const heat = getHeat(h.count);
          return (
            <div key={h.count} className="flex items-center gap-1.5">
              <span
                className="w-2 h-2 rounded-full"
                style={{
                  backgroundColor: heat.fill,
                  boxShadow: `0 0 6px ${heat.glow}`,
                }}
              />
              <span className="text-slate-300 uppercase tracking-wide">
                {h.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RecenterStandalone() {
  const flyTo = useStore((s) => s.flyTo);
  return (
    <button
      onClick={() => flyTo(SG_CENTER[0], SG_CENTER[1], SG_ZOOM)}
      className="safewatch-control-btn"
      title="Recenter on Singapore"
    >
      <Crosshair className="w-4 h-4" />
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Area aggregation
// ─────────────────────────────────────────────────────────────────────

interface AreaAggregate {
  areaName: string; // "GEYLANG"
  centroid: [number, number]; // [lat, lng]
  geom: PlanningGeom;
  incidents: Incident[];
}

function useAreaAggregates(incidents: Incident[]): {
  areas: AreaAggregate[];
  unmatched: Incident[];
} {
  const [areasMap, setAreasMap] = useState<Map<string, PlanningGeom> | null>(
    planningAreaCache,
  );
  useEffect(() => {
    if (!areasMap) loadPlanningAreas().then(setAreasMap);
  }, [areasMap]);

  return useMemo(() => {
    if (!areasMap) return { areas: [], unmatched: [] };
    const knownNames = [...areasMap.keys()];
    const buckets = new Map<string, Incident[]>();
    const unmatched: Incident[] = [];

    for (const inc of incidents) {
      const name = matchPlanningAreaName(inc.location.area, knownNames);
      if (!name) {
        unmatched.push(inc);
        continue;
      }
      const list = buckets.get(name) ?? [];
      list.push(inc);
      buckets.set(name, list);
    }

    const areas: AreaAggregate[] = [];
    for (const [name, list] of buckets) {
      const geom = areasMap.get(name);
      if (!geom) continue;
      areas.push({
        areaName: name,
        centroid: computeCentroid(geom),
        geom,
        incidents: list.sort(
          (a, b) =>
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
        ),
      });
    }
    return { areas, unmatched };
  }, [areasMap, incidents]);
}

// ─────────────────────────────────────────────────────────────────────
// Area pin (one per planning area)
// ─────────────────────────────────────────────────────────────────────

function AreaPin({
  area,
  open,
  onOpen,
  onClose,
  onHover,
  onIncidentClick,
}: {
  area: AreaAggregate;
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  onHover: (hovering: boolean) => void;
  onIncidentClick: (inc: Incident) => void;
}) {
  const count = area.incidents.length;
  const heat = getHeat(count);
  // Pin grows a bit with count, capped
  const size = Math.min(28 + Math.log2(count) * 6, 52);
  const ringSize = size + 14;

  const icon = useMemo(
    () =>
      divIcon({
        className: "safewatch-area-pin-wrap",
        html: `
          <div class="safewatch-area-pin"
               style="--pin-size:${size}px;--ring-size:${ringSize}px;--pin-fill:${heat.fill};--pin-glow:${heat.glow};--pin-ring:${heat.ring};--pin-bounce:${heat.bounce}s;">
            <div class="safewatch-area-pin-ring"></div>
            <div class="safewatch-area-pin-disc">
              <span class="safewatch-area-pin-count">${count}</span>
            </div>
          </div>
        `,
        iconSize: [ringSize, ringSize],
        iconAnchor: [ringSize / 2, ringSize / 2],
      }),
    [count, size, ringSize, heat.fill, heat.glow, heat.ring, heat.bounce],
  );

  return (
    <Marker
      position={area.centroid}
      icon={icon}
      eventHandlers={{
        click: onOpen,
        mouseover: () => onHover(true),
        mouseout: () => onHover(false),
      }}
      zIndexOffset={count * 10}
    >
      {/* Hover tooltip — quick preview.
          Always mounted (Leaflet auto-hides while popup is open).
          Conditionally unmounting causes a "_source on null" crash
          when react-leaflet tries to unbind a tooltip from a marker
          that's also re-rendering. */}
      <Tooltip
        direction="top"
        offset={[0, -ringSize / 2]}
        opacity={1}
        className="safewatch-tooltip"
      >
          <div className="text-xs min-w-[180px] max-w-[240px]">
            <div className="flex items-center justify-between gap-2 mb-1">
              <div
                className="font-bold uppercase tracking-wide"
                style={{ color: heat.fill }}
              >
                {prettyAreaName(area.areaName)}
              </div>
              <span
                className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                style={{
                  backgroundColor: `${heat.fill}26`,
                  color: heat.glow,
                  border: `1px solid ${heat.fill}55`,
                }}
              >
                {count}
              </span>
            </div>
            <div className="space-y-1 max-h-[160px] overflow-hidden">
              {area.incidents.slice(0, 5).map((inc) => (
                <div
                  key={inc.id}
                  className="flex items-center gap-1.5 text-[11px]"
                >
                  <span
                    className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    style={{
                      backgroundColor: SEVERITY_COLOR[inc.severity],
                      boxShadow: `0 0 4px ${SEVERITY_COLOR[inc.severity]}`,
                    }}
                  />
                  <span className="text-slate-200 truncate">{inc.title}</span>
                  <span className="text-slate-500 font-mono text-[9px] ml-auto flex-shrink-0">
                    {timeAgo(inc.timestamp)}
                  </span>
                </div>
              ))}
              {count > 5 && (
                <div className="text-[10px] text-slate-500 italic pt-0.5">
                  +{count - 5} more — click to view
                </div>
              )}
            </div>
            <div className="text-[10px] text-slate-500 mt-1.5 pt-1.5 border-t border-white/10">
              Click pin to open list
            </div>
          </div>
        </Tooltip>

      {/* Click popup — interactive list */}
      <Popup
        className="safewatch-popup"
        offset={[0, -ringSize / 2 + 4]}
        closeButton={false}
        autoPan
        eventHandlers={{ remove: onClose }}
      >
        <div className="text-xs min-w-[220px] max-w-[280px]">
          <div className="flex items-center justify-between gap-2 mb-2">
            <div
              className="font-bold uppercase tracking-wide text-sm"
              style={{ color: heat.fill }}
            >
              {prettyAreaName(area.areaName)}
            </div>
            <span
              className="text-[10px] font-mono px-2 py-0.5 rounded-full"
              style={{
                backgroundColor: `${heat.fill}26`,
                color: heat.glow,
                border: `1px solid ${heat.fill}55`,
              }}
            >
              {heat.label}
            </span>
          </div>
          <div className="space-y-1 max-h-[260px] overflow-y-auto safewatch-popup-scroll">
            {area.incidents.map((inc) => (
              <button
                key={inc.id}
                onClick={() => onIncidentClick(inc)}
                className="w-full text-left flex items-start gap-2 px-2 py-1.5 rounded hover:bg-white/10 transition-colors"
              >
                <span
                  className="w-2 h-2 rounded-full mt-1 flex-shrink-0"
                  style={{
                    backgroundColor: SEVERITY_COLOR[inc.severity],
                    boxShadow: `0 0 6px ${SEVERITY_COLOR[inc.severity]}`,
                  }}
                />
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-slate-100 truncate">
                    {inc.title}
                  </div>
                  <div className="text-slate-400 text-[10px] truncate">
                    {inc.location.area}
                  </div>
                </div>
                <span className="text-slate-500 font-mono text-[10px] mt-0.5 flex-shrink-0">
                  {timeAgo(inc.timestamp)}
                </span>
              </button>
            ))}
          </div>
        </div>
      </Popup>
    </Marker>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Fallback pin (incidents that can't be mapped to a planning area)
// ─────────────────────────────────────────────────────────────────────

function FallbackPin({
  incident,
  selected,
  onClick,
}: {
  incident: Incident;
  selected: boolean;
  onClick: () => void;
}) {
  const color = SEVERITY_COLOR[incident.severity];
  const headSize = selected ? 20 : 16;
  const totalH = 40;
  const totalW = headSize + 6;

  const icon = useMemo(
    () =>
      divIcon({
        className: "safewatch-pin-wrap",
        html: `
          <div class="safewatch-pushpin ${selected ? "is-selected" : ""}"
               style="--pin-color:${color};--head-size:${headSize}px;--pin-bounce:2s;">
            <div class="safewatch-pushpin-shadow"></div>
            <svg class="safewatch-pushpin-body" viewBox="0 0 ${totalW} ${totalH}" width="${totalW}" height="${totalH}">
              <ellipse cx="${totalW / 2}" cy="${totalH - 1}" rx="${headSize / 2.2}" ry="1.4" fill="rgba(0,0,0,0.55)" />
              <path d="M ${totalW / 2 - 0.8} ${headSize - 1} L ${totalW / 2 + 0.8} ${headSize - 1} L ${totalW / 2 + 0.4} ${totalH - 2} L ${totalW / 2 - 0.4} ${totalH - 2} Z"
                    fill="#94a3b8"/>
              <circle cx="${totalW / 2}" cy="${headSize / 2}" r="${headSize / 2}"
                      fill="${color}"
                      stroke="rgba(255,255,255,0.85)" stroke-width="1"/>
            </svg>
          </div>
        `,
        iconSize: [totalW, totalH],
        iconAnchor: [totalW / 2, totalH - 1],
      }),
    [color, headSize, totalH, totalW, selected],
  );

  return (
    <Marker
      position={[incident.location.lat, incident.location.lng]}
      icon={icon}
      eventHandlers={{ click: onClick }}
      zIndexOffset={selected ? 1000 : 0}
    >
      <Tooltip
        direction="top"
        offset={[0, -totalH - 2]}
        opacity={1}
        className="safewatch-tooltip"
      >
        <div className="text-xs">
          <div className="font-bold" style={{ color }}>
            {incident.title}
          </div>
          <div className="text-slate-300">{incident.location.area}</div>
          <div className="text-slate-400 font-mono text-[10px]">
            {timeAgo(incident.timestamp)}
          </div>
        </div>
      </Tooltip>
    </Marker>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Planning-area geometry helpers
// ─────────────────────────────────────────────────────────────────────

type PlanningGeom =
  | { type: "Polygon"; coordinates: number[][][] }
  | { type: "MultiPolygon"; coordinates: number[][][][] };

interface PlanningFeature {
  properties: { name: string };
  geometry: PlanningGeom;
}

let planningAreaCache: Map<string, PlanningGeom> | null = null;
let planningAreaPromise: Promise<Map<string, PlanningGeom>> | null = null;

function loadPlanningAreas(): Promise<Map<string, PlanningGeom>> {
  if (planningAreaCache) return Promise.resolve(planningAreaCache);
  if (planningAreaPromise) return planningAreaPromise;
  planningAreaPromise = fetch("/data/sg-planning-areas.geojson")
    .then((r) => r.json())
    .then((gj: { features: PlanningFeature[] }) => {
      const map = new Map<string, PlanningGeom>();
      for (const f of gj.features) {
        map.set(f.properties.name.toUpperCase(), f.geometry);
      }
      planningAreaCache = map;
      return map;
    });
  return planningAreaPromise;
}

// Longest-substring match: "Geylang Lorong 25" → "GEYLANG"
function matchPlanningAreaName(
  text: string,
  knownNames: string[],
): string | null {
  const upper = text.toUpperCase();
  let best: string | null = null;
  for (const name of knownNames) {
    if (upper.includes(name) && (!best || name.length > best.length))
      best = name;
  }
  return best;
}

// Convert geojson [lng,lat] → leaflet [lat,lng]
function toLeafletPositions(
  geom: PlanningGeom,
): [number, number][] | [number, number][][] {
  if (geom.type === "Polygon") {
    return geom.coordinates[0].map(([lng, lat]) => [lat, lng]);
  }
  return geom.coordinates.map((poly) =>
    poly[0].map(([lng, lat]) => [lat, lng] as [number, number]),
  );
}

// Centroid: average of outer-ring vertices of the largest polygon.
// Fast and visually fine for HDB-style planning areas.
function computeCentroid(geom: PlanningGeom): [number, number] {
  let ring: number[][];
  if (geom.type === "Polygon") {
    ring = geom.coordinates[0];
  } else {
    // pick the outer ring of the largest polygon by vertex count
    let largest = geom.coordinates[0];
    for (const p of geom.coordinates) {
      if (p[0].length > largest[0].length) largest = p;
    }
    ring = largest[0];
  }
  let sumLat = 0;
  let sumLng = 0;
  for (const [lng, lat] of ring) {
    sumLat += lat;
    sumLng += lng;
  }
  return [sumLat / ring.length, sumLng / ring.length];
}

function prettyAreaName(upperName: string): string {
  return upperName
    .toLowerCase()
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function PolygonOutline({
  geom,
  color,
}: {
  geom: PlanningGeom;
  color: string;
}) {
  const positions = useMemo(() => toLeafletPositions(geom), [geom]);
  return (
    <Polygon
      positions={positions as [number, number][] | [number, number][][]}
      pathOptions={{
        color,
        weight: 2.5,
        opacity: 0.9,
        fillColor: color,
        fillOpacity: 0.15,
        className: "safewatch-area-outline",
        interactive: false,
      }}
    />
  );
}
