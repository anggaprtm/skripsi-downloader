import { useHealth } from "../hooks/useJobs";

export default function Header() {
  const { data, isError } = useHealth();
  const online = !isError && data?.status === "ok";
  const ocrReady = data?.tesseract;

  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-xl border border-amber/30 bg-ink-700 shadow-glow">
          <svg className="h-6 w-6 text-amber" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.5C9.5 5 6.5 5 4 6v12c2.5-1 5.5-1 8 .5 2.5-1.5 5.5-1.5 8-.5V6c-2.5-1-5.5-1-8 .5z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.5v13" />
          </svg>
        </div>
        <div>
          <h1 className="font-display text-xl font-700 leading-none tracking-tight text-white">
            Skripsi <span className="text-amber">Downloader</span>
          </h1>
          <p className="mt-1 font-mono text-[11px] tracking-wide text-slate-500">
            flipbook repository → searchable pdf
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span className="flex items-center gap-2 rounded-lg border border-line bg-ink-700/60 px-3 py-1.5 text-xs">
          <span className={`h-2 w-2 rounded-full ${online ? "bg-good" : "bg-bad"}`} />
          <span className="text-slate-300">{online ? "Backend aktif" : "Backend mati"}</span>
        </span>
        <span
          className={`rounded-lg border px-3 py-1.5 text-xs ${
            ocrReady ? "border-teal/30 text-teal" : "border-line text-slate-500"
          }`}
          title={ocrReady ? "Tesseract terpasang" : "OCR tidak tersedia"}
        >
          OCR {ocrReady ? "siap" : "—"}
        </span>
      </div>
    </header>
  );
}
