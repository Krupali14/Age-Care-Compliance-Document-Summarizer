import { useNavigate } from "react-router-dom";

const features = [
  {
    title: "Summarise instantly",
    description:
      "Upload any compliance document and get a clear, structured summary in seconds — no more skimming hundred-page PDFs.",
  },
  {
    title: "Extract obligations & risks",
    description:
      "Automatically surface regulatory obligations and flag risk areas so nothing slips through the cracks.",
  },
  {
    title: "Track deadlines & actions",
    description:
      "Every date and required action is pulled out and tracked, keeping your team ahead of compliance deadlines.",
  },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-b from-brand-50 to-white text-slate-900">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <span className="text-lg font-semibold tracking-tight text-brand-700">
          Aged Care Compliance Summariser
        </span>
        <button
          onClick={() => navigate("/dashboard")}
          className="rounded-md border border-brand-600 px-4 py-2 text-sm font-medium text-brand-700 transition hover:bg-brand-50"
        >
          Sign in
        </button>
      </header>

      <main className="mx-auto max-w-4xl px-6 pt-16 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          Compliance Documents, <span className="text-brand-600">Understood in Minutes</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-slate-600">
          Our AI reads your aged-care compliance documents so you don't have to — using
          NLP to summarise content and automatically extract obligations, risks, deadlines,
          and action items your team needs to track.
        </p>
        <button
          onClick={() => navigate("/dashboard")}
          className="mt-10 rounded-lg bg-brand-600 px-8 py-3 text-base font-semibold text-white shadow-lg shadow-brand-600/20 transition hover:bg-brand-700"
        >
          Explore Platform
        </button>
      </main>

      <section className="mx-auto mt-24 grid max-w-5xl gap-8 px-6 pb-24 sm:grid-cols-3">
        {features.map((f) => (
          <div
            key={f.title}
            className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition hover:shadow-md"
          >
            <h3 className="text-base font-semibold text-brand-700">{f.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">{f.description}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
