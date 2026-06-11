export default function ProgressBar({ value = 0, status }) {
  const pct = Math.max(0, Math.min(100, value));
  const active = status && status !== "completed" && status !== "failed";
  const failed = status === "failed";
  const done = status === "completed";

  const fill = failed ? "bg-bad/70" : done ? "bg-good" : "bg-gradient-to-r from-amber-deep to-amber";

  return (
    <div className="flex items-center gap-3">
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-ink-600">
        <div
          className={`h-full rounded-full transition-[width] duration-500 ease-out ${fill}`}
          style={{ width: `${failed ? 100 : pct}%` }}
        >
          {active && (
            <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/25 to-transparent" />
          )}
        </div>
      </div>
      <span className="w-10 shrink-0 text-right font-mono text-xs tabular-nums text-slate-400">
        {failed ? "—" : `${pct}%`}
      </span>
    </div>
  );
}
