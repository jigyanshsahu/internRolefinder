"use client";

export const jobsPerPage = 100;
export type JobCategory = "sde" | "ai" | "other";
export type Job = {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  country: string | null;
  is_remote: boolean;
  role_type: JobCategory;
  apply_url: string;
};

type JobListProps = {
  jobs: Job[];
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  appliedIds: ReadonlySet<string>;
  actionLabel: string;
  disableAppliedAction: boolean;
  onAction: (job: Job) => void;
};

const label = (role: JobCategory) => ({ sde: "SDE", ai: "AI", other: "Other" })[role];

export default function JobList({ jobs, page, pageCount, onPageChange, appliedIds, actionLabel, disableAppliedAction, onAction }: JobListProps) {
  const firstVisiblePage = Math.max(1, Math.min(page - 2, pageCount - 4));
  const visiblePages = Array.from({ length: Math.min(5, pageCount) }, (_, index) => firstVisiblePage + index);

  return (
    <>
      {jobs.map((job) => {
        const applied = appliedIds.has(job.id);
        return (
          <article className="job" key={job.id}>
            <div>
              <h2>{job.title}</h2>
              {job.company && <p>{job.company}</p>}
              {job.location && <p className="location">{job.location}</p>}
              <span>{label(job.role_type)}</span>
            </div>
            <div className="job-actions">
              <a href={job.apply_url} target="_blank" rel="noopener noreferrer">Apply <span aria-hidden="true">↗</span></a>
              <button className="application-action" disabled={applied && disableAppliedAction} onClick={() => onAction(job)}>
                {applied && disableAppliedAction ? "Applied" : actionLabel}
              </button>
            </div>
          </article>
        );
      })}
      {pageCount > 1 && (
        <nav className="pagination" aria-label="Job pages">
          <button disabled={page === 1} onClick={() => onPageChange(page - 1)}>Previous</button>
          {firstVisiblePage > 1 && <span aria-hidden="true">…</span>}
          {visiblePages.map((visiblePage) => (
            <button key={visiblePage} aria-current={visiblePage === page ? "page" : undefined} className={visiblePage === page ? "selected" : ""} onClick={() => onPageChange(visiblePage)}>
              {visiblePage}
            </button>
          ))}
          {firstVisiblePage + visiblePages.length - 1 < pageCount && <span aria-hidden="true">…</span>}
          <span>Page {page} of {pageCount}</span>
          <button disabled={page === pageCount} onClick={() => onPageChange(page + 1)}>Next</button>
        </nav>
      )}
    </>
  );
}