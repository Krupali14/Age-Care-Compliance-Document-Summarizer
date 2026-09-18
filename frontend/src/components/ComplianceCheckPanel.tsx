import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createCheck, deleteCheck, getCheck, listChecks, type CheckFinding,
} from "../api/compliance";

const VERDICT_GROUPS = [
  { key: "not_done", label: "Not done", tone: "bg-coral/10 text-coral" },
  { key: "partly", label: "Partly done", tone: "bg-amber-50 text-amber" },
  { key: "done", label: "Done — maintain", tone: "bg-sage/10 text-sage" },
  { key: "unclear", label: "Not covered by this case study", tone: "bg-parchment-200 text-slate-500" },
] as const;

function formatWhen(iso: string | null) {
  if (!iso) return null;
  return new Date(iso).toLocaleString(undefined, {
    day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}

function FindingRow({
  finding,
  sections,
  onSectionClick,
}: {
  finding: CheckFinding;
  sections: { id: number; heading: string }[];
  onSectionClick?: (sectionId: number) => void;
}) {
  const heading = sections.find((s) => s.id === finding.section_id)?.heading;
  return (
    <div className="border-b border-ink/5 px-5 py-4">
      <p className="text-sm text-ink">{finding.requirement}</p>
      {finding.note && <p className="mt-1 text-sm text-slate-500">{finding.note}</p>}
      {/* Belt and braces: the backend now normalises the literal word "null" to
          None, but a row stored before that fix can still carry it. */}
      {finding.evidence && finding.evidence.trim().toLowerCase() !== "null" && (
        <blockquote className="mt-2 border-l-2 border-teal/40 pl-3 text-sm italic text-slate-500">
          {finding.evidence}
        </blockquote>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        {/* No bucket here: a check judges "was this done before the deadline",
            not "is the deadline before now" — bucketing due_at against today would
            call every past incident's deadline "overdue" beside a "done" verdict.
            The due time itself is still meaningful, so it stays. */}
        {finding.due_at && (
          <span className="rounded-full bg-parchment-200 px-2 py-0.5 text-slate-500">
            Due {formatWhen(finding.due_at)}
          </span>
        )}
        {heading && finding.section_id != null && onSectionClick && (
          <button
            onClick={() => onSectionClick(finding.section_id!)}
            className="rounded-full bg-teal-50 px-2.5 py-1 font-mono text-teal-600 transition hover:bg-teal hover:text-white"
          >
            {heading}
          </button>
        )}
      </div>
    </div>
  );
}

export default function ComplianceCheckPanel({
  docId,
  sections,
  onSectionClick,
}: {
  docId: number;
  sections: { id: number; heading: string }[];
  onSectionClick?: (sectionId: number) => void;
}) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: checks } = useQuery({
    queryKey: ["compliance-checks", docId],
    queryFn: () => listChecks(docId),
    // A check that is still running finishes without anything else touching the page.
    refetchInterval: (query) =>
      (query.state.data ?? []).some((c) => c.status === "pending" || c.status === "processing") ? 3000 : false,
  });

  const activeId = selected ?? checks?.[0]?.id ?? null;
  const { data: check } = useQuery({
    queryKey: ["compliance-check", activeId],
    queryFn: () => getCheck(activeId!),
    enabled: activeId != null,
    refetchInterval: (query) =>
      query.state.data?.status === "pending" || query.state.data?.status === "processing" ? 3000 : false,
  });

  const upload = useMutation({
    mutationFn: (file: File) => createCheck(docId, file),
    onSuccess: (created) => {
      setError(null);
      setSelected(created.id);
      queryClient.invalidateQueries({ queryKey: ["compliance-checks", docId] });
    },
    onError: (e: Error) => setError(e.message),
  });

  const remove = useMutation({
    mutationFn: (checkId: number) => deleteCheck(checkId),
    onSuccess: () => {
      setSelected(null);
      queryClient.invalidateQueries({ queryKey: ["compliance-checks", docId] });
    },
  });

  useEffect(() => {
    if (checks && activeId != null && !checks.some((c) => c.id === activeId)) setSelected(null);
  }, [checks, activeId]);

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3 border-b border-ink/10 px-5 py-4">
        <label className="cursor-pointer rounded-lg bg-ink px-3 py-2 text-sm text-parchment transition hover:bg-ink-800">
          {upload.isPending ? "Uploading…" : "Upload a case-study document"}
          <input
            type="file"
            accept=".pdf,.docx"
            // ponytail: visually hidden but not display:none / hidden — that would
            // pull it out of the tab order, which is exactly what made it mouse-only.
            className="absolute h-px w-px overflow-hidden opacity-0"
            aria-label="Upload a case-study document"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) upload.mutate(file);
              e.target.value = "";
            }}
          />
        </label>
        <p className="text-sm text-slate-500">
          Checked against this document's obligations and deadlines.
        </p>
        {(checks?.length ?? 0) > 1 && (
          <select
            aria-label="Select a case-study check"
            value={activeId ?? ""}
            onChange={(e) => setSelected(Number(e.target.value))}
            className="ml-auto rounded-lg border border-ink/10 bg-white px-2 py-1 text-xs text-slate-500"
          >
            {checks!.map((c) => <option key={c.id} value={c.id}>{c.filename}</option>)}
          </select>
        )}
      </div>

      {error && <p className="px-5 py-3 text-sm text-coral">{error}</p>}

      {!check && <p className="p-10 text-center text-sm text-slate-500">
        No case study checked yet. Upload one to see what is done, what is outstanding, and how long is left.
      </p>}

      {check && (check.status === "pending" || check.status === "processing") && (
        <p className="p-10 text-center text-sm text-slate-500">Checking {check.filename} against this document…</p>
      )}

      {check && check.status === "failed" && (
        <p className="p-10 text-center text-sm text-coral">{check.error_message}</p>
      )}

      {check && check.status === "done" && (
        <>
          <div className="flex flex-wrap items-center gap-3 border-b border-ink/10 bg-parchment-100 px-5 py-3 text-xs text-slate-500">
            <span className="font-medium text-ink">{check.filename}</span>
            <span>
              Incident {formatWhen(check.incident_at) ?? "unknown"}
              {check.incident_source === "upload_time" && " (assumed — the document states no date)"}
            </span>
            {/* The check succeeded — a requirement cap is a neutral notice about
                what was checked, not a failure, so it does not use the coral
                error styling `status === "failed"` gets below. */}
            {check.error_message && <span>{check.error_message}</span>}
            {VERDICT_GROUPS.map((g) => (
              <span key={g.key} className={`rounded-full px-2 py-0.5 ${g.tone}`}>
                {g.label} {check.counts[g.key] ?? 0}
              </span>
            ))}
            <button
              onClick={() => remove.mutate(check.id)}
              className="ml-auto rounded-lg border border-ink/10 px-2 py-1 transition hover:bg-white"
            >
              Delete check
            </button>
          </div>

          {VERDICT_GROUPS.map((group) => {
            const rows = check.findings.filter((f) => f.verdict === group.key);
            if (rows.length === 0) return null;
            // Deadlines first inside every group: a requirement with a clock on it is
            // the one the user has to act on first.
            const ordered = [...rows].sort((a, b) => (a.due_at ? 0 : 1) - (b.due_at ? 0 : 1));
            return (
              <section key={group.key}>
                <h3 className={`px-5 py-2 text-xs uppercase tracking-wide ${group.tone}`}>
                  {group.label} · {rows.length}
                </h3>
                {ordered.map((f) => (
                  <FindingRow key={f.id} finding={f} sections={sections} onSectionClick={onSectionClick} />
                ))}
              </section>
            );
          })}
        </>
      )}
    </div>
  );
}
