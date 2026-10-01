"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import JobList, { jobsPerPage, type Job } from "../components/JobList";
import { readAppliedJobs, saveAppliedJobs, subscribeToAppliedJobChanges } from "../applied-storage";

export default function AppliedPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [page, setPage] = useState(1);
  const [loaded, setLoaded] = useState(false);
  const pageCount = Math.max(1, Math.ceil(jobs.length / jobsPerPage));
  const currentPage = Math.min(page, pageCount);
  const pageJobs = jobs.slice((currentPage - 1) * jobsPerPage, currentPage * jobsPerPage);

  useEffect(() => {
    setJobs(readAppliedJobs());
    setLoaded(true);
  }, []);

  useEffect(() => subscribeToAppliedJobChanges(() => setJobs(readAppliedJobs())), []);

  const removeApplied = (job: Job) => {
    const nextJobs = jobs.filter((appliedJob) => appliedJob.id !== job.id);
    setJobs(nextJobs);
    setPage((currentPage) => Math.min(currentPage, Math.max(1, Math.ceil(nextJobs.length / jobsPerPage))));
    saveAppliedJobs(nextJobs);
  };

  return (
    <main>
      <header>
        <p className="eyebrow">Your application list</p>
        <h1>Applied internships</h1>
        <p className="subtle">Saved in this browser.</p>
      </header>
      <div className="page-links">
        <Link href="/">Browse jobs</Link>
        <Link href="/applied" aria-current="page">Applied internships ({jobs.length})</Link>
      </div>
      <section aria-live="polite">
        {!loaded && <p className="status">Loading saved internships…</p>}
        {loaded && jobs.length === 0 && <p className="status">No applied internships yet.</p>}
        {loaded && jobs.length > 0 && (
          <JobList
            jobs={pageJobs}
            page={currentPage}
            pageCount={pageCount}
            onPageChange={setPage}
            appliedIds={new Set(jobs.map((job) => job.id))}
            actionLabel="Remove"
            disableAppliedAction={false}
            onAction={removeApplied}
          />
        )}
      </section>
    </main>
  );
}