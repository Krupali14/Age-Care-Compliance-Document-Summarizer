import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateDeadlineStatus, type Deadline } from "../api/extractions";

// Ordered most urgent first — the same order the API's BUCKETS tuple uses, and the
// order rows sort in when sorting by urgency.
const BUCKETS = ["overdue", "within_24_hours", "within_7_days", "within_30_days", "later", "no_date"] as const;

const BUCKET_LABEL: Record<string, string> = {
  overdue: "Overdue",
  within_24_hours: "Within 24 hours",
  within_7_days: "Within 7 days",
  within_30_days: "Within 30 days",
  later: "Later",
  no_date: "No date",
};

const BUCKET_TONE: Record<string, string> = {
  overdue: "bg-coral/10 text-coral",
  within_24_hours: "bg-coral/10 text-coral",
  within_7_days: "bg-amber-50 text-amber",
  within_30_days: "bg-teal-50 text-teal-600",
  later: "bg-parchment-200 text-slate-500",
  no_date: "bg-parchment-200 text-slate-400",
};

const BUCKET_BAR: Record<string, string> = {
  overdue: "bg-coral",
  within_24_hours: "bg-coral",
  within_7_days: "bg-amber",
  within_30_days: "bg-teal",
  later: "bg-slate-200",
  no_date: "bg-slate-200",
};

const STATUSES = [
  { value: "not_started", label: "Not started" },
  { value: "in_progress", label: "In progress" },
  { value: "completed", label: "Completed" },
];

/** "17 Sep 2026, 6:00 pm" — deadlines can fall due at an hour, not just on a day. */
function formatDueAt(iso: string | null) {
  if (!iso) return null;
  return new Date(iso).toLocaleString(undefined, {
    day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

export default function DeadlineTable({
  docId,
  rows,
  sections,
  onSectionClick,
}: {
  docId: number;
  rows: Deadline[];
  sections: { id: number; heading: string }[];
  onSectionClick?: (sectionId: number) => void;
}) {
  const [bucketFilter, setBucketFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sort, setSort] = useState<"urgency" | "latest" | "status">("urgency");
  const queryClient = useQueryClient();

  const setStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => updateDeadlineStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["deadlines", docId] }),
  });

  const headingFor = (sectionId?: number) => sections.find((s) => s.id === sectionId)?.heading ?? "—";
  const counts = useMemo(() => {
    const out: Record<string, number> = {};
    for (const row of rows) out[row.bucket] = (out[row.bucket] ?? 0) + 1;
    return out;
  }, [rows]);

  const visible = useMemo(() => {
    const filtered = rows.filter(
      (r) => (bucketFilter === "all" || r.bucket === bucketFilter) && (statusFilter === "all" || r.status === statusFilter),
    );
    // Rows with no due time sort last whichever way the list is ordered — an unknown
    // date is not "very soon" and not "very far away".
    const rank = (r: Deadline) => BUCKETS.indexOf(r.bucket as (typeof BUCKETS)[number]);
    return [...filtered].sort((a, b) => {
      if (sort === "status") return STATUSES.findIndex((s) => s.value === a.status) - STATUSES.findIndex((s) => s.value === b.status);
      if (a.due_at === null || b.due_at === null) return (a.due_at === null ? 1 : 0) - (b.due_at === null ? 1 : 0);
      if (sort === "latest") return b.due_at.localeCompare(a.due_at);
      return rank(a) - rank(b) || a.due_at.localeCompare(b.due_at);
    });
  }, [rows, bucketFilter, statusFilter, sort]);

  if (rows.length === 0) {
    return (
      <div className="p-10 text-center">
        <p className="text-sm text-slate-500">Nothing extracted for this category yet.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 border-b border-ink/10 px-5 py-3">
        <button
          onClick={() => setBucketFilter("all")}
          className={`rounded-full px-2.5 py-1 text-xs transition ${bucketFilter === "all" ? "bg-ink text-parchment" : "bg-parchment-200 text-slate-500 hover:bg-parchment"}`}
        >
          All {rows.length}
        </button>
        {BUCKETS.filter((b) => counts[b]).map((b) => (
          <button
            key={b}
            onClick={() => setBucketFilter(b)}
            className={`rounded-full px-2.5 py-1 text-xs transition ${bucketFilter === b ? "bg-ink text-parchment" : `${BUCKET_TONE[b]} hover:opacity-80`}`}
          >
            {BUCKET_LABEL[b]} {counts[b]}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <label className="sr-only" htmlFor="deadline-status-filter">Filter by status</label>
          <select
            id="deadline-status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-ink/10 bg-white px-2 py-1 text-xs text-slate-500"
          >
            <option value="all">Any status</option>
            {STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
          <label className="sr-only" htmlFor="deadline-sort">Sort deadlines</label>
          <select
            id="deadline-sort"
            value={sort}
            onChange={(e) => setSort(e.target.value as typeof sort)}
            className="rounded-lg border border-ink/10 bg-white px-2 py-1 text-xs text-slate-500"
          >
            <option value="urgency">Most urgent first</option>
            <option value="latest">Furthest away first</option>
            <option value="status">By status</option>
          </select>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[46rem] text-left text-sm">
          <thead className="border-b border-ink/10 text-xs uppercase tracking-wide text-slate-400">
            <tr>
              <th className="py-3 pl-5">Deadline</th>
              <th className="py-3">Role</th>
              <th className="py-3">Due</th>
              <th className="py-3">Urgency</th>
              <th className="py-3">Progress</th>
              <th className="py-3 pr-5">Source section</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={row.id} className="group border-b border-ink/5 transition hover:bg-parchment-100">
                <td className="relative py-3 pl-5 pr-4">
                  <span className={`absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full ${BUCKET_BAR[row.bucket] ?? "bg-slate-200"}`} />
                  <span className={row.status === "completed" ? "text-slate-400 line-through" : ""}>{row.description}</span>
                </td>
                <td className="py-3 pr-4 text-slate-500">{row.responsible_role ?? "—"}</td>
                <td className="py-3 pr-4 text-xs text-slate-500">
                  {formatDueAt(row.due_at) ?? "—"}
                  {/* The wording the document used, kept beside the resolved time so a
                      relative timeframe is still traceable to its trigger. */}
                  {row.due_date && row.due_date !== row.due_at?.slice(0, 10) && (
                    <span className="block font-mono text-[11px] text-slate-400">{row.due_date}</span>
                  )}
                </td>
                <td className="py-3 pr-4">
                  <span className={`rounded-full px-2 py-0.5 text-xs ${BUCKET_TONE[row.bucket] ?? "bg-parchment-200 text-slate-500"}`}>
                    {BUCKET_LABEL[row.bucket] ?? row.bucket}
                  </span>
                </td>
                <td className="py-3 pr-4">
                  <label className="sr-only" htmlFor={`deadline-status-${row.id}`}>Progress for {row.description}</label>
                  <select
                    id={`deadline-status-${row.id}`}
                    value={row.status}
                    disabled={setStatus.isPending}
                    onChange={(e) => setStatus.mutate({ id: row.id, status: e.target.value })}
                    className="rounded-lg border border-ink/10 bg-white px-2 py-1 text-xs text-slate-500"
                  >
                    {STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                </td>
                <td className="py-3 pr-5">
                  {row.section_id != null && onSectionClick ? (
                    <button
                      onClick={() => onSectionClick(row.section_id)}
                      className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2.5 py-1 font-mono text-xs text-teal-600 transition hover:bg-teal hover:text-white"
                    >
                      {headingFor(row.section_id)}
                    </button>
                  ) : (
                    <span className="font-mono text-xs text-slate-500">{headingFor(row.section_id)}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {visible.length === 0 && (
          <p className="p-10 text-center text-sm text-slate-500">No deadlines match these filters.</p>
        )}
      </div>
    </div>
  );
}
