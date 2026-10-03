"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import JobList, { jobsPerPage, type Job, type JobCategory } from "./components/JobList";
import {
  addAppliedJob,
  readAppliedHistoryIds,
  readAppliedJobs,
  subscribeToAppliedJobChanges,
} from "./applied-storage";

type RoleFilter = "all" | JobCategory;

type JobsResponse = {
  items: Job[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

type SummaryResponse = {
  all: number;
  sde: number;
  frontend: number;
  backend: number;
  full_stack: number;
  total_remote: number;
  total_startups: number;
};

const CATEGORIES: { key: RoleFilter; label: string }[] = [
  { key: "all", label: "All Roles" },
  { key: "sde", label: "SDE Intern" },
  { key: "frontend", label: "Frontend Intern" },
  { key: "backend", label: "Backend Intern" },
  { key: "full_stack", label: "Fullstack Intern" },
];

function getApiUrl(): string {
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return "";
    }
  }
  const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "";
  return rawApiUrl.replace(/\/+$/, "").replace(/\/api$/, "");
}

export default function Home() {
  const [role, setRole] = useState<RoleFilter>("all");
  const [remoteOnly, setRemoteOnly] = useState<boolean>(false);
  const [startupsOnly, setStartupsOnly] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [debouncedSearch, setDebouncedSearch] = useState<string>("");

  const [page, setPage] = useState(1);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [appliedJobsCount, setAppliedJobsCount] = useState(0);
  const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set());
  const [applicationsLoaded, setApplicationsLoaded] = useState(false);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);

  const [queryReady, setQueryReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Auto-hide applied toast after 4 seconds
  useEffect(() => {
    if (!toastMessage) return;
    const timer = setTimeout(() => setToastMessage(null), 4000);
    return () => clearTimeout(timer);
  }, [toastMessage]);

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1);
    }, 250);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Endpoint construction
  const endpoint = useMemo(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(jobsPerPage),
      remote_only: String(remoteOnly),
      startups_only: String(startupsOnly),
    });
    if (role !== "all") {
      params.set("role_type", role);
    }
    if (debouncedSearch.trim()) {
      params.set("search", debouncedSearch.trim());
    }
    const base = getApiUrl();
    return `${base}/api/jobs?${params.toString()}`;
  }, [page, role, remoteOnly, startupsOnly, debouncedSearch]);

  // Sync initial state from URL query
  useEffect(() => {
    const syncFromUrl = () => {
      const params = new URLSearchParams(window.location.search);
      const queryPage = Number(params.get("page"));
      const queryRole = params.get("role_type") as RoleFilter | null;
      const queryRemote = params.get("remote_only");
      const queryStartups = params.get("startups_only");
      const querySearch = params.get("search");

      setPage(Number.isInteger(queryPage) && queryPage > 0 ? queryPage : 1);
      if (
        queryRole &&
        ["all", "sde", "frontend", "backend", "full_stack"].includes(queryRole)
      ) {
        setRole(queryRole);
      } else {
        setRole("all");
      }
      setRemoteOnly(queryRemote === "true");
      setStartupsOnly(queryStartups === "true");
      if (querySearch) {
        setSearchQuery(querySearch);
        setDebouncedSearch(querySearch);
      }
    };

    syncFromUrl();
    setQueryReady(true);
    window.addEventListener("popstate", syncFromUrl);
    return () => window.removeEventListener("popstate", syncFromUrl);
  }, []);

  // Load applied jobs and history for tracking and filtering
  useEffect(() => {
    const updateLocalApplied = () => {
      const stored = readAppliedJobs();
      setAppliedJobsCount(stored.length);
      const historyIds = readAppliedHistoryIds();
      setAppliedIds(historyIds);
      setApplicationsLoaded(true);
    };
    updateLocalApplied();
    return subscribeToAppliedJobChanges(updateLocalApplied);
  }, []);

  // Active unapplied jobs visible on current page
  const visibleJobs = useMemo(() => {
    return jobs.filter((job) => !appliedIds.has(job.id));
  }, [jobs, appliedIds]);

  // Fetch summary counts for tabs
  useEffect(() => {
    const base = getApiUrl();
    const primaryUrl = `${base}/api/jobs/summary?remote_only=${remoteOnly}&startups_only=${startupsOnly}`;
    const fallbackUrl = `/api/jobs/summary?remote_only=${remoteOnly}&startups_only=${startupsOnly}`;

    fetch(primaryUrl, {
      headers: { "ngrok-skip-browser-warning": "true" },
    })
      .then((res) => {
        if (res.ok) return res.json();
        if (primaryUrl !== fallbackUrl) {
          return fetch(fallbackUrl, {
            headers: { "ngrok-skip-browser-warning": "true" },
          }).then((r) => (r.ok ? r.json() : null));
        }
        return null;
      })
      .then((data: SummaryResponse | null) => {
        if (data) setSummary(data);
      })
      .catch(() => {});
  }, [remoteOnly, startupsOnly]);

  // Fetch jobs for current query with resilient fallback
  useEffect(() => {
    if (!queryReady) return;
    let active = true;
    const controller = new AbortController();
    setLoading(true);
    setError("");

    const fetchWithFallback = async () => {
      try {
        let response = await fetch(endpoint, {
          signal: controller.signal,
          headers: { "ngrok-skip-browser-warning": "true" },
        });

        // If configured external API failed (e.g. 404 or tunnel down), fallback to local /api rewrite proxy
        if (!response.ok && (endpoint.startsWith("http://") || endpoint.startsWith("https://"))) {
          const fallbackUrl = endpoint.replace(/^https?:\/\/[^\/]+/, "");
          const fallbackRes = await fetch(fallbackUrl, {
            signal: controller.signal,
            headers: { "ngrok-skip-browser-warning": "true" },
          });
          if (fallbackRes.ok) {
            response = fallbackRes;
          }
        }

        if (!response.ok) {
          throw new Error("Could not load jobs from server.");
        }

        const data: JobsResponse = await response.json();
        if (!active) return;
        setJobs(data.items);
        setTotal(data.total);
        setTotalPages(data.total_pages);
        if (data.page !== page) {
          setPage(data.page);
        }
      } catch (reason: any) {
        if (active && reason.name !== "AbortError") {
          setError(reason.message || "Could not load jobs from server.");
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchWithFallback();

    return () => {
      active = false;
      controller.abort();
    };
  }, [endpoint, page, queryReady]);

  // Push state to URL
  const pushUrlState = (
    overrides: Record<string, string | number | boolean | null | undefined>
  ) => {
    const params = new URLSearchParams(window.location.search);
    params.set("page", String(overrides.page ?? page));

    const nextRole = overrides.role !== undefined ? String(overrides.role) : role;
    if (nextRole && nextRole !== "all") {
      params.set("role_type", nextRole);
    } else {
      params.delete("role_type");
    }

    const nextRemote =
      overrides.remoteOnly !== undefined ? Boolean(overrides.remoteOnly) : remoteOnly;
    if (nextRemote) {
      params.set("remote_only", "true");
    } else {
      params.delete("remote_only");
    }

    const nextStartups =
      overrides.startupsOnly !== undefined ? Boolean(overrides.startupsOnly) : startupsOnly;
    if (nextStartups) {
      params.set("startups_only", "true");
    } else {
      params.delete("startups_only");
    }

    const nextSearch =
      overrides.search !== undefined ? String(overrides.search) : debouncedSearch;
    if (nextSearch && nextSearch.trim()) {
      params.set("search", nextSearch.trim());
    } else {
      params.delete("search");
    }

    window.history.pushState({}, "", `${window.location.pathname}?${params.toString()}`);
  };

  const handleRoleChange = (newRole: RoleFilter) => {
    setRole(newRole);
    setPage(1);
    pushUrlState({ role: newRole, page: 1 });
  };

  const handleRemoteToggle = (isRemote: boolean) => {
    setRemoteOnly(isRemote);
    setPage(1);
    pushUrlState({ remoteOnly: isRemote, page: 1 });
  };

  const handleStartupsToggle = (isStartups: boolean) => {
    setStartupsOnly(isStartups);
    setPage(1);
    pushUrlState({ startupsOnly: isStartups, page: 1 });
  };

  const resetAllFilters = () => {
    setRole("all");
    setRemoteOnly(false);
    setStartupsOnly(false);
    setSearchQuery("");
    setDebouncedSearch("");
    setPage(1);
    pushUrlState({
      role: "all",
      remoteOnly: false,
      startupsOnly: false,
      search: "",
      page: 1,
    });
  };

  const markApplied = (job: Job) => {
    addAppliedJob(job);
    const company = job.company ? `${job.company} — ` : "";
    setToastMessage(`✓ Applied: "${company}${job.title}" removed from list & tracked for 2 days.`);
  };

  const getCategoryCount = (key: RoleFilter): number | null => {
    if (!summary) return null;
    if (key === "all") return summary.all;
    if (key === "sde") return summary.sde;
    if (key === "frontend") return summary.frontend;
    if (key === "backend") return summary.backend;
    if (key === "full_stack") return summary.full_stack;
    return null;
  };

  const hasActiveFilters =
    role !== "all" || remoteOnly || startupsOnly || debouncedSearch.trim() !== "";

  return (
    <main>
      <header className="site-header">
        <div className="header-meta-row">
          <p className="eyebrow">⚡ Direct ATS & Startup Feeds</p>
          <div className="header-badges-row">
            <span className="live-stat-pill">
              🇮🇳 India Rank #1
            </span>
            <span className="live-stat-pill">
              🚀 {summary?.total_startups ?? 0} High-Reply Startups
            </span>
          </div>
        </div>

        <div className="header-title-row">
          <div>
            <h1>InternRoleFinder</h1>
            <p className="subtle">
              Verified software internships for <strong>SDE, Frontend, Backend & Fullstack</strong>. Direct ATS application links only — prioritized for startups with the highest interview callback rates.
            </p>
          </div>
        </div>
      </header>

      {/* Primary Navigation */}
      <div className="page-links">
        <Link href="/" aria-current="page" className="nav-link active">
          Browse Opportunities ({total})
        </Link>
        <Link href="/applied" className="nav-link">
          Applied Tracker ({appliedJobsCount})
        </Link>
      </div>

      {/* Startup Advantage Callout */}
      <div className="startup-tip-banner">
        <div className="startup-tip-content">
          <span className="startup-tip-icon" aria-hidden="true">💡</span>
          <div>
            <strong>Why apply to high-growth startups?</strong> Fast-moving tech startups have a <strong>10x–50x higher interview response rate</strong> than legacy MNC black holes because engineering leads directly review your GitHub, projects, and resume.
          </div>
        </div>
      </div>

      {/* Live Search Bar */}
      <div className="search-section">
        <div className="search-input-wrapper">
          <span className="search-icon" aria-hidden="true">🔍</span>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by company (e.g. Zepto, Razorpay, Supabase), tech (React, Go, Python), or location..."
            className="search-input"
            aria-label="Search software internships"
          />
          {searchQuery && (
            <button
              type="button"
              className="search-clear-btn"
              onClick={() => setSearchQuery("")}
              aria-label="Clear search input"
              title="Clear search"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Filter Card: Category, Startups Toggle & Remote Toggle */}
      <div className="filter-card">
        <div className="filter-row primary-controls">
          <div className="control-group">
            <span className="filter-label">Role Category:</span>
            <div className="btn-toggle-group role-selector-group" role="group" aria-label="Role category">
              {CATEGORIES.map((cat) => {
                const count = getCategoryCount(cat.key);
                return (
                  <button
                    type="button"
                    key={cat.key}
                    className={`filter-btn ${role === cat.key ? "selected" : ""}`}
                    onClick={() => handleRoleChange(cat.key)}
                  >
                    <span>{cat.label}</span>
                    {count !== null && <span className="cat-count-pill">{count}</span>}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="control-group secondary-toggles">
            <span className="filter-label">Opportunity Filter:</span>
            <div className="btn-toggle-group" role="group" aria-label="Startups and workplace filter">
              <button
                type="button"
                className={`filter-btn startup-filter-btn ${startupsOnly ? "selected is-startup-active" : ""}`}
                onClick={() => handleStartupsToggle(!startupsOnly)}
                title="Only show fast-growing tech startups with high response rates"
              >
                <span>🚀 Startups Only</span>
                {summary && (
                  <span className="cat-count-pill startup-count-pill">
                    {summary.total_startups}
                  </span>
                )}
              </button>

              <button
                type="button"
                className={`filter-btn remote-btn ${remoteOnly ? "selected is-remote" : ""}`}
                onClick={() => handleRemoteToggle(!remoteOnly)}
                title="Only show verified remote positions"
              >
                <span className="pulse-indicator" aria-hidden="true" />
                <span>Remote Only</span>
              </button>
            </div>
          </div>
        </div>

        {hasActiveFilters && (
          <div className="active-filter-bar">
            <span className="active-filters-label">Active Filters:</span>
            {role !== "all" && (
              <span className="filter-tag">
                {CATEGORIES.find((c) => c.key === role)?.label}
              </span>
            )}
            {startupsOnly && <span className="filter-tag tag-startup">🚀 Startups Only</span>}
            {remoteOnly && <span className="filter-tag tag-remote">🌐 Remote Only</span>}
            {debouncedSearch && (
              <span className="filter-tag tag-search">"{debouncedSearch}"</span>
            )}
            <button
              type="button"
              className="btn-clear-all"
              onClick={resetAllFilters}
            >
              Reset All Filters ✕
            </button>
          </div>
        )}
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
            <p>{error} Ensure the backend API is running and reachable, then refresh.</p>
          </div>
        )}

        {!loading && !error && total === 0 && (
          <div className="status-banner empty">
            <p className="empty-title">No matching roles found.</p>
            <p className="empty-desc">
              {debouncedSearch
                ? `No active openings matched "${debouncedSearch}". Try a broader term like "React", "Python", or reset filters.`
                : "Try switching filters to 'All Roles' or resetting filters to see available listings."}
            </p>
            <button
              type="button"
              className="btn-reset"
              onClick={resetAllFilters}
            >
              Reset All Filters
            </button>
          </div>
        )}

        {!loading && !error && total > 0 && (
          <div className="result-meta-row">
            <span className="result-count">
              Showing <strong>{visibleJobs.length}</strong> active roles
              {appliedIds.size > 0 && (
                <span className="meta-applied-note"> ({appliedIds.size} applied removed)</span>
              )}
              {startupsOnly ? " (Startups Only)" : ""}
              {remoteOnly ? " (Remote Only)" : ""}
              {debouncedSearch ? ` for "${debouncedSearch}"` : ""}
            </span>
            <span className="ats-direct-hint">
              ⚡ 100% Direct Employer ATS Links
            </span>
          </div>
        )}

        {!loading && !error && jobs.length > 0 && visibleJobs.length === 0 && applicationsLoaded && (
          <div className="status-banner empty">
            <p className="empty-title">All roles on this page applied to! 🎉</p>
            <p className="empty-desc">
              You have applied to all positions on page {page}. They have been removed from this list and are saved in your Applied Tracker for 2 days.
            </p>
            <div style={{ display: "flex", gap: "12px", justifyContent: "center", marginTop: "16px", flexWrap: "wrap" }}>
              {page < totalPages && (
                <button
                  type="button"
                  className="filter-btn selected"
                  onClick={() => {
                    setPage(page + 1);
                    pushUrlState({ page: page + 1 });
                  }}
                >
                  Go to Next Page ({page + 1}) →
                </button>
              )}
              <Link href="/applied" className="filter-btn" style={{ textDecoration: "none" }}>
                View Applied Tracker ({appliedJobsCount}) →
              </Link>
            </div>
          </div>
        )}

        {!loading && !error && visibleJobs.length > 0 && applicationsLoaded && (
          <JobList
            jobs={visibleJobs}
            page={page}
            pageCount={totalPages}
            onPageChange={(nextPage) => {
              setPage(nextPage);
              pushUrlState({ page: nextPage });
            }}
            appliedIds={appliedIds}
            actionLabel="Mark as Applied"
            disableAppliedAction={false}
            onAction={markApplied}
          />
        )}
      </section>

      {toastMessage && (
        <div className="action-toast" role="status" aria-live="polite">
          <span className="toast-icon">🚀</span>
          <span>{toastMessage}</span>
          <button
            type="button"
            className="toast-close-btn"
            onClick={() => setToastMessage(null)}
            aria-label="Close notification"
          >
            ✕
          </button>
        </div>
      )}
    </main>
  );
}
