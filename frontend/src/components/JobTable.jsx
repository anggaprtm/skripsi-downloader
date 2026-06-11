import { useState } from "react";
import { api } from "../api/client";
import { useDeleteJob, useJobs } from "../hooks/useJobs";
import { useToast } from "./Toast";
import ProgressBar from "./ProgressBar";
import StatusBadge from "./StatusBadge";

function timeAgo(ts) {
  const seconds = Math.floor(Date.now() / 1000 - ts);
  if (seconds < 60) return "baru saja";
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins} mnt lalu`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} jam lalu`;
  return `${Math.floor(hours / 24)} hr lalu`;
}

function formatSize(bytes) {
  if (!bytes) return "—";
  const mb = bytes / 1024 / 1024;
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${(bytes / 1024).toFixed(0)} KB`;
}

function formatDuration(startTs) {
  if (!startTs) return null;
  const secs = Math.floor(Date.now() / 1000 - startTs);
  if (secs < 60) return `${secs}d`;
  return `${Math.floor(secs / 60)}m ${secs % 60}d`;
}

function pageLabel(job) {
  if (job.status === "downloading" && job.total_pages) {
    return `Hal. ${job.current_page} / ${job.total_pages}`;
  }
  if (job.total_pages) return `${job.total_pages} hal.`;
  return "—";
}

// Mini OCR progress bar shown inline in the detail panel
function OcrDetail({ job }) {
  if (job.status !== "running_ocr") return null;
  const total = job.ocr_total_pages || job.total_pages || 0;
  const current = job.ocr_current_page || 0;
  const pct = total > 0 ? Math.round((current / total) * 100) : 0;
  const elapsed = formatDuration(job.ocr_start_time);

  return (
    <div className="mt-3 space-y-2 rounded-xl border border-teal/20 bg-ink-900/60 p-3">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[11px] uppercase tracking-wider text-teal/80">
          Detail OCR
        </span>
        <span className="font-mono text-xs text-slate-400">
          {elapsed && `${elapsed} berlalu`}
        </span>
      </div>

      {/* Per-page progress */}
      <div className="flex items-center gap-3">
        <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-ink-600">
          <div
            className="h-full rounded-full bg-gradient-to-r from-teal/60 to-teal transition-[width] duration-300"
            style={{ width: `${pct}%` }}
          >
            <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/20 to-transparent" />
          </div>
        </div>
        <span className="w-24 shrink-0 text-right font-mono text-xs tabular-nums text-teal">
          {current} / {total} hal.
        </span>
      </div>

      {/* Stage label */}
      {job.ocr_stage && (
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-teal opacity-50" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-teal" />
          </span>
          <span className="font-mono text-xs text-slate-300">{job.ocr_stage}</span>
        </div>
      )}
    </div>
  );
}

function Actions({ job }) {
  const del = useDeleteJob();
  const toast = useToast();
  const done = job.status === "completed";

  return (
    <div className="flex items-center justify-end gap-2">
      {done && (
        <a
          href={api.downloadUrl(job.job_id)}
          className="btn-ghost border-amber/40 text-amber-soft"
          download
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
          </svg>
          PDF {job.file_size ? `(${formatSize(job.file_size)})` : ""}
        </a>
      )}
      <button
        onClick={() =>
          del.mutate(job.job_id, {
            onSuccess: () => toast.info("Job dihapus."),
            onError: (e) => toast.error(e.message),
          })
        }
        className="btn-ghost hover:border-bad/40 hover:text-bad"
        aria-label="Hapus job"
      >
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-1 12a2 2 0 01-2 2H8a2 2 0 01-2-2L5 7m3 0V5a2 2 0 012-2h4a2 2 0 012 2v2m-7 4v6m4-6v6" />
        </svg>
      </button>
    </div>
  );
}

function JobRow({ job }) {
  const isOcr = job.status === "running_ocr";
  const [expanded, setExpanded] = useState(false);
  const showDetail = isOcr || expanded;

  return (
    <>
      <tr
        className="border-b border-line/60 last:border-0 hover:bg-ink-700/30 cursor-pointer"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="max-w-[240px] px-5 py-3">
          <p className="truncate font-medium text-slate-100" title={job.title || job.job_id}>
            {job.title || "Tanpa judul"}
          </p>
          <p className={`mt-0.5 truncate font-mono text-[11px] ${job.error ? "text-bad" : "text-slate-500"}`}>
            {job.error ? job.error : job.message}
          </p>
        </td>
        <td className="px-3 py-3">
          <StatusBadge status={job.status} />
        </td>
        <td className="whitespace-nowrap px-3 py-3 font-mono text-xs text-slate-400">
          {pageLabel(job)}
        </td>
        <td className="px-3 py-3 w-52">
          <ProgressBar value={job.progress} status={job.status} />
          {isOcr && job.ocr_total_pages > 0 && (
            <p className="mt-1 font-mono text-[10px] text-teal/80 tabular-nums">
              OCR {job.ocr_current_page}/{job.ocr_total_pages} hal.
              {job.ocr_stage ? ` · ${job.ocr_stage}` : ""}
            </p>
          )}
        </td>
        <td className="whitespace-nowrap px-3 py-3 text-xs text-slate-500">
          {timeAgo(job.created_at)}
        </td>
        <td className="px-5 py-3" onClick={(e) => e.stopPropagation()}>
          <Actions job={job} />
        </td>
      </tr>

      {/* Expandable detail row */}
      {showDetail && (
        <tr className="border-b border-line/40 bg-ink-900/40">
          <td colSpan={6} className="px-5 py-1 pb-3">
            <OcrDetail job={job} />
            {!isOcr && expanded && (
              <div className="mt-2 font-mono text-xs text-slate-500">
                Job ID: {job.job_id}
                {job.file_size > 0 && <span className="ml-4">Ukuran: {formatSize(job.file_size)}</span>}
                {job.ocr && <span className="ml-4">OCR: {job.languages}</span>}
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function MobileCard({ job }) {
  const isOcr = job.status === "running_ocr";

  return (
    <div className="space-y-3 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-medium text-slate-100">{job.title || "Tanpa judul"}</p>
          <p className="mt-0.5 font-mono text-[11px] text-slate-500">
            {pageLabel(job)} · {timeAgo(job.created_at)} · {formatSize(job.file_size)}
          </p>
        </div>
        <StatusBadge status={job.status} />
      </div>

      {/* Main progress */}
      <ProgressBar value={job.progress} status={job.status} />

      {/* OCR detail on mobile */}
      {isOcr && <OcrDetail job={job} />}

      {job.error && <p className="text-xs text-bad">{job.error}</p>}
      <Actions job={job} />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-16 text-center">
      <div className="grid h-14 w-14 place-items-center rounded-2xl border border-line bg-ink-700">
        <svg className="h-7 w-7 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.6">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.6L19 9.4V19a2 2 0 01-2 2z" />
        </svg>
      </div>
      <p className="font-display text-base text-slate-300">Belum ada job</p>
      <p className="max-w-xs text-sm text-slate-500">
        Tempel URL flipbook di atas untuk membuat PDF skripsi yang bisa dicari.
      </p>
    </div>
  );
}

export default function JobTable() {
  const { data, isLoading, isError } = useJobs();
  const jobs = data?.jobs || [];

  return (
    <section className="panel overflow-hidden">
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <span className="eyebrow">Antrean job</span>
        <span className="font-mono text-xs text-slate-500">{jobs.length} total</span>
      </div>

      {isLoading ? (
        <div className="px-6 py-16 text-center font-mono text-sm text-slate-500">Memuat…</div>
      ) : isError ? (
        <div className="px-6 py-16 text-center text-sm text-bad">
          Tidak bisa terhubung ke backend. Cek apakah service berjalan.
        </div>
      ) : jobs.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          {/* Desktop table */}
          <table className="hidden w-full md:table">
            <thead>
              <tr className="border-b border-line text-left font-mono text-[11px] uppercase tracking-wider text-slate-500">
                <th className="px-5 py-3 font-medium">Judul</th>
                <th className="px-3 py-3 font-medium">Status</th>
                <th className="px-3 py-3 font-medium">Halaman</th>
                <th className="w-52 px-3 py-3 font-medium">Progress</th>
                <th className="px-3 py-3 font-medium">Dibuat</th>
                <th className="px-5 py-3 text-right font-medium">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <JobRow key={job.job_id} job={job} />
              ))}
            </tbody>
          </table>

          {/* Mobile cards */}
          <div className="divide-y divide-line/60 md:hidden">
            {jobs.map((job) => (
              <MobileCard key={job.job_id} job={job} />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
