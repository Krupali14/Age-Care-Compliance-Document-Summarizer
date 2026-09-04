import { Link } from "react-router-dom";

/**
 * Anything the router doesn't recognise used to render an empty white page, which
 * reads as a crash and leaves no way back.
 */
export default function NotFound({
  code = "404",
  title = "Page not found",
  message = "That page doesn't exist, or the link that brought you here is out of date.",
  to = "/dashboard",
  linkLabel = "Back to documents",
}: {
  code?: string;
  title?: string;
  message?: string;
  to?: string;
  linkLabel?: string;
}) {
  return (
    <div className="mx-auto max-w-md px-6 py-20 text-center">
      <p className="font-mono text-xs uppercase tracking-wider text-slate-400">{code}</p>
      <h1 className="mt-2 font-display text-2xl font-semibold text-ink">{title}</h1>
      <p className="mt-2 text-sm leading-relaxed text-slate-500">{message}</p>
      <Link
        to={to}
        className="mt-6 inline-flex rounded-md bg-ink px-4 py-2 text-sm font-medium text-parchment shadow-card transition hover:-translate-y-0.5"
      >
        {linkLabel}
      </Link>
    </div>
  );
}
