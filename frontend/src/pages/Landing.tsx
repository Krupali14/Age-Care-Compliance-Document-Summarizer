import { useRef } from "react";
import { useNavigate } from "react-router-dom";

const steps = [
  { n: "01", title: "Upload", body: "Drop in a PDF or DOCX compliance report — policy, incident review, audit finding, anything." },
  { n: "02", title: "Extract", body: "The model reads it section by section and pulls obligations, risks, deadlines, and actions — each tied back to its source." },
  { n: "03", title: "Act", body: "Review a structured record instead of a hundred-page document, and verify every claim against the original text." },
];

const features = [
  {
    title: "Obligation extraction",
    description: "Every requirement the standards place on your facility, surfaced automatically and linked to its clause.",
  },
  {
    title: "Risk triage",
    description: "High, medium, and low severity flagged at a glance, so the serious ones don't wait for a full read-through.",
  },
  {
    title: "Deadlines & owners",
    description: "Every date and responsible role pulled out and tracked, so nothing quietly passes its due date.",
  },
];

export default function Landing() {
  const navigate = useNavigate();
  const stackRef = useRef<HTMLDivElement>(null);

  function handleStackMove(e: React.MouseEvent<HTMLDivElement>) {
    const el = stackRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    el.style.setProperty("--rx", `${py * -8}deg`);
    el.style.setProperty("--ry", `${px * 10}deg`);
  }

  function resetStack() {
    stackRef.current?.style.setProperty("--rx", "0deg");
    stackRef.current?.style.setProperty("--ry", "0deg");
  }

  return (
    <div className="min-h-screen bg-parchment text-ink">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <span className="flex items-center gap-2 font-display text-lg font-semibold tracking-tight">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-ink text-xs font-mono text-parchment">§</span>
          Compliance Summariser
        </span>
        <button
          onClick={() => navigate("/login")}
          className="rounded-md border border-ink/15 px-4 py-2 text-sm font-medium text-ink transition hover:border-ink/30 hover:bg-white"
        >
          Sign in
        </button>
      </header>

      <main className="mx-auto grid max-w-6xl items-center gap-12 px-6 pb-24 pt-8 lg:grid-cols-[1.05fr_0.95fr] lg:gap-8 lg:pt-16">
        <div className="animate-fade-up">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-teal">Aged care compliance, read for you</p>
          <h1 className="mt-4 font-display text-5xl font-semibold leading-[1.05] tracking-tight sm:text-6xl">
            Every obligation,
            <br />
            <span className="relative inline-block">
              found in minutes.
              <svg className="absolute -bottom-1 left-0 w-full" height="8" viewBox="0 0 300 8" preserveAspectRatio="none">
                <path d="M1 5.5C60 1.5 240 1.5 299 5.5" stroke="#0E7C7B" strokeWidth="3" fill="none" strokeLinecap="round" />
              </svg>
            </span>
          </h1>
          <p className="mt-6 max-w-md text-lg leading-relaxed text-slate-500">
            Upload a compliance document and get its obligations, risks, deadlines, and action items —
            structured, source-linked, and verified against the standards your facility answers to.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <button
              onClick={() => navigate("/login")}
              className="rounded-lg bg-ink px-7 py-3.5 text-base font-semibold text-parchment shadow-card transition hover:-translate-y-0.5 hover:shadow-card-hover"
            >
              Get started
            </button>
            <button
              onClick={() => navigate("/login")}
              className="rounded-lg border border-ink/15 px-7 py-3.5 text-base font-medium text-ink transition hover:bg-white"
            >
              Sign in
            </button>
          </div>
        </div>

        {/* Signature: layered document stack, hand-read into structure */}
        <div
          className="[perspective:1200px]"
          onMouseMove={handleStackMove}
          onMouseLeave={resetStack}
        >
          <div
            ref={stackRef}
            className="relative mx-auto h-80 w-full max-w-sm transition-transform duration-300 ease-out [transform:rotateX(var(--rx,0deg))_rotateY(var(--ry,0deg))] [transform-style:preserve-3d]"
            style={{ "--rx": "0deg", "--ry": "0deg" } as React.CSSProperties}
          >
            <div className="absolute inset-4 translate-x-3 translate-y-6 rotate-[6deg] rounded-xl bg-ink/10" />
            <div className="absolute inset-4 translate-x-1.5 translate-y-3 -rotate-[3deg] rounded-xl bg-ink/20" />
            <div className="absolute inset-4 overflow-hidden rounded-xl bg-white shadow-stack">
              <div className="border-b border-ink/10 px-5 py-3">
                <p className="font-mono text-[10px] uppercase tracking-wider text-slate-400">Doc Ref · IC-2026-0143</p>
                <p className="mt-1 text-sm font-semibold">Incident &amp; Compliance Review</p>
              </div>
              <div className="space-y-2.5 px-5 py-4">
                {[
                  { label: "Obligation", tone: "bg-teal", w: "w-11/12" },
                  { label: "Risk · High", tone: "bg-coral", w: "w-9/12" },
                  { label: "Deadline · 24h", tone: "bg-amber", w: "w-10/12" },
                  { label: "Action item", tone: "bg-sage", w: "w-8/12" },
                ].map((row) => (
                  <div key={row.label} className="flex items-center gap-2.5">
                    <span className={`h-2 w-2 shrink-0 rounded-full ${row.tone}`} />
                    <span className={`h-2.5 ${row.w} rounded-full bg-ink/10`} />
                  </div>
                ))}
              </div>
              <div className="pointer-events-none absolute inset-x-0 top-0 h-16 animate-scan bg-gradient-to-b from-teal/0 via-teal/10 to-teal/0" />
            </div>
          </div>
        </div>
      </main>

      <section className="border-y border-ink/10 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <h2 className="font-mono text-xs font-normal uppercase tracking-[0.2em] text-teal">How it works</h2>
          <div className="mt-8 grid gap-10 sm:grid-cols-3">
            {steps.map((s, i) => (
              <div key={s.n} className="relative">
                <span className="font-display text-4xl font-medium text-ink/15">{s.n}</span>
                <h3 className="mt-2 font-display text-xl font-semibold">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-500">{s.body}</p>
                {i < steps.length - 1 && (
                  <span className="absolute right-[-1.25rem] top-2 hidden text-ink/15 sm:block">→</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-20" aria-labelledby="features-heading">
        <h2 id="features-heading" className="sr-only">What it extracts</h2>
        <div className="grid gap-6 sm:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="group rounded-xl border border-ink/10 bg-white p-6 shadow-card transition hover:-translate-y-1 hover:shadow-card-hover"
            >
              <div className="h-1 w-8 rounded-full bg-teal transition-all duration-300 group-hover:w-14" />
              <h3 className="mt-4 font-display text-lg font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-500">{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-ink/10 px-6 py-8 text-center text-xs text-slate-400">
        Decision-support only — verify every result against the source document.
      </footer>
    </div>
  );
}
