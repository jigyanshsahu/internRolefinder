"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import JobList, { jobsPerPage, type Job, type JobCategory } from "./components/JobList";
import { readAppliedJobs, saveAppliedJobs, subscribeToAppliedJobChanges } from "./applied-storage";

type Role = JobCategory;
type JobsResponse = { items: Job[]; page: number; page_size: number; total: number; total_pages: number };

const filters: { key: Role; label: string }[] = [
  { key: "sde", label: "SDE" },
  { key: "ai", label: "AI" },
];
const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [role, setRole] = useState<Role>("sde");
  const [page, setPage] = useState(1);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [appliedJobs, setAppliedJobs] = useState<Job[]>([]);
  const [applicationsLoaded, setApplicationsLoaded] = useState(false);
  const [queryReady, setQueryReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const endpoint = useMemo(() => {
    const params = new URLSearchParams({ page: String(page), page_size: String(jobsPerPage) });
    params.set("role_type", role);
    return `${apiUrl}/api/jobs?${params.toString()}`;
  }, [page, role]);

  useEffect(() => {
    const syncFromUrl = () => {
      const params = new URLSearchParams(window.location.search);
      const queryPage = Number(params.get("page"));
      const queryRole = params.get("role_type");
      setPage(Number.isInteger(queryPage) && queryPage > 0 ? queryPage : 1);
      setRole(queryRole === "ai" ? "ai" : "sde");
    };
    syncFromUrl();
    setQueryReady(true);
    window.addEventListener("popstate", syncFromUrl);
    return () => window.removeEventListener("popstate", syncFromUrl);
  }, []);

  useEffect(() => {
    setAppliedJobs(readAppliedJobs());
    setApplicationsLoaded(true);
  }, []);

  useEffect(() => subscribeToAppliedJobChanges(() => setAppliedJobs(readAppliedJobs())), []);

  useEffect(() => {
    if (!queryReady) return;
    let active = true;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    fetch(endpoint, { signal: controller.signal })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("Could not load jobs.")))
      .then((data: JobsResponse) => {
        if (!active) return;
        setJobs(data.items);
        setTotal(data.total);
        setTotalPages(data.total_pages);
        if (data.page !== page) {
          setPage(data.page);
          const params = new URLSearchParams(window.location.search);
          params.set("page", String(data.page));
          window.history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);
        }
      })
      .catch((reason: Error) => { if (active && reason.name !== "AbortError") setError(reason.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [endpoint, page, queryReady]);

  const updateQuery = (nextRole: Role, nextPage: number) => {
    const params = new URLSearchParams(window.location.search);
    params.set("page", String(nextPage));
    params.set("role_type", nextRole);
    window.history.pushState({}, "", `${window.location.pathname}?${params.toString()}`);
    setRole(nextRole);
    setPage(nextPage);
  };

  const markApplied = (job: Job) => {
    const nextAppliedJobs = [...appliedJobs.filter((appliedJob) => appliedJob.id !== job.id), job];
    setAppliedJobs(nextAppliedJobs);
    saveAppliedJobs(nextAppliedJobs);
  };

  return (
    <main>
      <header>
        <p className="eyebrow">Active internship links</p>
        <h1>InternRoleFinder</h1>
        <p className="subtle">Freshly verified application links. Closed roles disappear automatically.</p>
      </header>
      <div className="page-links">
        <Link href="/" aria-current="page">Browse jobs</Link>
        <Link href="/applied">Applied internships ({appliedJobs.length})</Link>
      </div>
      <nav aria-label="Role filters">
        {filters.map((filter) => (
          <button key={filter.key} className={role === filter.key ? "selected" : ""} onClick={() => updateQuery(filter.key, 1)}>
            {filter.label}
          </button>
        ))}
      </nav>
      <section aria-live="polite">
        {loading && <p className="status">Loading active roles…</p>}
        {error && <p className="status error">{error} Ensure the API is running, then refresh.</p>}
        {!loading && !error && total === 0 && <p className="status">No active roles found yet. The crawler will add verified links as it discovers them.</p>}
        {!loading && !error && total > 0 && <p className="result-count">{total} active roles</p>}
        {!loading && !error && jobs.length > 0 && applicationsLoaded && (
          <JobList
            jobs={jobs}
            page={page}
            pageCount={totalPages}
            onPageChange={(nextPage) => updateQuery(role, nextPage)}
            appliedIds={new Set(appliedJobs.map((job) => job.id))}
            actionLabel="Mark applied"
            disableAppliedAction
            onAction={markApplied}
          />
        )}
      </section>
    </main>
  );
}
