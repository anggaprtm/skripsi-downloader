import DownloadForm from "./components/DownloadForm";
import Header from "./components/Header";
import JobTable from "./components/JobTable";

export default function App() {
  return (
    <div className="mx-auto flex min-h-full max-w-4xl flex-col gap-7 px-4 py-8 sm:px-6 sm:py-12">
      <Header />

      <section className="space-y-2">
        <h2 className="font-display text-2xl font-600 leading-tight tracking-tight text-white sm:text-[28px]">
          Ubah flipbook repository jadi{" "}
          <span className="bg-gradient-to-r from-amber to-amber-soft bg-clip-text text-transparent">
            PDF yang bisa dicari
          </span>
        </h2>
        <p className="max-w-2xl text-sm leading-relaxed text-slate-400">
          Tempel URL <span className="font-mono text-slate-300">index.html</span> dari koleksi
          digital Universitas Airlangga. Sistem mengunduh tiap halaman, menyusunnya jadi satu PDF,
          lalu menjalankan OCR (Indonesia + Inggris) agar teksnya bisa dicari dan disalin.
        </p>
      </section>

      <DownloadForm />
      <JobTable />

      <footer className="mt-auto flex flex-col items-center gap-1 pt-6 text-center text-xs text-slate-600">
        <p className="font-mono">
          FastAPI · Redis · RQ · Tesseract · React — untuk keperluan akademik & arsip pribadi
        </p>
        <p>Hormati hak cipta penulis dan ketentuan repository saat menggunakan dokumen.</p>
      </footer>
    </div>
  );
}
