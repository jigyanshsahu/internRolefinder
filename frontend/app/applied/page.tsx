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

type FilterStageTab = "all" | "active" | "oa" | "interview" | "offer" | "followups_due" | "closed";

function daysBetween(dateStr: string): number {
  try {
    const diffTime = Date.now() - new Date(dateStr).getTime();
    return Math.floor(diffTime / (1000 * 60 * 60 * 24));
  } catch {
    return 0;
  }
}

function isDueOrOverdue(followUpDate?: string, completed?: boolean): boolean {
  if (!followUpDate || completed) return false;
  const today = new Date().toISOString().slice(0, 10);
  return followUpDate <= today;
}

export default function AppliedPage() {
  const [jobs, setJobs] = useState<AppliedJob[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [activeTab, setActiveTab] = useState<FilterStageTab>("all");
  const [copiedEmailJobId, setCopiedEmailJobId] = useState<string | null>(null);
  const [editingNotesJobId, setEditingNotesJobId] = useState<string | null>(null);
  const [noteDraft, setNoteDraft] = useState<string>("");

  useEffect(() => {
    setJobs(readAppliedJobs());
    setLoaded(true);
  }, []);

  useEffect(() => subscribeToAppliedJobChanges(() => setJobs(readAppliedJobs())), []);

  // Filter jobs by selected tab
  const filteredJobs = jobs.filter((job) => {
    if (activeTab === "all") return true;
    if (activeTab === "followups_due") return isDueOrOverdue(job.follow_up_date, job.follow_up_completed);
    if (activeTab === "active") return ["applied", "oa", "screening", "technical", "final"].includes(job.stage);
    if (activeTab === "oa") return job.stage === "oa";
    if (activeTab === "interview") return ["screening", "technical", "final"].includes(job.stage);
    if (activeTab === "offer") return job.stage === "offer";
    if (activeTab === "closed") return ["rejected", "withdrawn"].includes(job.stage);
    return true;
  });

  // Calculate metrics
  const totalApplied = jobs.length;
  const inPipeline = jobs.filter((j) => ["oa", "screening", "technical", "final"].includes(j.stage)).length;
  const offersCount = jobs.filter((j) => j.stage === "offer").length;
  const followUpsDue = jobs.filter((j) => isDueOrOverdue(j.follow_up_date, j.follow_up_completed));

  const handleStageChange = (jobId: string, nextStage: InterviewStage) => {
    updateAppliedJob(jobId, { stage: nextStage });
  };

  const handleSetFollowUpDays = (jobId: string, days: number) => {
    const nextDate = new Date(Date.now() + days * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    updateAppliedJob(jobId, { follow_up_date: nextDate, follow_up_completed: false });
  };

  const handleDateChange = (jobId: string, newDate: string) => {
    updateAppliedJob(jobId, { follow_up_date: newDate, follow_up_completed: false });
  };

  const handleToggleFollowUpCompleted = (job: AppliedJob) => {
    updateAppliedJob(job.id, { follow_up_completed: !job.follow_up_completed });
  };

  const handleInterviewDateChange = (jobId: string, dateVal: string) => {
    updateAppliedJob(jobId, { interview_date: dateVal });
  };

  const handleSaveNotes = (jobId: string) => {
    updateAppliedJob(jobId, { stage_notes: noteDraft });
    setEditingNotesJobId(null);
  };

  const copyFollowUpEmail = (job: AppliedJob) => {
    const days = daysBetween(job.applied_at);
    const emailDraft = `Subject: Following up on application for ${job.title} - [Your Name]

Dear Hiring Team at ${job.company || "the company"},

I hope this email finds you well.

I am writing to politely follow up on my application for the ${job.title} internship position, which I submitted ${
      days > 0 ? `${days} days ago` : "recently"
    } via your direct careers portal.

I remains enthusiastically interested in the opportunity to contribute to ${
      job.company || "your team"
    } and would appreciate any update you might have regarding the status of my application or next steps in the interview process.

Thank you very much for your time, consideration, and support.

Best regards,
[Your Name]
[Your Phone Number]
[Your LinkedIn / Portfolio URL]`;

    navigator.clipboard.writeText(emailDraft);
    setCopiedEmailJobId(job.id);
    setTimeout(() => setCopiedEmailJobId(null), 3000);
  };

  return (
    <main>
      <header className="site-header">
        <p className="eyebrow">Personal Pipeline & Reminders</p>
        <h1>Application Tracker</h1>
        <p className="subtle">
          Record interview stages, follow-up reminders, and candidate notes. Stored locally in your browser.
        </p>

        {/* Pipeline Analytics Cards */}
        <div className="metrics-bar">
          <div className="metric-chip">
            <span className="metric-val">{totalApplied}</span>
            <span className="metric-lbl">Total Applied</span>
          </div>
          <div className="metric-chip">
            <span className="metric-val">{inPipeline}</span>
            <span className="metric-lbl">In Interview Process</span>
          </div>
          <div className="metric-chip">
            <span className="metric-val" style={{ color: followUpsDue.length > 0 ? "#f59e0b" : undefined }}>
              {followUpsDue.length}
            </span>
            <span className="metric-lbl">Follow-ups Due</span>
          </div>
          <div className="metric-chip">
            <span className="metric-val" style={{ color: offersCount > 0 ? "#10b981" : undefined }}>
              {offersCount}
            </span>
            <span className="metric-lbl">Offers Received 🎉</span>
          </div>
        </div>
      </header>

      {/* Navigation Links */}
      <div className="page-links">
        <Link href="/" className="nav-link">
          ← Browse Jobs
        </Link>
        <Link href="/applied" aria-current="page" className="nav-link active">
          Application Tracker ({jobs.length})
        </Link>
      </div>

      {/* Follow-up Reminders Due Alert Banner */}
      {followUpsDue.length > 0 && (
        <div className="reminder-alert-banner">
          <div className="reminder-icon">⏰</div>
          <div className="reminder-content">
            <strong>
              {followUpsDue.length} Application Follow-up{followUpsDue.length > 1 ? "s" : ""} Due Today:
            </strong>
            <p>
              {followUpsDue.map((j) => `${j.company || "Unknown"} (${j.title})`).join(" • ")}
            </p>
          </div>
          <button
            type="button"
            className="btn-filter-followups"
            onClick={() => setActiveTab("followups_due")}
          >
            Review Follow-ups
          </button>
        </div>
      )}

      {/* Stage Filter Tabs */}
      <div className="stage-filter-tabs" role="tablist" aria-label="Application stages">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "all"}
          className={`tab-btn ${activeTab === "all" ? "active" : ""}`}
          onClick={() => setActiveTab("all")}
        >
          All ({totalApplied})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "active"}
          className={`tab-btn ${activeTab === "active" ? "active" : ""}`}
          onClick={() => setActiveTab("active")}
        >
          Active Pipeline ({inPipeline + jobs.filter((j) => j.stage === "applied").length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "oa"}
          className={`tab-btn ${activeTab === "oa" ? "active" : ""}`}
          onClick={() => setActiveTab("oa")}
        >
          Assessments / OA ({jobs.filter((j) => j.stage === "oa").length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "interview"}
          className={`tab-btn ${activeTab === "interview" ? "active" : ""}`}
          onClick={() => setActiveTab("interview")}
        >
          Interviews ({jobs.filter((j) => ["screening", "technical", "final"].includes(j.stage)).length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "offer"}
          className={`tab-btn ${activeTab === "offer" ? "active" : ""}`}
          onClick={() => setActiveTab("offer")}
        >
          Offers ({offersCount})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "followups_due"}
          className={`tab-btn ${activeTab === "followups_due" ? "active warning-tab" : ""}`}
          onClick={() => setActiveTab("followups_due")}
        >
          Follow-ups Due ({followUpsDue.length})
        </button>
      </div>

      <section aria-live="polite" className="applied-list-section">
        {!loaded && <p className="status">Loading saved internships…</p>}

        {loaded && jobs.length === 0 && (
          <div className="status-banner empty">
            <p className="empty-title">No applications tracked yet.</p>
            <p className="empty-desc">
              Browse newly verified roles on the homepage and click &ldquo;Save & Track&rdquo; on any role to start
              tracking your interview stages and follow-up reminders.
            </p>
            <Link href="/" className="btn-primary">
              Explore Active Internships →
            </Link>
          </div>
        )}

        {loaded && jobs.length > 0 && filteredJobs.length === 0 && (
          <div className="status-banner empty">
            <p className="empty-title">No applications in this category.</p>
            <button type="button" className="btn-reset" onClick={() => setActiveTab("all")}>
              Show All Applications
            </button>
          </div>
        )}

        {loaded && filteredJobs.length > 0 && (
          <div className="applied-cards-grid">
            {filteredJobs.map((job) => {
              const stageInfo = STAGE_CONFIG[job.stage] || STAGE_CONFIG.applied;
              const due = isDueOrOverdue(job.follow_up_date, job.follow_up_completed);
              const daysApplied = daysBetween(job.applied_at);

              return (
                <article key={job.id} className={`applied-card ${due ? "card-warning" : ""}`}>
                  {/* Card Header */}
                  <div className="applied-card-header">
                    <div>
                      <h2 className="applied-job-title">{job.title}</h2>
                      <div className="applied-meta-row">
                        {job.company && <span className="job-company">{job.company}</span>}
                        {job.company && <span className="meta-separator">•</span>}
                        <span className="job-location">
                          {job.is_remote ? "Remote" : job.location || job.country || "India"}
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
                        <option value="applied">1. Applied</option>
                        <option value="oa">2. Online Assessment / OA</option>
                        <option value="screening">3. Recruiter Screen</option>
                        <option value="technical">4. Technical Interview</option>
                        <option value="final">5. Final / Behavioral</option>
                        <option value="offer">6. Offer Received 🎉</option>
                        <option value="rejected">Not Selected</option>
                        <option value="withdrawn">Withdrawn</option>
                      </select>
                    </div>
                  </div>

                  {/* Stage Visual Pipeline Stepper */}
                  <div className="stage-stepper-container" aria-label="Interview progress">
                    {(["applied", "oa", "screening", "technical", "offer"] as InterviewStage[]).map((stg) => {
                      const stgConfig = STAGE_CONFIG[stg];
                      const isReached = stageInfo.step >= stgConfig.step && stageInfo.step > 0;
                      const isCurrent = job.stage === stg;
                      return (
                        <div
                          key={stg}
                          className={`step-node ${isReached ? "reached" : ""} ${isCurrent ? "current" : ""}`}
                          title={stgConfig.label}
                        >
                          <div className="step-dot" />
                          <span className="step-label">{stgConfig.short}</span>
                        </div>
                      );
                    })}
                  </div>

                  {/* Interview Date & Schedule Tracker */}
                  <div className="schedule-row">
                    <label className="schedule-label">
                      <span>Interview Scheduled:</span>
                      <input
                        type="datetime-local"
                        className="styled-datetime-input"
                        value={job.interview_date || ""}
                        onChange={(e) => handleInterviewDateChange(job.id, e.target.value)}
                      />
                    </label>
                  </div>

                  {/* Follow-up Reminder Module */}
                  <div className={`followup-module ${due ? "module-due" : ""}`}>
                    <div className="followup-header">
                      <span className="module-title">
                        {due ? "⚠️ Follow-up Due:" : "Follow-up Reminder:"}
                      </span>
                      <label className="followup-check-label">
                        <input
                          type="checkbox"
                          checked={Boolean(job.follow_up_completed)}
                          onChange={() => handleToggleFollowUpCompleted(job)}
                        />
                        <span>{job.follow_up_completed ? "Completed ✓" : "Mark as done"}</span>
                      </label>
                    </div>

                    <div className="followup-controls">
                      <input
                        type="date"
                        className="styled-date-input"
                        value={job.follow_up_date || ""}
                        onChange={(e) => handleDateChange(job.id, e.target.value)}
                      />
                      <div className="quick-days-group">
                        <button
                          type="button"
                          className="btn-quick-day"
                          onClick={() => handleSetFollowUpDays(job.id, 3)}
                          title="Remind in 3 days"
                        >
                          +3d
                        </button>
                        <button
                          type="button"
                          className="btn-quick-day"
                          onClick={() => handleSetFollowUpDays(job.id, 7)}
                          title="Remind in 7 days"
                        >
                          +7d
                        </button>
                        <button
                          type="button"
                          className="btn-quick-day"
                          onClick={() => handleSetFollowUpDays(job.id, 14)}
                          title="Remind in 14 days"
                        >
                          +14d
                        </button>
                      </div>

                      <button
                        type="button"
                        className={`btn-copy-email ${copiedEmailJobId === job.id ? "copied" : ""}`}
                        onClick={() => copyFollowUpEmail(job)}
                        title="Generate and copy a professional follow-up email"
                      >
                        {copiedEmailJobId === job.id ? "✓ Copied Draft!" : "✉ Copy Follow-up Email"}
                      </button>
                    </div>
                  </div>

                  {/* Notes & Interview Feedback Drawer */}
                  <div className="notes-section">
                    {editingNotesJobId === job.id ? (
                      <div className="notes-editor">
                        <textarea
                          placeholder="Record interview notes, questions asked, recruiter contacts, or feedback…"
                          value={noteDraft}
                          onChange={(e) => setNoteDraft(e.target.value)}
                          className="notes-textarea"
                          rows={3}
                        />
                        <div className="notes-actions">
                          <button
                            type="button"
                            className="btn-save-notes"
                            onClick={() => handleSaveNotes(job.id)}
                          >
                            Save Note
                          </button>
                          <button
                            type="button"
                            className="btn-cancel-notes"
                            onClick={() => setEditingNotesJobId(null)}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="notes-display">
                        {job.stage_notes ? (
                          <div className="existing-note">
                            <span className="note-text">&ldquo;{job.stage_notes}&rdquo;</span>
                            <button
                              type="button"
                              className="btn-edit-note"
                              onClick={() => {
                                setNoteDraft(job.stage_notes || "");
                                setEditingNotesJobId(job.id);
                              }}
                            >
                              Edit Note
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className="btn-add-note"
                            onClick={() => {
                              setNoteDraft("");
                              setEditingNotesJobId(job.id);
                            }}
                          >
                            + Add interview feedback / notes
                          </button>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Bottom Actions Row */}
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