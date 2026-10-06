"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import JobList, { jobsPerPage, type Job, type JobCategory } from "./components/JobList";
import {
  addAppliedJob,
  readAppliedHistoryIds,
  readAppliedJobs,
  readInvalidatedHistoryIds,
  addInvalidatedJobId,
  subscribeToAppliedJobChanges,
} from "./applied-storage";

export type SortOption = "direct_portal" | "india_first" | "recent";

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
  total_india: number;
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
  const [sortBy, setSortBy] = useState<SortOption>("direct_portal");
  const [remoteOnly, setRemoteOnly] = useState<boolean>(false);
  const [startupsOnly, setStartupsOnly] = useState<boolean>(false);
  const [indiaOnly, setIndiaOnly] = useState<boolean>(false);
  const [mncsOnly, setMncsOnly] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");

  const [debouncedSearch, setDebouncedSearch] = useState<string>("");

  const [page, setPage] = useState(1);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [appliedJobsCount, setAppliedJobsCount] = useState(0);
  const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set());
  const [invalidatedIds, setInvalidatedIds] = useState<Set<string>>(new Set());
  const [applicationsLoaded, setApplicationsLoaded] = useState(false);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);

  const [queryReady, setQueryReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastCareerLink, setToastCareerLink] = useState<{ label: string; url: string } | null>(null);

  // Auto-hide applied toast after 6 seconds
  useEffect(() => {
    if (!toastMessage) return;
    const timer = setTimeout(() => {
      setToastMessage(null);
      setToastCareerLink(null);
    }, 6000);
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
      india_only: String(indiaOnly),
      mncs_only: String(mncsOnly),
      sort_by: sortBy,
    });
    if (role !== "all") {
      params.set("role_type", role);
    }
    if (debouncedSearch.trim()) {
      params.set("search", debouncedSearch.trim());
    }
    const base = getApiUrl();
    return `${base}/api/jobs?${params.toString()}`;
  }, [page, role, sortBy, remoteOnly, startupsOnly, indiaOnly, mncsOnly, debouncedSearch]);


  // Sync initial state from URL query
  useEffect(() => {
    const syncFromUrl = () => {
      const params = new URLSearchParams(window.location.search);
      const queryPage = Number(params.get("page"));
      const queryRole = params.get("role_type") as RoleFilter | null;
      const querySort = params.get("sort_by") as SortOption | null;
      const queryRemote = params.get("remote_only");
      const queryStartups = params.get("startups_only");
      const queryIndia = params.get("india_only");
      const queryMncs = params.get("mncs_only");
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
      if (querySort && ["direct_portal", "india_first", "recent"].includes(querySort)) {
        setSortBy(querySort);
      } else {
        setSortBy("direct_portal");
      }
      setRemoteOnly(queryRemote === "true");
      setStartupsOnly(queryStartups === "true");
      setIndiaOnly(queryIndia === "true");
      setMncsOnly(queryMncs === "true");
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
      const invIds = readInvalidatedHistoryIds();
      setInvalidatedIds(invIds);
      setApplicationsLoaded(true);
    };
    updateLocalApplied();
    return subscribeToAppliedJobChanges(updateLocalApplied);
  }, []);

  // Active unapplied and non-invalidated jobs visible on current page
  const visibleJobs = useMemo(() => {
    return jobs.filter((job) => !appliedIds.has(job.id) && !invalidatedIds.has(job.id));
  }, [jobs, appliedIds, invalidatedIds]);

  // Fetch summary counts for tabs
  useEffect(() => {
    const base = getApiUrl();
    const query = `remote_only=${remoteOnly}&startups_only=${startupsOnly}&india_only=${indiaOnly}&mncs_only=${mncsOnly}`;

    const primaryUrl = `${base}/api/jobs/summary?${query}`;
    const fallbackUrl = `/api/jobs/summary?${query}`;
    const directUrl = `http://127.0.0.1:8000/api/jobs/summary?${query}`;

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
        return fetch(directUrl, {
          headers: { "ngrok-skip-browser-warning": "true" },
        }).then((r) => (r.ok ? r.json() : null));
      })
      .then((data: SummaryResponse | null) => {
        if (data) setSummary(data);
      })
      .catch(() => {
        fetch(directUrl)
          .then((r) => (r.ok ? r.json() : null))
          .then((data) => {
            if (data) setSummary(data);
          })
          .catch(() => {});
      });
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
        let response: Response;
        try {
          response = await fetch(endpoint, {
            signal: controller.signal,
            headers: { "ngrok-skip-browser-warning": "true" },
          });
        } catch (initialErr: any) {
          if (initialErr.name === "AbortError") throw initialErr;
          if (
            endpoint.startsWith("/api") &&
            typeof window !== "undefined" &&
            (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
          ) {
            response = await fetch(`http://127.0.0.1:8000${endpoint}`, {
              signal: controller.signal,
              headers: { "ngrok-skip-browser-warning": "true" },
            });
          } else {
            throw initialErr;
          }
        }

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

        // If relative rewrite proxy returned 500 or 502, try direct 127.0.0.1:8000
        if (
          !response.ok &&
          endpoint.startsWith("/api") &&
          typeof window !== "undefined" &&
          (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
        ) {
          const directRes = await fetch(`http://127.0.0.1:8000${endpoint}`, {
            signal: controller.signal,
            headers: { "ngrok-skip-browser-warning": "true" },
          });
          if (directRes.ok) {
            response = directRes;
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

    const nextSort = overrides.sortBy !== undefined ? String(overrides.sortBy) : sortBy;
    if (nextSort && nextSort !== "direct_portal") {
      params.set("sort_by", nextSort);
    } else {
      params.delete("sort_by");
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

    const nextIndia =
      overrides.indiaOnly !== undefined ? Boolean(overrides.indiaOnly) : indiaOnly;
    if (nextIndia) {
      params.set("india_only", "true");
    } else {
      params.delete("india_only");
    }

    if (current.mncsOnly) {
      params.set("mncs_only", "true");
    } else {
      params.delete("mncs_only");
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

  const handleSortChange = (newSort: SortOption) => {
    setSortBy(newSort);
    setPage(1);
    pushUrlState({ sortBy: newSort, page: 1 });
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

  const handleIndiaToggle = (isIndia: boolean) => {
    setIndiaOnly(isIndia);
    setPage(1);
    pushUrlState({ indiaOnly: isIndia, page: 1 });
  };

  const handleMncsToggle = (isMncs: boolean) => {
    setMncsOnly(isMncs);
    setPage(1);
    pushUrlState({ mncsOnly: isMncs, page: 1 });
  };

  const resetAllFilters = () => {
    setRole("all");
    setSortBy("direct_portal");
    setRemoteOnly(false);
    setStartupsOnly(false);
    setIndiaOnly(false);
    setMncsOnly(false);
    setSearchQuery("");
    setDebouncedSearch("");
    setPage(1);
    pushUrlState({
      role: "all",
      sortBy: "direct_portal",
      remoteOnly: false,
      startupsOnly: false,
      indiaOnly: false,
      mncsOnly: false,
      search: "",
      page: 1,
    });
  };


  const markApplied = (job: Job) => {
    addAppliedJob(job);
    const company = job.company ? `${job.company} — ` : "";
    setToastMessage(`✓ Applied: "${company}${job.title}" removed from list & tracked for 2 days.`);
  };

  const handleInvalidate = async (job: Job) => {
    addInvalidatedJobId(job.id);
    setInvalidatedIds((prev) => new Set([...prev, job.id]));
    setJobs((prev) => prev.filter((j) => j.id !== job.id));
    const company = job.company ? `${job.company} — ` : "";

    if (job.career_url) {
      setToastCareerLink({
        label: `Browse ${job.company || "Company"} Careers`,
        url: job.career_url,
      });
      setToastMessage(`⚑ Listing reported as closed/404 & removed.`);
    } else {
      setToastCareerLink(null);
      setToastMessage(`⚑ Invalidation submitted: "${company}${job.title}" removed.`);
    }

    try {
      const base = getApiUrl();
      const primaryUrl = `${base}/api/jobs/${job.id}/invalidate`;
      const fallbackUrl = `/api/jobs/${job.id}/invalidate`;
      let res = await fetch(primaryUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok && primaryUrl !== fallbackUrl) {
        await fetch(fallbackUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
      }
    } catch {}
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
    role !== "all" ||
    sortBy !== "direct_portal" ||
    remoteOnly ||
    startupsOnly ||
    indiaOnly ||
    debouncedSearch.trim() !== "";


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

      {/* Startup Advantage Callout - removed clutter */}


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
                className={`filter-btn india-filter-btn ${indiaOnly ? "selected is-india-only-active" : ""}`}
                onClick={() => handleIndiaToggle(!indiaOnly)}
                title="Only show jobs from Indian companies or India-based locations"
              >
                <span>🇮🇳 India Only</span>
                {summary && (
                  <span className="cat-count-pill india-count-pill">
                    {summary.total_india}
                  </span>
                )}
              </button>

              <button
                type="button"
                className={`filter-btn mnc-filter-btn ${mncsOnly ? "selected is-mnc-active" : ""}`}
                onClick={() => handleMncsToggle(!mncsOnly)}
                title="Only show top multinational corporations (MNCs)"
              >
                <span>🏢 MNCs Only</span>
                {summary && (
                  <span className="cat-count-pill mnc-count-pill">
                    {(summary as any).total_mncs || 0}
                  </span>
                )}
              </button>

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

        <div className="filter-row sort-controls-row">
          <div className="control-group">
            <span className="filter-label">Sort Priority:</span>
            <div className="btn-toggle-group sort-selector-group" role="group" aria-label="Sort priority">
              <button
                type="button"
                className={`filter-btn sort-btn ${sortBy === "direct_portal" ? "selected is-direct-portal-active" : ""}`}
                onClick={() => handleSortChange("direct_portal")}
                title="Prioritize verified direct employer career portals first"
              >
                <span>⚡ Direct Portal First</span>
              </button>
              <button
                type="button"
                className={`filter-btn sort-btn ${sortBy === "india_first" ? "selected is-india-active" : ""}`}
                onClick={() => handleSortChange("india_first")}
                title="Prioritize Indian tech companies and locations first"
              >
                <span>🇮🇳 India First</span>
              </button>
              <button
                type="button"
                className={`filter-btn sort-btn ${sortBy === "recent" ? "selected" : ""}`}
                onClick={() => handleSortChange("recent")}
                title="Show most recently added verified roles first"
              >
                <span>🕒 Most Recent</span>
              </button>
            </div>
          </div>
        </div>

        {(role !== "all" || sortBy !== "direct_portal" || remoteOnly || startupsOnly || indiaOnly || mncsOnly || debouncedSearch) && (
          <div className="active-filter-bar">
            <span className="active-filters-label">Active Filters:</span>
            {role !== "all" && (
              <span className="filter-tag">
                {CATEGORIES.find((c) => c.key === role)?.label}
              </span>
            )}
            {sortBy !== "direct_portal" && (
              <span className="filter-tag tag-sort">
                {sortBy === "india_first" ? "🇮🇳 India First" : "🕒 Most Recent"}
              </span>
            )}
            {startupsOnly && <span className="filter-tag tag-startup">🚀 Startups Only</span>}
            {indiaOnly && <span className="filter-tag tag-india">🇮🇳 India Only</span>}
            {mncsOnly && <span className="filter-tag tag-mnc">🏢 MNCs Only</span>}
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
              {indiaOnly ? " (India Only)" : ""}
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
            onInvalidate={handleInvalidate}
          />
        )}
      </section>

      {toastMessage && (
        <div className="action-toast" role="status" aria-live="polite">
          <span className="toast-icon">🚀</span>
          <span>{toastMessage}</span>
          {toastCareerLink && (
            <a
              href={toastCareerLink.url}
              target="_blank"
              rel="noopener noreferrer"
              className="toast-action-link"
            >
              {toastCareerLink.label} ↗
            </a>
          )}
          <button
            type="button"
            className="toast-close-btn"
            onClick={() => {
              setToastMessage(null);
              setToastCareerLink(null);
            }}
            aria-label="Close notification"
          >
            ✕
          </button>
        </div>
      )}
    </main>
  );
}
