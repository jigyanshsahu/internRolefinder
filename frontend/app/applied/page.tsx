"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  type AppliedJob,
  type InterviewStage,
  STAGE_CONFIG,
  readAppliedJobs,
  removeAppliedJob,
  subscribeToAppliedJobChanges,
  updateAppliedJob,
} from "../applied-storage";

function daysBetween(dateStr: string): number {
  try {
    const diffTime = Date.now() - new Date(dateStr).getTime();
    return Math.floor(diffTime / (1000 * 60 * 60 * 24));
  } catch {
    return 0;
  }
}

export default function AppliedPage() {
  const [jobs, setJobs] = useState<AppliedJob[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setJobs(readAppliedJobs());
    setLoaded(true);
  }, []);

  useEffect(() => subscribeToAppliedJobChanges(() => setJobs(readAppliedJobs())), []);

  const handleStageChange = (jobId: string, nextStage: InterviewStage) => {
    updateAppliedJob(jobId, { stage: nextStage });
  };

  return (
    <main>
      <header className="site-header">
        <p className="eyebrow">Personal Tracking</p>
        <div className="header-title-row">
          <div>
            <h1>Application Tracker</h1>
            <p className="subtle">
              Manage your saved applications and update your interview status. Saved locally in your browser.
            </p>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <div className="page-links">
        <Link href="/" className="nav-link">
          ← Browse Jobs
        </Link>
        <Link href="/applied" aria-current="page" className="nav-link active">
          Saved Applications ({jobs.length})
        </Link>
      </div>

      <section aria-live="polite" className="applied-list-section">
        {!loaded && (
          <div className="loading-state">
            <div className="spinner" />
            <p className="status">Loading saved internships…</p>
          </div>
        )}

        {loaded && jobs.length === 0 && (
          <div className="status-banner empty">
            <p className="empty-title">No applications tracked yet.</p>
            <p className="empty-desc">
              Browse newly verified roles on the homepage and click &ldquo;Save & Track&rdquo; on any role to keep track of it here.
            </p>
            <Link href="/" className="btn-primary" style={{ marginTop: 12, display: "inline-block" }}>
              Explore Active Internships →
            </Link>
          </div>
        )}

        {loaded && jobs.length > 0 && (
          <div className="applied-cards-grid">
            {jobs.map((job) => {
              const stageInfo = STAGE_CONFIG[job.stage] || STAGE_CONFIG.applied;
              const daysApplied = daysBetween(job.applied_at);

              return (
                <article key={job.id} className="applied-card">
                  <div className="applied-card-header">
                    <div>
                      <h2 className="applied-job-title">{job.title}</h2>
                      <div className="applied-meta-row">
                        {job.company && <span className="job-company">{job.company}</span>}
                        {job.company && <span className="meta-separator">•</span>}
                        <span className="job-location">
                          {job.is_remote ? "Remote" : job.location || job.country || "On-site"}
                        </span>
                        <span className="meta-separator">•</span>
                        <span className="days-applied-text">
                          Applied {daysApplied === 0 ? "today" : `${daysApplied}d ago`}
                        </span>
                      </div>
                    </div>

                    <div className="stage-badge-selector">
                      <select
                        aria-label={`Interview stage for ${job.title}`}
                        className="stage-select-dropdown"
                        style={{
                          color: stageInfo.color,
                          backgroundColor: stageInfo.bg,
                          borderColor: stageInfo.border,
                        }}
                        value={job.stage}
                        onChange={(e) => handleStageChange(job.id, e.target.value as InterviewStage)}
                      >
                        <option value="applied">Applied</option>
                        <option value="oa">Online Assessment (OA)</option>
                        <option value="screening">Recruiter Screening</option>
                        <option value="technical">Technical Round</option>
                        <option value="final">Final Round</option>
                        <option value="offer">Offer Received 🎉</option>
                        <option value="rejected">Not Selected</option>
                        <option value="withdrawn">Withdrawn</option>
                      </select>
                    </div>
                  </div>

                  <div className="card-footer-actions">
                    <a
                      href={job.apply_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-revisit"
                      title="Reopen employer job application"
                    >
                      View Posting <span aria-hidden="true">↗</span>
                    </a>
                    <button
                      type="button"
                      className="btn-remove"
                      onClick={() => removeAppliedJob(job.id)}
                      title="Remove from tracking"
                    >
                      Remove
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}