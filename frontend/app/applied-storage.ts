import type { Job } from "./components/JobList";

export type InterviewStage =
  | "applied"
  | "oa"
  | "screening"
  | "technical"
  | "final"
  | "offer"
  | "rejected"
  | "withdrawn";

export type AppliedJob = Job & {
  applied_at: string;
  stage: InterviewStage;
  stage_updated_at: string;
  stage_notes?: string;
  interview_date?: string;
  interview_notes?: string;
  follow_up_date?: string;
  follow_up_completed?: boolean;
  salary_or_stipend?: string;
};

const storageKey = "intern-role-finder-applied-jobs";
const changeEvent = "intern-role-finder-applied-jobs-change";

export const STAGE_CONFIG: Record<
  InterviewStage,
  { label: string; short: string; color: string; bg: string; border: string; step: number }
> = {
  applied: {
    label: "Applied",
    short: "Applied",
    color: "#87a9ff",
    bg: "rgba(56, 103, 232, 0.15)",
    border: "rgba(135, 169, 255, 0.3)",
    step: 1,
  },
  oa: {
    label: "Online Assessment / OA",
    short: "OA",
    color: "#f59e0b",
    bg: "rgba(245, 158, 11, 0.15)",
    border: "rgba(245, 158, 11, 0.3)",
    step: 2,
  },
  screening: {
    label: "Recruiter Screen",
    short: "Screen",
    color: "#38bdf8",
    bg: "rgba(56, 189, 248, 0.15)",
    border: "rgba(56, 189, 248, 0.3)",
    step: 3,
  },
  technical: {
    label: "Technical Round",
    short: "Tech",
    color: "#a855f7",
    bg: "rgba(168, 85, 247, 0.15)",
    border: "rgba(168, 85, 247, 0.3)",
    step: 4,
  },
  final: {
    label: "Final / Behavioral",
    short: "Final",
    color: "#ec4899",
    bg: "rgba(236, 72, 153, 0.15)",
    border: "rgba(236, 72, 153, 0.3)",
    step: 5,
  },
  offer: {
    label: "Offer Received 🎉",
    short: "Offer",
    color: "#10b981",
    bg: "rgba(16, 185, 129, 0.2)",
    border: "rgba(16, 185, 129, 0.4)",
    step: 6,
  },
  rejected: {
    label: "Not Selected",
    short: "Rejected",
    color: "#ef4444",
    bg: "rgba(239, 68, 68, 0.15)",
    border: "rgba(239, 68, 68, 0.3)",
    step: 0,
  },
  withdrawn: {
    label: "Withdrawn",
    short: "Withdrawn",
    color: "#94a3b8",
    bg: "rgba(148, 163, 184, 0.15)",
    border: "rgba(148, 163, 184, 0.3)",
    step: 0,
  },
};

export function readAppliedJobs(): AppliedJob[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(storageKey);
    const storedJobs: unknown = JSON.parse(raw ?? "[]");
    if (!Array.isArray(storedJobs)) return [];

    const validJobs = storedJobs.filter(
      (job) =>
        typeof job?.id === "string" &&
        typeof job?.title === "string" &&
        (typeof job?.company === "string" || job?.company === null) &&
        typeof job?.apply_url === "string"
    );

    return validJobs.map((job) => {
      const isRemote =
        typeof job.is_remote === "boolean"
          ? job.is_remote
          : Boolean(job.location?.toLowerCase().includes("remote"));

      const defaultFollowUp = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
        .toISOString()
        .slice(0, 10);

      return {
        id: job.id,
        title: job.title,
        company: job.company ?? null,
        location: job.location ?? null,
        country: job.country ?? null,
        is_remote: isRemote,
        role_type: job.role_type === "ai" ? "ai" : "sde",
        apply_url: job.apply_url,
        description: job.description ?? null,
        first_seen_at: job.first_seen_at,
        last_checked_at: job.last_checked_at,
        posted_at: job.posted_at ?? null,
        fit_score: typeof job.fit_score === "number" ? job.fit_score : undefined,
        matched_skills: Array.isArray(job.matched_skills) ? job.matched_skills : [],
        applied_at: typeof job.applied_at === "string" ? job.applied_at : new Date().toISOString(),
        stage: (["applied", "oa", "screening", "technical", "final", "offer", "rejected", "withdrawn"].includes(
          job.stage
        )
          ? job.stage
          : "applied") as InterviewStage,
        stage_updated_at:
          typeof job.stage_updated_at === "string" ? job.stage_updated_at : new Date().toISOString(),
        stage_notes: typeof job.stage_notes === "string" ? job.stage_notes : "",
        interview_date: typeof job.interview_date === "string" ? job.interview_date : undefined,
        interview_notes: typeof job.interview_notes === "string" ? job.interview_notes : "",
        follow_up_date:
          typeof job.follow_up_date === "string" ? job.follow_up_date : defaultFollowUp,
        follow_up_completed: Boolean(job.follow_up_completed),
        salary_or_stipend: typeof job.salary_or_stipend === "string" ? job.salary_or_stipend : "",
      };
    });
  } catch {
    return [];
  }
}

export function saveAppliedJobs(jobs: AppliedJob[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(storageKey, JSON.stringify(jobs));
  window.dispatchEvent(new Event(changeEvent));
}

export function addAppliedJob(job: Job) {
  const current = readAppliedJobs();
  if (current.some((item) => item.id === job.id)) return;
  const defaultFollowUp = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const newEntry: AppliedJob = {
    ...job,
    applied_at: new Date().toISOString(),
    stage: "applied",
    stage_updated_at: new Date().toISOString(),
    stage_notes: "",
    interview_date: undefined,
    interview_notes: "",
    follow_up_date: defaultFollowUp,
    follow_up_completed: false,
    salary_or_stipend: "",
  };
  saveAppliedJobs([...current, newEntry]);
}

export function updateAppliedJob(id: string, updates: Partial<AppliedJob>) {
  const current = readAppliedJobs();
  const next = current.map((item) => {
    if (item.id !== id) return item;
    const stageChanged = updates.stage && updates.stage !== item.stage;
    return {
      ...item,
      ...updates,
      stage_updated_at: stageChanged ? new Date().toISOString() : item.stage_updated_at,
    };
  });
  saveAppliedJobs(next);
}

export function removeAppliedJob(id: string) {
  const current = readAppliedJobs();
  saveAppliedJobs(current.filter((item) => item.id !== id));
}

export function subscribeToAppliedJobChanges(callback: () => void) {
  if (typeof window === "undefined") return () => {};
  window.addEventListener(changeEvent, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(changeEvent, callback);
    window.removeEventListener("storage", callback);
  };
}