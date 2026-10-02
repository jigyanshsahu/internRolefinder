"use client";

import { useState } from "react";

export const jobsPerPage = 20;
export type JobCategory = "sde" | "ai";

export type Job = {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  country: string | null;
  is_remote: boolean;
  role_type: JobCategory;
  apply_url: string;
  description?: string | null;
  first_seen_at?: string;
  last_checked_at?: string;
  posted_at?: string | null;
  fit_score?: number | null;
  matched_skills?: string[];
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
  activeSkills?: string[];
};

const label = (role: JobCategory) => ({ sde: "SDE", ai: "AI" })[role];

function isNewlyVerified(dateString?: string): boolean {
  if (!dateString) return false;
  try {
    const diffHours = (Date.now() - new Date(dateString).getTime()) / (1000 * 60 * 60);
    return diffHours >= 0 && diffHours <= 36;
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
  activeSkills = [],
}: JobListProps) {
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);

  const firstVisiblePage = Math.max(1, Math.min(page - 2, pageCount - 4));
  const visiblePages = Array.from({ length: Math.min(5, pageCount) }, (_, index) => firstVisiblePage + index);

  return (
    <div className="job-list-container">
      {jobs.map((job) => {
        const applied = appliedIds.has(job.id);
        const isNew = isNewlyVerified(job.first_seen_at);
        const isExpanded = expandedJobId === job.id;

        const locationLabel = job.is_remote
          ? job.location?.toLowerCase().includes("remote")
            ? job.location
            : `Remote${job.location ? ` · ${job.location}` : job.country ? ` · ${job.country}` : ""}`
          : job.location ?? job.country;

        const fit = job.fit_score ?? null;
        const fitColorClass =
          fit && fit >= 85
            ? "fit-high"
            : fit && fit >= 65
            ? "fit-medium"
            : "fit-standard";

        return (
          <article className={`job-card ${applied ? "job-applied" : ""}`} key={job.id}>
            <div className="job-main-info">
              <div className="job-header-row">
                <div className="job-title-group">
                  <h2 className="job-title">{job.title}</h2>
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
                  {isNew && <span className="badge badge-new">✨ Newly Verified</span>}
                  {job.is_remote && <span className="badge badge-remote">Remote</span>}
                  <span className={`badge badge-role ${job.role_type}`}>{label(job.role_type)}</span>
                  {typeof fit === "number" && (
                    <span className={`badge badge-fit ${fitColorClass}`} title="Calculated fit score">
                      ⚡ {fit}% Fit
                    </span>
                  )}
                </div>
              </div>

              {/* Matched skills chips */}
              {job.matched_skills && job.matched_skills.length > 0 && (
                <div className="matched-skills-row">
                  <span className="skills-label">Skill matches:</span>
                  {job.matched_skills.map((skill) => (
                    <span key={skill} className="skill-pill matched">
                      ✓ {skill}
                    </span>
                  ))}
                </div>
              )}

              {/* Description preview toggle */}
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
                      <p>{job.description.slice(0, 700)}...</p>
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
                title="Open employer application"
              >
                Apply <span aria-hidden="true">↗</span>
              </a>
              <button
                className={`application-action ${applied ? "btn-applied" : "btn-mark"}`}
                disabled={applied && disableAppliedAction}
                onClick={() => onAction(job)}
              >
                {applied && disableAppliedAction ? "✓ Saved" : actionLabel}
              </button>
            </div>
          </article>
        );
      })}

      {pageCount > 1 && (
        <nav className="pagination" aria-label="Job pages">
          <button
            className="pagination-nav-btn"
            disabled={page === 1}
            onClick={() => onPageChange(page - 1)}
          >
            ← Previous
          </button>
          {firstVisiblePage > 1 && <span className="pagination-ellipsis" aria-hidden="true">…</span>}
          {visiblePages.map((visiblePage) => (
            <button
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
          <span className="pagination-summary">Page {page} of {pageCount}</span>
          <button
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