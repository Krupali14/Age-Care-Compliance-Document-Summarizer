function Placeholder({ title }: { title: string }) {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
      <div className="mt-6 rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
        This section is coming soon.
      </div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
      <p className="mt-2 text-slate-600">
        Select a section from the sidebar to get started.
      </p>
    </div>
  );
}

export function UploadSection() {
  return <Placeholder title="Upload" />;
}

export function SummariesSection() {
  return <Placeholder title="Summaries" />;
}

export function ObligationsRisksSection() {
  return <Placeholder title="Obligations & Risks" />;
}

export function DeadlinesSection() {
  return <Placeholder title="Deadlines" />;
}

export function ActionItemsSection() {
  return <Placeholder title="Action Items" />;
}
