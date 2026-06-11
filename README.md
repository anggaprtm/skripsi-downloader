# Skripsi Downloader

Download FlipBuilder / Flip PDF flipbooks from the Universitas Airlangga
digital repository and convert them into a single **searchable OCR PDF**.

Paste a repository `index.html` URL → the system fetches the flipbook config,
downloads every page (large quality when available, mobile otherwise), merges
them into a PDF, and optionally runs OCR (Indonesian + English) so the text
becomes selectable and searchable.

> Untuk keperluan akademik dan arsip pribadi. Selalu hormati hak cipta penulis
> dan ketentuan repository. Jangan menyalahgunakan untuk distribusi ulang.

---

## Architecture

```
┌────────────┐     POST /api/download     ┌────────────┐     enqueue      ┌────────────┐
│  Frontend  │ ─────────────────────────► │  Backend   │ ───────────────► │   Redis    │
│ React+Vite │ ◄───── GET /api/jobs ────  │  FastAPI   │                  │   (RQ)     │
└────────────┘        (poll 2s)           └────────────┘                  └─────┬──────┘
                                                                                │ pop
                                                                          ┌─────▼──────┐
                                                                          │   Worker   │
                                                                          │ download → │
                                                                          │ pdf → ocr  │
                                                                          └────────────┘
```

| Service    | Stack                                            | Port (host) |
| ---------- | ------------------------------------------------ | ----------- |
| `frontend` | React, Vite, TailwindCSS, React Query, nginx     | `8080`      |
| `backend`  | FastAPI, Uvicorn                                 | `8000`      |
| `worker`   | RQ worker (downloader, img2pdf, OCRmyPDF)        | —           |
| `redis`    | Redis 7 (queue + job state)                      | internal    |

---

## Quick start (Docker — recommended)

Requirements: Docker + Docker Compose plugin.

```bash
git clone <your-repo> skripsi-downloader
cd skripsi-downloader

cp .env.example .env        # adjust if needed
docker compose up -d --build
```

Then open:

- **App:** http://localhost:8080
- **API docs (Swagger):** http://localhost:8000/docs

Stop everything:

```bash
docker compose down          # keep data
docker compose down -v       # also wipe redis + generated PDFs
```

The first build downloads the Tesseract Indonesian/English language packs, so
it may take a few minutes.

---

## How to use

1. Open the flipbook in the repository and copy the `index.html` URL, e.g.

   ```
   https://ir.unair.ac.id/uploaded_files/temporary/DigitalCollection/XXXXX/index.html
   ```

2. Paste it into the command bar.
3. Toggle **Aktifkan OCR** on/off and pick the language (`ind+eng`, `ind`, `eng`).
4. Press **Mulai unduh** (or `⌘/Ctrl + Enter`).
5. Watch the job progress live in the table (`Downloading page 43 / 143` →
   `Generating PDF` → `Running OCR` → `Completed`).
6. Click **PDF** to download the result.

Jobs and generated files are kept for **24 hours**, then cleaned up automatically.

---

## API

| Method   | Endpoint                   | Description                          |
| -------- | -------------------------- | ------------------------------------ |
| `POST`   | `/api/download`            | Create a job. Body: `{ url, ocr, languages }` → `{ job_id }` |
| `GET`    | `/api/jobs`                | List all jobs                        |
| `GET`    | `/api/jobs/{id}`           | Job status & progress                |
| `GET`    | `/api/jobs/{id}/download`  | Download the finished PDF            |
| `DELETE` | `/api/jobs/{id}`           | Remove a job and its file            |
| `GET`    | `/api/health`              | Redis + Tesseract availability       |

Example job status response:

```json
{
  "job_id": "f1a2...",
  "status": "downloading",
  "progress": 35,
  "current_page": 43,
  "total_pages": 143,
  "title": "Analisis ...",
  "ocr": true,
  "download_url": null
}
```

---

## Local development (without Docker)

You still need **Redis**, **Tesseract** (with `ind` + `eng`), **Ghostscript**
and **qpdf** installed on the host.

### Backend

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Terminal 1 — API
uvicorn app.main:app --reload --port 8000

# Terminal 2 — worker
python worker.py
```

Make sure Redis is running locally (`redis-server`) and `REDIS_URL` points to it.

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api → :8000)
```

---

## Linux deployment (bare metal / VPS)

```bash
# 1. System dependencies (Debian/Ubuntu)
sudo apt update
sudo apt install -y python3.12 python3.12-venv redis-server \
    ocrmypdf tesseract-ocr tesseract-ocr-ind tesseract-ocr-eng \
    ghostscript qpdf nodejs npm nginx

sudo systemctl enable --now redis-server

# 2. Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Build frontend
cd ../frontend && npm install && npm run build
# serve ./dist with nginx and proxy /api to 127.0.0.1:8000
```

Run the API and worker under a process manager (systemd, supervisor, pm2):

```ini
# /etc/systemd/system/skripsi-api.service
[Service]
WorkingDirectory=/opt/skripsi-downloader/backend
ExecStart=/opt/skripsi-downloader/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

# /etc/systemd/system/skripsi-worker.service
[Service]
WorkingDirectory=/opt/skripsi-downloader/backend
ExecStart=/opt/skripsi-downloader/backend/.venv/bin/python worker.py
Restart=always
```

The simplest production path remains `docker compose up -d --build`.

---

## Environment variables

| Variable                   | Default                     | Description                                     |
| -------------------------- | --------------------------- | ----------------------------------------------- |
| `BACKEND_PORT`             | `8000`                      | Host port for the API                           |
| `FRONTEND_PORT`            | `8080`                      | Host port for the web app                       |
| `CORS_ORIGINS`             | localhost origins           | Comma-separated allowed browser origins         |
| `REDIS_URL`                | `redis://localhost:6379/0`  | Redis connection string                         |
| `QUEUE_NAME`               | `skripsi`                   | RQ queue name                                   |
| `JOB_TIMEOUT`              | `3600`                      | Max seconds a job may run                        |
| `JOB_TTL`                  | `86400`                     | Result retention in Redis (seconds)             |
| `STORAGE_ROOT`             | `/data`                     | Root for `downloads/`, `jobs/`, `temp/`         |
| `JOB_RETENTION_HOURS`      | `24`                        | Auto-cleanup window                             |
| `DEFAULT_DOWNLOAD_THREADS` | `20`                        | Concurrent page downloads                       |
| `DOWNLOAD_RETRIES`         | `3`                         | Retries per page                                |
| `DOWNLOAD_TIMEOUT`         | `30`                        | Per-request timeout (seconds)                   |
| `DEFAULT_OCR_LANGUAGES`    | `ind+eng`                   | Fallback OCR languages                          |
| `OCR_JOBS`                 | `2`                         | Parallel Tesseract jobs                         |

---

## Troubleshooting

**`Could not locate config.js` / `Could not detect totalPageCount`**
The URL must point at the flipbook's `index.html` (or its folder). Open the
flipbook in a browser first and confirm it loads, then copy that exact URL.

**`Could not locate page images (large or mobile)`**
The repository uses a non-standard image path. The downloader probes
`files/large/`, `files/mobile/`, `files/page/` and the paths declared in
`config.js`. If yours differs, add it to `_resolve_template` in
`backend/app/downloader.py`.

**OCR shows `—` / `ocrmypdf not installed`**
Tesseract/OCRmyPDF aren't present. In Docker this is handled automatically;
locally install `ocrmypdf tesseract-ocr tesseract-ocr-ind tesseract-ocr-eng`.
You can still produce a non-searchable PDF by leaving OCR off.

**Jobs stay in `Antre` (queued) forever**
The worker isn't running or can't reach Redis. Check `docker compose logs worker`
and that `REDIS_URL` is correct.

**Backend mati / `Tidak bisa terhubung ke backend`**
Confirm the API container is up (`docker compose ps`) and that
`CORS_ORIGINS` includes the frontend origin.

**Downloads are slow or the repository rate-limits you**
Lower `DEFAULT_DOWNLOAD_THREADS` (e.g. to `8`) to be gentler on the server.

**`PDF too large` through nginx**
`client_max_body_size` is set to `200m` in `frontend/nginx.conf`; raise it if
your scans are bigger.

---

## Project structure

```
skripsi-downloader/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app & routes
│   │   ├── config.py        # settings (pydantic-settings)
│   │   ├── models.py        # Job model + JobStatus
│   │   ├── schemas.py       # request/response schemas
│   │   ├── queue.py         # Redis + RQ
│   │   ├── downloader.py    # config.js parse + page download
│   │   ├── pdf.py           # img2pdf assembly
│   │   ├── ocr.py           # ocrmypdf wrapper
│   │   ├── jobs.py          # pipeline orchestration
│   │   ├── storage.py       # Redis job store + filesystem
│   │   └── utils.py         # logging & helpers
│   ├── worker.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # React + Vite + Tailwind
├── docker/redis.conf
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## License

Provided as-is for academic and personal archival use. You are responsible for
complying with copyright and the source repository's terms of service.
