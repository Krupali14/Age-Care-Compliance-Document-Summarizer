interface Row {
  id: number;
  text: string;
  section_id?: number;
  responsible_role?: string | null;
  priority?: string | null;
  severity?: string | null;
  extra?: string | null;
}

const TONE_BAR: Record<string, string> = {
  high: "bg-coral",
  critical: "bg-coral",
  medium: "bg-amber",
  low: "bg-sage",
};

const TONE_TEXT: Record<string, string> = {
  high: "text-coral",
  critical: "text-coral",
  medium: "text-amber",
  low: "text-sage",
};

export default function CategoryTable({
  rows,
  sections,
  onSectionClick,
}: {
  rows: Row[];
  sections: { id: number; heading: string }[];
  onSectionClick?: (sectionId: number) => void;
}) {
  const headingFor = (sectionId?: number) => sections.find((s) => s.id === sectionId)?.heading ?? "—";
  const hasExtra = rows.some((row) => row.extra != null);

  if (rows.length === 0) {
    return (
      <div className="p-10 text-center">
        <p className="text-sm text-slate-500">Nothing extracted for this category yet.</p>
      </div>
    );
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="border-b border-ink/10 text-xs uppercase tracking-wide text-slate-400">
        <tr>
          <th className="py-3 pl-5">Text</th>
          <th className="py-3">Role</th>
          <th className="py-3">Priority / Severity</th>
          {hasExtra && <th className="py-3">Due / Timeframe</th>}
          <th className="py-3 pr-5">Source section</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const tone = (row.priority ?? row.severity ?? "").toLowerCase();
          return (
            <tr key={row.id} className="group border-b border-ink/5 transition hover:bg-parchment-100">
              <td className="relative py-3 pl-5 pr-4">
                <span className={`absolute left-0 top-1/2 h-6 w-1 -translate-y-1/2 rounded-r-full ${TONE_BAR[tone] ?? "bg-slate-200"}`} />
                {row.text}
              </td>
              <td className="py-3 pr-4 text-slate-500">{row.responsible_role ?? "—"}</td>
              <td className={`py-3 pr-4 font-medium capitalize ${TONE_TEXT[tone] ?? "text-slate-500"}`}>
                {row.priority ?? row.severity ?? "—"}
              </td>
              {hasExtra && <td className="py-3 pr-4 font-mono text-xs text-slate-500">{row.extra ?? "—"}</td>}
              <td className="py-3 pr-5">
                {row.section_id != null && onSectionClick ? (
                  <button
                    onClick={() => onSectionClick(row.section_id!)}
                    className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2.5 py-1 font-mono text-xs text-teal-600 transition hover:bg-teal hover:text-white"
                  >
                    {headingFor(row.section_id)}
                  </button>
                ) : (
                  <span className="font-mono text-xs text-slate-500">{headingFor(row.section_id)}</span>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
