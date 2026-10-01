import type { Job } from "./components/JobList";

const storageKey = "intern-role-finder-applied-jobs";
const changeEvent = "intern-role-finder-applied-jobs-change";

export function readAppliedJobs(): Job[] {
  try {
    const storedJobs: unknown = JSON.parse(window.localStorage.getItem(storageKey) ?? "[]");
    if (!Array.isArray(storedJobs)) return [];
    const validJobs = storedJobs.filter((job) =>
      typeof job?.id === "string" &&
      typeof job?.title === "string" &&
      (typeof job?.company === "string" || job?.company === null) &&
      (job?.location === undefined || typeof job?.location === "string" || job?.location === null) &&
      typeof job?.role_type === "string" &&
      ["sde", "ai", "full_stack", "frontend", "backend", "web_engineer"].includes(job.role_type) &&
      typeof job?.apply_url === "string"
    );
    return validJobs.map((job) => ({
      ...job,
      location: job.location ?? null,
      country: job.country ?? null,
      is_remote: typeof job.is_remote === "boolean" ? job.is_remote : Boolean(job.location?.toLowerCase().includes("remote")),
      role_type: job.role_type === "ai" ? "ai" : "sde",
    }));
  } catch {
    return [];
  }
}

export function saveAppliedJobs(jobs: Job[]) {
  window.localStorage.setItem(storageKey, JSON.stringify(jobs));
  window.dispatchEvent(new Event(changeEvent));
}

export function subscribeToAppliedJobChanges(callback: () => void) {
  window.addEventListener(changeEvent, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(changeEvent, callback);
    window.removeEventListener("storage", callback);
  };
}