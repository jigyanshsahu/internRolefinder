from urllib.parse import urlsplit

AGGREGATOR_DOMAINS = {
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "internshala.com",
    "naukri.com",
    "wellfound.com",
    "angel.co",
    "cutshort.io",
    "foundit.in",
    "simplyhired.com",
    "simplyhired.co.in",
    "shine.com",
    "instahyre.com",
    "cuvette.tech",
    "jobaaj.com",
    "unstop.com",
    "timesjobs.com",
    "freshersworld.com",
    "hirist.tech",
    "hirist.com",
    "ziprecruiter.com",
    "monster.com",
    "careerbuilder.com",
}


def is_aggregator_domain(url_or_host: str) -> bool:
    if not url_or_host:
        return False
    parsed = urlsplit(url_or_host) if "://" in url_or_host else None
    host = (parsed.hostname if parsed else url_or_host or "").lower().removeprefix("www.")
    return any(host == domain or host.endswith(f".{domain}") for domain in AGGREGATOR_DOMAINS)
