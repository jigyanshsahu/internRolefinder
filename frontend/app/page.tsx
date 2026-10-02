"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import JobList, { jobsPerPage, type Job, type JobCategory } from "./components/JobList";
import { addAppliedJob, readAppliedJobs, subscribeToAppliedJobChanges } from "./applied-storage";

type Role = JobCategory;
type JobsResponse = { items: Job[]; page: number; page_size: number; total: number; total_pages: number };
type SummaryResponse = { sde: number; ai: number; total_remote: number; total_active: number };
type AlertsResponse = { items: Job[]; total_new: number; last_checked_at: string };

const POPULAR_SKILLS = [
  "Python",
  "React",
  "TypeScript",
  "Next.js",
  "Node.js",
  "Go",
  "Java",
  "PyTorch",
  "LLMs",
  "Docker",
  "SQL",
  "C++",
];

const LOCATION_OPTIONS = [
  { key: "any_remote", label: "Any Remote" },
  { key: "india", label: "India Remote & Hubs" },
  { key: "international", label: "International" },
  { key: "all", label: "All Locations (Inc. On-site)" },
];

const DATES_OPTIONS = [
  { key: "all", label: "All Terms" },
  { key: "summer_2026", label: "Summer 2026" },
  { key: "immediate", label: "Immediate / Spring" },
  { key: "fall_2026", label: "Fall 2026" },
  { key: "winter_2027", label: "Winter 2027" },
];

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [role, setRole] = useState<Role>("sde");
  const [remoteOnly, setRemoteOnly] = useState<boolean>(true);
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState<string>("");
  const [locationEligibility, setLocationEligibility] = useState<string>("any_remote");
  const [internshipDates, setInternshipDates] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"priority" | "fit" | "freshness">("priority");

  const [page, setPage] = useState(1);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [appliedJobsCount, setAppliedJobsCount] = useState(0);
  const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set());
  const [applicationsLoaded, setApplicationsLoaded] = useState(false);

  const [alerts, setAlerts] = useState<Job[]>([]);
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);

  const [queryReady, setQueryReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Endpoint construction with all active filters
  const endpoint = useMemo(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(jobsPerPage),
      role_type: role,
      remote_only: String(remoteOnly),
      sort_by: selectedSkills.length > 0 && sortBy === "priority" ? "fit" : sortBy,
    });
    if (selectedSkills.length > 0) {
      params.set("skills", selectedSkills.join(","));
    }
    if (locationEligibility && locationEligibility !== "all") {
      params.set("location_eligibility", locationEligibility);
    }
    if (internshipDates && internshipDates !== "all") {
      params.set("internship_dates", internshipDates);
    }
    return `${apiUrl}/api/jobs?${params.toString()}`;
  }, [page, role, remoteOnly, selectedSkills, locationEligibility, internshipDates, sortBy]);

  // Sync initial state from URL query
  useEffect(() => {
    const syncFromUrl = () => {
      const params = new URLSearchParams(window.location.search);
      const queryPage = Number(params.get("page"));
      const queryRole = params.get("role_type");
      const queryRemote = params.get("remote_only");
      const querySkills = params.get("skills");
      const queryLocation = params.get("location_eligibility");
      const queryDates = params.get("internship_dates");
      const querySort = params.get("sort_by") as "priority" | "fit" | "freshness";

      setPage(Number.isInteger(queryPage) && queryPage > 0 ? queryPage : 1);
      setRole(queryRole === "ai" ? "ai" : "sde");
      // Default to remoteOnly = true unless explicitly set to false
      setRemoteOnly(queryRemote === "false" ? false : true);
      if (querySkills) {
        setSelectedSkills(querySkills.split(",").map((s) => s.trim()).filter(Boolean));
      }
      if (queryLocation) setLocationEligibility(queryLocation);
      if (queryDates) setInternshipDates(queryDates);
      if (querySort) setSortBy(querySort);
    };

    syncFromUrl();
    setQueryReady(true);
    window.addEventListener("popstate", syncFromUrl);
    return () => window.removeEventListener("popstate", syncFromUrl);
  }, []);

  // Check Web Notifications permission
  useEffect(() => {
    if (typeof window !== "undefined" && "Notification" in window) {
      setNotificationsEnabled(Notification.permission === "granted");
    }
  }, []);

  // Load applied jobs
  useEffect(() => {
    const updateLocalApplied = () => {
      const stored = readAppliedJobs();
      setAppliedJobsCount(stored.length);
      setAppliedIds(new Set(stored.map((job) => job.id)));
      setApplicationsLoaded(true);
    };
    updateLocalApplied();
    return subscribeToAppliedJobChanges(updateLocalApplied);
  }, []);

  // Fetch summary counts and newly verified alerts
  useEffect(() => {
    fetch(`${apiUrl}/api/jobs/summary?remote_only=${remoteOnly}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data: SummaryResponse | null) => {
        if (data) setSummary(data);
      })
      .catch(() => {});

    fetch(`${apiUrl}/api/jobs/alerts?role_type=${role}&remote_only=${remoteOnly}&hours=24`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data: AlertsResponse | null) => {
        if (data) {
          setAlerts(data.items);
          if (notificationsEnabled && data.items.length > 0 && "Notification" in window) {
            new Notification(`InternRoleFinder: ${data.items.length} new verified roles!`, {
              body: `${data.items[0].title} at ${data.items[0].company || "Verified Startup"} is now open.`,
              icon: "/favicon.ico",
            });
          }
        }
      })
      .catch(() => {});
  }, [role, remoteOnly, notificationsEnabled]);

  // Fetch jobs for current query
  useEffect(() => {
    if (!queryReady) return;
    let active = true;
    const controller = new AbortController();
    setLoading(true);
    setError("");

    fetch(endpoint, { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error("Could not load jobs."))))
      .then((data: JobsResponse) => {
        if (!active) return;
        setJobs(data.items);
        setTotal(data.total);
        setTotalPages(data.total_pages);
        if (data.page !== page) {
          setPage(data.page);
        }
      })
      .catch((reason: Error) => {
        if (active && reason.name !== "AbortError") setError(reason.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [endpoint, page, queryReady]);

  // Push state to URL
  const pushUrlState = (
    overrides: Record<string, string | number | boolean | string[] | null | undefined>
  ) => {
    const params = new URLSearchParams(window.location.search);
    params.set("page", String(overrides.page ?? page));
    params.set("role_type", String(overrides.role ?? role));
    params.set("remote_only", String(overrides.remoteOnly ?? remoteOnly));

    const nextSkills = Array.isArray(overrides.skills)
      ? (overrides.skills as string[])
      : selectedSkills;
    if (nextSkills.length > 0) {
      params.set("skills", nextSkills.join(","));
    } else {
      params.delete("skills");
    }

    const nextLoc = overrides.location !== undefined ? (overrides.location as string) : locationEligibility;
    if (nextLoc && nextLoc !== "all") params.set("location_eligibility", nextLoc);
    else params.delete("location_eligibility");

    const nextDates = overrides.dates !== undefined ? (overrides.dates as string) : internshipDates;
    if (nextDates && nextDates !== "all") params.set("internship_dates", nextDates);
    else params.delete("internship_dates");

    const nextSort = overrides.sortBy !== undefined ? (overrides.sortBy as string) : sortBy;
    if (nextSort !== "priority") params.set("sort_by", nextSort);
    else params.delete("sort_by");

    window.history.pushState({}, "", `${window.location.pathname}?${params.toString()}`);
  };

  const toggleSkill = (skill: string) => {
    const clean = skill.trim();
    if (!clean) return;
    const exists = selectedSkills.some((s) => s.toLowerCase() === clean.toLowerCase());
    const next = exists
      ? selectedSkills.filter((s) => s.toLowerCase() !== clean.toLowerCase())
      : [...selectedSkills, clean];
    setSelectedSkills(next);
    setPage(1);
    pushUrlState({ skills: next, page: 1 });
  };

  const handleAddCustomSkill = (e: React.FormEvent) => {
    e.preventDefault();
    if (!skillInput.trim()) return;
    toggleSkill(skillInput);
    setSkillInput("");
  };

  const handleRoleChange = (newRole: Role) => {
    setRole(newRole);
    setPage(1);
    pushUrlState({ role: newRole, page: 1 });
  };

  const handleRemoteToggle = (isRemote: boolean) => {
    setRemoteOnly(isRemote);
    setPage(1);
    pushUrlState({ remoteOnly: isRemote, page: 1 });
  };

  const handleLocationChange = (loc: string) => {
    setLocationEligibility(loc);
    setPage(1);
    pushUrlState({ location: loc, page: 1 });
  };

  const handleDatesChange = (dates: string) => {
    setInternshipDates(dates);
    setPage(1);
    pushUrlState({ dates: dates, page: 1 });
  };

  const handleSortChange = (newSort: "priority" | "fit" | "freshness") => {
    setSortBy(newSort);
    setPage(1);
    pushUrlState({ sortBy: newSort, page: 1 });
  };

  const requestNotificationAccess = async () => {
    if (typeof window !== "undefined" && "Notification" in window) {
      const permission = await Notification.requestPermission();
      setNotificationsEnabled(permission === "granted");
      if (permission === "granted") {
        new Notification("Alerts Activated!", {
          body: "You will receive desktop alerts when new verified roles are discovered.",
          icon: "/favicon.ico",
        });
      }
    }
  };

  const markApplied = (job: Job) => {
    addAppliedJob(job);
  };

  return (
    <main>
      <header className="site-header">
        <div className="header-meta-row">
          <p className="eyebrow">Verified Direct ATS Feeds</p>
          {/* Alerts Bell trigger with badge */}
          <button
            type="button"
            className={`alert-trigger-btn ${alerts.length > 0 ? "has-alerts" : ""}`}
            onClick={() => setShowAlertModal(true)}
            title="View newly verified matching roles"
            aria-label="View alerts for newly verified roles"
          >
            <span className="bell-icon">🔔</span>
            <span className="alert-btn-text">Alerts</span>
            {alerts.length > 0 && <span className="alert-count-pill">{alerts.length} New</span>}
          </button>
        </div>

        <div className="header-title-row">
          <div>
            <h1>InternRoleFinder</h1>
            <p className="subtle">
              Zero-credential discovery of verified software and AI internships. Direct employer ATS links only.
            </p>
          </div>
        </div>

        {/* Global Statistics Bar */}
        <div className="metrics-bar">
          <div className="metric-chip">
            <span className="metric-val">{total}</span>
            <span className="metric-lbl">Matching Roles</span>
          </div>
          <div className="metric-chip">
            <span className="metric-val">{summary?.total_remote ?? "—"}</span>
            <span className="metric-lbl">Verified Remote</span>
          </div>
          <div className="metric-chip">
            <span className="metric-val">{alerts.length}</span>
            <span className="metric-lbl">Discovered in 24h</span>
          </div>
        </div>
      </header>

      {/* Primary Top Navigation */}
      <div className="page-links">
        <Link href="/" aria-current="page" className="nav-link active">
          Browse Jobs ({total})
        </Link>
        <Link href="/applied" className="nav-link">
          Application Tracker ({appliedJobsCount})
        </Link>
      </div>

      {/* Filter Section Card */}
      <div className="filter-card">
        {/* Row 1: Role Type + Remote Only Switch */}
        <div className="filter-row primary-controls">
          <div className="control-group">
            <span className="filter-label">Role Focus:</span>
            <div className="btn-toggle-group" role="group" aria-label="Role category">
              <button
                type="button"
                className={`filter-btn ${role === "sde" ? "selected" : ""}`}
                onClick={() => handleRoleChange("sde")}
              >
                SDE Internships
              </button>
              <button
                type="button"
                className={`filter-btn ${role === "ai" ? "selected" : ""}`}
                onClick={() => handleRoleChange("ai")}
              >
                AI & GenAI Internships
              </button>
            </div>
          </div>

          {/* Remote Only Toggle - Default Active */}
          <div className="control-group remote-toggle-group">
            <span className="filter-label">Workplace:</span>
            <div className="btn-toggle-group" role="group" aria-label="Remote filter">
              <button
                type="button"
                className={`filter-btn remote-btn ${remoteOnly ? "selected is-remote" : ""}`}
                onClick={() => handleRemoteToggle(true)}
                title="Only show verified remote positions"
              >
                <span className="pulse-indicator" aria-hidden="true" />
                Remote Only (Default)
              </button>
              <button
                type="button"
                className={`filter-btn ${!remoteOnly ? "selected" : ""}`}
                onClick={() => handleRemoteToggle(false)}
                title="Include on-site and hybrid roles"
              >
                All (Inc. On-site)
              </button>
            </div>
          </div>
        </div>

        {/* Row 2: Location Eligibility & Internship Dates */}
        <div className="filter-row secondary-controls">
          <div className="control-group">
            <label htmlFor="location-select" className="filter-label">
              Location Eligibility:
            </label>
            <select
              id="location-select"
              className="styled-select"
              value={locationEligibility}
              onChange={(e) => handleLocationChange(e.target.value)}
            >
              {LOCATION_OPTIONS.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="control-group">
            <label htmlFor="dates-select" className="filter-label">
              Internship Term / Dates:
            </label>
            <select
              id="dates-select"
              className="styled-select"
              value={internshipDates}
              onChange={(e) => handleDatesChange(e.target.value)}
            >
              {DATES_OPTIONS.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="control-group">
            <label htmlFor="sort-select" className="filter-label">
              Rank & Sort:
            </label>
            <select
              id="sort-select"
              className="styled-select"
              value={selectedSkills.length > 0 && sortBy === "priority" ? "fit" : sortBy}
              onChange={(e) => handleSortChange(e.target.value as "priority" | "fit" | "freshness")}
            >
              <option value="fit">⚡ Best Fit (Ranked)</option>
              <option value="priority">Priority (Discovered Startups First)</option>
              <option value="freshness">Newly Verified (Most Recent)</option>
            </select>
          </div>
        </div>

        {/* Row 3: Skills Filter and Fit Matcher */}
        <div className="filter-row skills-controls">
          <div className="skills-header">
            <span className="filter-label">Filter & Rank by Your Skills:</span>
            {selectedSkills.length > 0 && (
              <button
                type="button"
                className="clear-skills-btn"
                onClick={() => {
                  setSelectedSkills([]);
                  setPage(1);
                  pushUrlState({ skills: [], page: 1 });
                }}
              >
                Clear skills ({selectedSkills.length})
              </button>
            )}
          </div>

          <div className="skills-pill-rack">
            {POPULAR_SKILLS.map((skill) => {
              const active = selectedSkills.some((s) => s.toLowerCase() === skill.toLowerCase());
              return (
                <button
                  type="button"
                  key={skill}
                  className={`skill-tag-btn ${active ? "active" : ""}`}
                  onClick={() => toggleSkill(skill)}
                >
                  {active ? `✓ ${skill}` : `+ ${skill}`}
                </button>
              );
            })}
          </div>

          <form onSubmit={handleAddCustomSkill} className="custom-skill-form">
            <input
              type="text"
              placeholder="Add other skill (e.g. FastAPI, Tailwind, Swift)…"
              value={skillInput}
              onChange={(e) => setSkillInput(e.target.value)}
              className="skill-input"
            />
            <button type="submit" className="add-skill-btn" disabled={!skillInput.trim()}>
              Add
            </button>
          </form>

          {selectedSkills.length > 0 && (
            <div className="active-skills-summary">
              <span className="summary-title">Active Match Criteria:</span>
              {selectedSkills.map((s) => (
                <span key={s} className="active-skill-badge">
                  {s}
                  <button
                    type="button"
                    onClick={() => toggleSkill(s)}
                    aria-label={`Remove ${s}`}
                    className="remove-skill-btn"
                  >
                    ×
                  </button>
                </span>
              ))}
              <span className="ranking-badge-note">⚡ Roles are ranked by fit score</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Results Section */}
      <section aria-live="polite" className="jobs-section">
        {loading && (
          <div className="loading-state">
            <div className="spinner" />
            <p className="status">Fetching active verified listings…</p>
          </div>
        )}

        {error && (
          <div className="status-banner error">
            <p>{error} Ensure the backend API is running on localhost:8000, then refresh.</p>
          </div>
        )}

        {!loading && !error && total === 0 && (
          <div className="status-banner empty">
            <p className="empty-title">No matching roles found.</p>
            <p className="empty-desc">
              Try adjusting your skill filters, switching from Remote Only to All Locations, or checking back soon as
              new verified sources are crawled.
            </p>
            <button
              type="button"
              className="btn-reset"
              onClick={() => {
                setRemoteOnly(true);
                setSelectedSkills([]);
                setLocationEligibility("all");
                setInternshipDates("all");
                setPage(1);
                pushUrlState({ skills: [], location: "all", dates: "all", page: 1 });
              }}
            >
              Reset Filters
            </button>
          </div>
        )}

        {!loading && !error && total > 0 && (
          <div className="result-meta-row">
            <span className="result-count">
              <strong>{total}</strong> verified roles
              {remoteOnly && " (Remote Only default active)"}
            </span>
            {selectedSkills.length > 0 && (
              <span className="ranking-indicator">
                Sorted by <strong>Fit Score</strong> for ({selectedSkills.join(", ")})
              </span>
            )}
          </div>
        )}

        {!loading && !error && jobs.length > 0 && applicationsLoaded && (
          <JobList
            jobs={jobs}
            page={page}
            pageCount={totalPages}
            onPageChange={(nextPage) => {
              setPage(nextPage);
              pushUrlState({ page: nextPage });
            }}
            appliedIds={appliedIds}
            actionLabel="Save & Track"
            disableAppliedAction
            onAction={markApplied}
            activeSkills={selectedSkills}
          />
        )}
      </section>

      {/* Newly Verified Roles Alerts Modal */}
      {showAlertModal && (
        <div className="modal-backdrop" onClick={() => setShowAlertModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>Newly Verified Role Alerts</h2>
                <p className="subtle">Roles crawled and verified active within the last 24 hours.</p>
              </div>
              <button
                type="button"
                className="close-modal-btn"
                onClick={() => setShowAlertModal(false)}
                aria-label="Close alerts"
              >
                ✕
              </button>
            </div>

            <div className="modal-actions-bar">
              <span className="alert-badge-count">{alerts.length} fresh roles available</span>
              {!notificationsEnabled ? (
                <button type="button" className="btn-notif-enable" onClick={requestNotificationAccess}>
                  🔔 Enable Browser Notifications
                </button>
              ) : (
                <span className="notif-active-badge">✓ Desktop Notifications Active</span>
              )}
            </div>

            <div className="alerts-list">
              {alerts.length === 0 ? (
                <p className="status">No new roles in the past 24 hours. Check back after the next crawl cycle!</p>
              ) : (
                alerts.map((alertJob) => (
                  <div key={alertJob.id} className="alert-job-item">
                    <div>
                      <div className="alert-job-title">{alertJob.title}</div>
                      <div className="alert-job-sub">
                        <span>{alertJob.company || "Verified Startup"}</span>
                        <span>•</span>
                        <span>{alertJob.is_remote ? "Remote" : alertJob.location || "India"}</span>
                      </div>
                    </div>
                    <div className="alert-item-actions">
                      <a
                        href={alertJob.apply_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-apply-alert"
                      >
                        Apply Soon ↗
                      </a>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
