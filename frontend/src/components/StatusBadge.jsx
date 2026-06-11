const CONFIG = {
  queued: { label: "Antre", dot: "bg-slate-400", text: "text-slate-300", ring: "border-slate-600" },
  downloading: { label: "Mengunduh", dot: "bg-info", text: "text-info", ring: "border-info/40", live: true },
  building_pdf: { label: "Menyusun PDF", dot: "bg-amber", text: "text-amber", ring: "border-amber/40", live: true },
  running_ocr: { label: "Menjalankan OCR", dot: "bg-teal", text: "text-teal", ring: "border-teal/40", live: true },
  completed: { label: "Selesai", dot: "bg-good", text: "text-good", ring: "border-good/40" },
  failed: { label: "Gagal", dot: "bg-bad", text: "text-bad", ring: "border-bad/40" },
};

export default function StatusBadge({ status }) {
  const c = CONFIG[status] || CONFIG.queued;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${c.ring} bg-ink-900/60 px-2.5 py-1 text-xs font-medium ${c.text}`}
    >
      <span className="relative flex h-2 w-2">
        {c.live && (
          <span className={`absolute inline-flex h-full w-full rounded-full ${c.dot} opacity-60 animate-pulse-ring`} />
        )}
        <span className={`relative inline-flex h-2 w-2 rounded-full ${c.dot}`} />
      </span>
      {c.label}
    </span>
  );
}
