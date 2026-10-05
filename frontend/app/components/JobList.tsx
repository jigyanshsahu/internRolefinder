"use client";

import { useState } from "react";

export const jobsPerPage = 20;
export type JobCategory = "sde" | "frontend" | "backend" | "full_stack";

export type Job = {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  country: string | null;
  is_remote: boolean;
  is_startup?: boolean;
  ats_type?: string | null;
  career_url?: string | null;
  role_type: JobCategory;
  apply_url: string;
  description?: string | null;
  first_seen_at?: string;
  last_checked_at?: string;
  posted_at?: string | null;
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
  onInvalidate?: (job: Job) => void;
};

const ROLE_BADGES: Record<JobCategory, { label: string; badgeClass: string }> = {
  sde: { label: "SDE Intern", badgeClass: "badge-sde" },
  frontend: { label: "Frontend Intern", badgeClass: "badge-frontend" },
  backend: { label: "Backend Intern", badgeClass: "badge-backend" },
  full_stack: { label: "Fullstack Intern", badgeClass: "badge-fullstack" },
};

function isNewlyVerified(dateString?: string): boolean {
  if (!dateString) return false;
  try {
    const diffHours = (Date.now() - new Date(dateString).getTime()) / (1000 * 60 * 60);
    return diffHours >= 0 && diffHours <= 48;
  } catch {
    return false;
  }
}

export default function JobList({
  jobs,
  page,
  pageCount,
  onPageChange,
  appliedIds,
  actionLabel,
  disableAppliedAction,
  onAction,
  onInvalidate,
}: JobListProps) {
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);

  const firstVisiblePage = Math.max(1, Math.min(page - 2, pageCount - 4));
  const visiblePages = Array.from(
    { length: Math.min(5, pageCount) },
    (_, index) => firstVisiblePage + index
  );

  return (
    <div className="job-list-container">
      {jobs.map((job) => {
        const applied = appliedIds.has(job.id);
        const isNew = isNewlyVerified(job.first_seen_at);
        const isExpanded = expandedJobId === job.id;
        const roleInfo = ROLE_BADGES[job.role_type] ?? {
          label: "SDE Intern",
          badgeClass: "badge-sde",
        };

        const locationLabel = job.is_remote
          ? job.location?.toLowerCase().includes("remote")
            ? job.location
            : `Remote${job.location ? ` · ${job.location}` : job.country ? ` · ${job.country}` : ""}`
          : job.location;
        const isIndian =
          job.country === "India" ||
          Boolean(
            job.location &&
              /\b(india|bengaluru|bangalore|hyderabad|mumbai|delhi|gurgaon|gurugram|noida|pune|chennai|kolkata|ahmedabad|jaipur|kochi|indore)\b/i.test(
                job.location
              ) &&
              !job.location.toLowerCase().includes("indianapolis")
          );

        return (
          <article className={`job-card ${applied ? "job-applied" : ""} ${job.is_startup ? "card-startup" : ""}`} key={job.id}>
            <div className="job-main-info">
              <div className="job-header-row">
                <div className="job-title-group">
                  <h2 className="job-title">
                    <a
                      href={job.apply_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="job-title-link"
                      title="Open official job listing"
                    >
                      {job.title}
                    </a>
                  </h2>
                  <div className="job-meta-row">
                    {job.company && <span className="job-company">{job.company}</span>}
                    {job.company && locationLabel && <span className="meta-separator">•</span>}
                    {locationLabel && (
                      <span className={`job-location ${job.is_remote ? "remote-pill" : ""}`}>
                        {job.is_remote && <span className="remote-dot" aria-hidden="true" />}
                        {locationLabel}
                      </span>
                    )}
                  </div>
                </div>

                <div className="badges-group">
                  {job.is_startup && (
                    <span className="badge badge-startup" title="High-growth startup with high interview callback rate">
                      🚀 Startup · High Callback
                    </span>
                  )}
                  {isIndian && <span className="badge badge-india">🇮🇳 India</span>}
                  {job.ats_type && (
                    <span
                      className={`badge badge-ats ${job.ats_type === "Direct Portal" ? "badge-direct-portal" : ""}`}
                      title={job.ats_type === "Direct Portal" ? "Official direct employer career portal - highest response rate" : "Direct employer ATS form - verified authentic link"}
                    >
                      {job.ats_type === "Direct Portal" ? "⚡ Direct Portal" : `✓ ${job.ats_type}`}
                    </span>
                  )}
                  {isNew && <span className="badge badge-new">✨ New</span>}
                  {job.is_remote && <span className="badge badge-remote">Remote</span>}
                  <span className={`badge badge-role ${roleInfo.badgeClass}`}>
                    {roleInfo.label}
                  </span>
                </div>
              </div>

              {job.description && (
                <div className="job-desc-section">
                  <button
                    type="button"
                    className="toggle-desc-btn"
                    onClick={() => setExpandedJobId(isExpanded ? null : job.id)}
                    aria-expanded={isExpanded}
                  >
                    {isExpanded ? "Hide overview ▲" : "View role details ▼"}
                  </button>
                  {isExpanded && (
                    <div className="job-expanded-desc">
                      <p>{job.description.slice(0, 800)}...</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="job-actions">
              <a
                href={job.apply_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-apply"
                title={
                  job.ats_type === "Direct Portal"
                    ? "Open official job listing on company career portal"
                    : `Open official job application on ${job.ats_type || "ATS"}`
                }
              >
                Apply Direct <span aria-hidden="true">↗</span>
              </a>

              {job.career_url && job.career_url !== job.apply_url && (
                <a
                  href={job.career_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-career-portal"
                  title={`Open official ${job.company || "company"} career page (browse all current openings)`}
                >
                  Career Page <span aria-hidden="true">↗</span>
                </a>
              )}
              <button
                type="button"
                className={`application-action ${applied ? "btn-applied" : "btn-mark"}`}
                disabled={applied && disableAppliedAction}
                onClick={() => onAction(job)}
                title="Mark this role as applied and track it in Applied Tracker"
              >
                {applied && disableAppliedAction ? "✓ Applied" : actionLabel}
              </button>
              {onInvalidate && (
                <button
                  type="button"
                  className="btn-invalidate"
                  onClick={() => onInvalidate(job)}
                  title="Report this listing as closed, expired, or broken to invalidate and remove it immediately"
                >
                  <span aria-hidden="true">⚑</span> Invalidate
                </button>
              )}
            </div>
          </article>
        );
      })}

      {pageCount > 1 && (
        <nav className="pagination" aria-label="Job pagination">
          <button
            type="button"
            className="pagination-nav-btn"
            disabled={page === 1}
            onClick={() => onPageChange(page - 1)}
          >
            ← Previous
          </button>
          {firstVisiblePage > 1 && <span className="pagination-ellipsis" aria-hidden="true">…</span>}
          {visiblePages.map((visiblePage) => (
            <button
              type="button"
              key={visiblePage}
              aria-current={visiblePage === page ? "page" : undefined}
              className={`pagination-num-btn ${visiblePage === page ? "selected" : ""}`}
              onClick={() => onPageChange(visiblePage)}
            >
              {visiblePage}
            </button>
          ))}
          {firstVisiblePage + visiblePages.length - 1 < pageCount && (
            <span className="pagination-ellipsis" aria-hidden="true">…</span>
          )}
          <span className="pagination-summary">
            Page {page} of {pageCount}
          </span>
          <button
            type="button"
            className="pagination-nav-btn"
            disabled={page === pageCount}
            onClick={() => onPageChange(page + 1)}
          >
            Next →
          </button>
        </nav>
      )}
    </div>
  );
}