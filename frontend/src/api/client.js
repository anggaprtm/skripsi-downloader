import axios from "axios";

const baseURL = import.meta.env.VITE_API_URL || "/api";

const http = axios.create({ baseURL, timeout: 20000 });

function extractError(error) {
  const detail = error?.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(", ");
  if (typeof detail === "string") return detail;
  return error?.message || "Something went wrong.";
}

export const api = {
  async createDownload({ url, ocr, languages }) {
    try {
      const { data } = await http.post("/download", { url, ocr, languages });
      return data; // { job_id }
    } catch (error) {
      throw new Error(extractError(error));
    }
  },

  async listJobs() {
    const { data } = await http.get("/jobs");
    return data; // { jobs, total }
  },

  async getJob(id) {
    const { data } = await http.get(`/jobs/${id}`);
    return data;
  },

  async deleteJob(id) {
    const { data } = await http.delete(`/jobs/${id}`);
    return data;
  },

  async health() {
    const { data } = await http.get("/health");
    return data;
  },

  downloadUrl(id) {
    return `${baseURL}/jobs/${id}/download`;
  },
};

export const ACTIVE_STATUSES = new Set([
  "queued",
  "downloading",
  "building_pdf",
  "running_ocr",
]);
