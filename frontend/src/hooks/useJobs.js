import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ACTIVE_STATUSES, api } from "../api/client";

const JOBS_KEY = ["jobs"];

export function useJobs() {
  return useQuery({
    queryKey: JOBS_KEY,
    queryFn: api.listJobs,
    // Poll every 2s while any job is still running, otherwise back off.
    refetchInterval: (query) => {
      const jobs = query.state.data?.jobs || [];
      const active = jobs.some((j) => ACTIVE_STATUSES.has(j.status));
      return active ? 2000 : 10000;
    },
    refetchOnWindowFocus: true,
  });
}

export function useCreateDownload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createDownload,
    onSuccess: () => qc.invalidateQueries({ queryKey: JOBS_KEY }),
  });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteJob,
    onSuccess: () => qc.invalidateQueries({ queryKey: JOBS_KEY }),
  });
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 30000,
    retry: false,
  });
}
