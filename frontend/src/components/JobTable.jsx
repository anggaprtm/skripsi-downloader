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

function pageLabel(job) {
  if (job.status === "downloading" && job.total_pages) {
    return `Hal. ${job.current_page} / ${job.total_pages}`;
  }
  if (job.total_pages) return `${job.total_pages} hal.`;
  return "—";
}

function Actions({ job }) {
  const del = useDeleteJob();
  const toast = useToast();
  const done = job.status === "completed";

  return (
    <div className="flex items-center justify-end gap-2">
      {done && (
        <a href={api.downloadUrl(job.job_id)} className="btn-ghost border-amber/40 text-amber-soft" download>
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
          </svg>
          PDF
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
        <div className="flex items-center gap-2">
          <span className="eyebrow">Antrean job</span>
        </div>
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
                <th className="w-56 px-3 py-3 font-medium">Progress</th>
                <th className="px-3 py-3 font-medium">Dibuat</th>
                <th className="px-5 py-3 text-right font-medium">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.job_id} className="border-b border-line/60 last:border-0 hover:bg-ink-700/30">
                  <td className="max-w-[260px] px-5 py-4">
                    <p className="truncate font-medium text-slate-100" title={job.title || job.job_id}>
                      {job.title || "Tanpa judul"}
                    </p>
                    {job.error ? (
                      <p className="mt-0.5 truncate text-xs text-bad" title={job.error}>
                        {job.error}
                      </p>
                    ) : (
                      <p className="mt-0.5 truncate font-mono text-[11px] text-slate-600">
                        {job.message}
                      </p>
                    )}
                  </td>
                  <td className="px-3 py-4">
                    <StatusBadge status={job.status} />
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 font-mono text-xs text-slate-400">
                    {pageLabel(job)}
                  </td>
                  <td className="px-3 py-4">
                    <ProgressBar value={job.progress} status={job.status} />
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-xs text-slate-500">
                    {timeAgo(job.created_at)}
                  </td>
                  <td className="px-5 py-4">
                    <Actions job={job} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Mobile cards */}
          <div className="divide-y divide-line/60 md:hidden">
            {jobs.map((job) => (
              <div key={job.job_id} className="space-y-3 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-100">{job.title || "Tanpa judul"}</p>
                    <p className="mt-0.5 font-mono text-[11px] text-slate-500">
                      {pageLabel(job)} · {timeAgo(job.created_at)} · {formatSize(job.file_size)}
                    </p>
                  </div>
                  <StatusBadge status={job.status} />
                </div>
                <ProgressBar value={job.progress} status={job.status} />
                {job.error && <p className="text-xs text-bad">{job.error}</p>}
                <Actions job={job} />
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
