import Link from "next/link";

type Incident = {
  incident_id: string;
  post_id: string;
  source_platform: string;
  source_url: string;
  raw_text: string;
  candidate: boolean;
  short_reason: string;
  category: string | null;
  severity: string | null;
  authenticity_score: number | null;
  location_text: string | null;
  latitude: number | null;
  longitude: number | null;
  timestamp_text: string | null;
  normalized_time: string | null;
  candidate_scores: Record<string, number>;
  matched_signals: string[];
  evidence_snippets: string[];
  status: string;
  duplicate_of: string | null;
  agent_notes: string[];
};

type IncidentResponse = {
  count: number;
  incidents: Incident[];
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const CATEGORY_STYLES: Record<string, string> = {
  theft: "bg-rose-100 text-rose-700",
  attempted_theft: "bg-orange-100 text-orange-700",
  vandalism: "bg-amber-100 text-amber-700",
  suspicious_activity: "bg-blue-100 text-blue-700",
  harassment: "bg-violet-100 text-violet-700",
};

export const dynamic = "force-dynamic";

function formatCategory(category: string | null): string {
  if (!category) {
    return "Uncategorized";
  }

  return category
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Unknown time";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString("en-SG", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

async function getIncidents(): Promise<{
  incidents: Incident[];
  error: string | null;
}> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/incidents?candidate_only=true&limit=100`,
      {
        cache: "no-store",
      },
    );

    if (!response.ok) {
      return {
        incidents: [],
        error: `Backend returned ${response.status}.`,
      };
    }

    const data = (await response.json()) as IncidentResponse;

    return {
      incidents: data.incidents,
      error: null,
    };
  } catch {
    return {
      incidents: [],
      error: `Cannot reach backend at ${API_BASE_URL}.`,
    };
  }
}

export default async function Home() {
  const { incidents, error } = await getIncidents();

  const categorySummary = incidents.reduce<Record<string, number>>(
    (summary, incident) => {
      const key = incident.category ?? "uncategorized";
      summary[key] = (summary[key] ?? 0) + 1;
      return summary;
    },
    {},
  );

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6">
        <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
            PettyCrimeSingapore
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            Incident Dashboard
          </h1>
          <p className="mt-3 max-w-3xl text-sm text-slate-600">
            This frontend is connected to the Python FastAPI backend and shows
            candidate incidents generated from mock community posts.
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <Link
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
              href="/"
            >
              Refresh Data
            </Link>
            <code className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-700">
              {API_BASE_URL}/api/incidents
            </code>
          </div>
        </section>

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <article className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-xs uppercase tracking-wide text-slate-500">Candidates</p>
            <p className="mt-1 text-2xl font-semibold">{incidents.length}</p>
          </article>
          {Object.entries(categorySummary).map(([key, count]) => (
            <article
              className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200"
              key={key}
            >
              <p className="text-xs uppercase tracking-wide text-slate-500">
                {formatCategory(key === "uncategorized" ? null : key)}
              </p>
              <p className="mt-1 text-2xl font-semibold">{count}</p>
            </article>
          ))}
        </section>

        <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              <p className="font-medium">Unable to load incidents: {error}</p>
              <p className="mt-1">
                Start backend with
                <code className="mx-1 rounded bg-red-100 px-1 py-0.5">
                  uvicorn backend.main:app --reload
                </code>
                from the repo root.
              </p>
            </div>
          )}

          {!error && incidents.length === 0 && (
            <p className="text-sm text-slate-600">No incidents returned.</p>
          )}

          {!error && incidents.length > 0 && (
            <div className="grid gap-4 lg:grid-cols-2">
              {incidents.map((incident) => (
                <article
                  className="rounded-xl border border-slate-200 p-4"
                  key={incident.incident_id}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-medium ${CATEGORY_STYLES[incident.category ?? ""] ?? "bg-slate-100 text-slate-700"}`}
                    >
                      {formatCategory(incident.category)}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                      {incident.status}
                    </span>
                  </div>

                  <p className="mt-3 text-sm leading-6 text-slate-700">
                    {incident.raw_text}
                  </p>

                  <dl className="mt-4 grid grid-cols-1 gap-2 text-xs text-slate-600 sm:grid-cols-2">
                    <div>
                      <dt className="font-semibold text-slate-800">Location</dt>
                      <dd>{incident.location_text ?? "Unknown"}</dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-800">Time</dt>
                      <dd>{formatDate(incident.normalized_time)}</dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-800">Source</dt>
                      <dd>{incident.source_platform}</dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-slate-800">Incident ID</dt>
                      <dd>{incident.incident_id}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
