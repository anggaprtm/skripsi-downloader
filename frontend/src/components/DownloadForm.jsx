import { useState } from "react";
import { useCreateDownload } from "../hooks/useJobs";
import { useToast } from "./Toast";

const URL_HINT =
  "https://ir.unair.ac.id/uploaded_files/temporary/DigitalCollection/XXXXX/index.html";

export default function DownloadForm() {
  const [url, setUrl] = useState("");
  const [ocr, setOcr] = useState(true);
  const [languages, setLanguages] = useState("ind+eng");
  const create = useCreateDownload();
  const toast = useToast();

  const submit = () => {
    const value = url.trim();
    if (!value) {
      toast.error("Tempel dulu URL flipbook-nya.");
      return;
    }
    if (!/^https?:\/\//i.test(value)) {
      toast.error("URL harus diawali http:// atau https://");
      return;
    }
    create.mutate(
      { url: value, ocr, languages: ocr ? languages : "ind+eng" },
      {
        onSuccess: () => {
          toast.success("Job dibuat. Lihat progresnya di tabel.");
          setUrl("");
        },
        onError: (err) => toast.error(err.message),
      }
    );
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
  };

  return (
    <section className="panel p-5 sm:p-7">
      <div className="mb-4 flex items-center gap-2">
        <span className="eyebrow">Tempel URL repository</span>
        <span className="h-px flex-1 bg-line" />
      </div>

      {/* Command bar */}
      <div className="group relative flex items-center gap-2 rounded-xl border border-line bg-ink-900/70 px-3 transition focus-within:border-amber/60 focus-within:shadow-glow">
        <span className="select-none font-mono text-sm text-amber/70">$</span>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={URL_HINT}
          spellCheck={false}
          autoComplete="off"
          className="w-full bg-transparent py-3 font-mono text-sm text-slate-100 placeholder:text-slate-600 outline-none"
        />
      </div>

      <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-4">
          {/* OCR toggle */}
          <button
            type="button"
            role="switch"
            aria-checked={ocr}
            onClick={() => setOcr((v) => !v)}
            className="flex items-center gap-2.5 text-sm text-slate-300"
          >
            <span
              className={`relative h-5 w-9 rounded-full border transition ${
                ocr ? "border-amber/50 bg-amber/30" : "border-line bg-ink-600"
              }`}
            >
              <span
                className={`absolute top-0.5 h-3.5 w-3.5 rounded-full transition-all ${
                  ocr ? "left-[18px] bg-amber" : "left-0.5 bg-slate-400"
                }`}
              />
            </span>
            Aktifkan OCR
          </button>

          {/* Language select */}
          <label
            className={`flex items-center gap-2 text-sm transition ${
              ocr ? "text-slate-300" : "pointer-events-none opacity-40"
            }`}
          >
            <span className="text-slate-500">Bahasa</span>
            <select
              value={languages}
              onChange={(e) => setLanguages(e.target.value)}
              disabled={!ocr}
              className="rounded-lg border border-line bg-ink-700 px-2.5 py-1.5 font-mono text-xs text-slate-200 outline-none focus:border-amber/50"
            >
              <option value="ind+eng">ind + eng</option>
              <option value="ind">ind</option>
              <option value="eng">eng</option>
            </select>
          </label>
        </div>

        <button onClick={submit} disabled={create.isPending} className="btn-primary">
          {create.isPending ? (
            <>
              <Spinner /> Menambahkan…
            </>
          ) : (
            <>
              Mulai unduh
              <kbd className="rounded bg-ink-900/30 px-1.5 py-0.5 font-mono text-[10px] text-ink-900/70">
                ⌘↵
              </kbd>
            </>
          )}
        </button>
      </div>
    </section>
  );
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z" />
    </svg>
  );
}
