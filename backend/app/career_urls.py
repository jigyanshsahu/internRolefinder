"""Utility module for resolving company career portal URLs.
Ensures applicants can always reach an authentic, working careers page even if
a specific direct listing URL returns 404 or has expired.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

KNOWN_COMPANY_CAREERS: dict[str, str] = {
    # Top Indian Tech & Unicorns
    "swiggy": "https://careers.swiggy.com",
    "razorpay": "https://razorpay.com/jobs",
    "cred": "https://careers.cred.club",
    "zepto": "https://zepto.co/careers",
    "groww": "https://groww.in/careers",
    "zerodha": "https://careers.zerodha.com",
    "postman": "https://www.postman.com/careers",
    "signoz": "https://signoz.io/careers",
    "juspay": "https://juspay.in/careers",
    "browserstack": "https://www.browserstack.com/careers",
    "blinkit": "https://blinkit.com/careers",
    "meesho": "https://www.meesho.io/jobs",
    "phonepe": "https://www.phonepe.com/careers",
    "inmobi": "https://www.inmobi.com/company/careers",
    "slice": "https://www.sliceit.com/careers",
    "smallcase": "https://www.smallcase.com/careers",
    "cashfree": "https://www.cashfree.com/careers",
    "indmoney": "https://www.indmoney.com/careers",
    "fi money": "https://fi.money/careers",
    "jupiter": "https://jupiter.money/careers",
    "darwinbox": "https://darwinbox.com/careers",
    "delhivery": "https://www.delhivery.com/careers",
    "shadowfax": "https://www.shadowfax.in/careers",
    "rapido": "https://www.rapido.bike/Careers",
    "porter": "https://porter.in/careers",
    "cars24": "https://www.cars24.com/careers",
    "spinny": "https://www.spinny.com/careers",
    "physicswallah": "https://www.pw.live/careers",
    "hasura": "https://hasura.io/careers",
    "atlan": "https://atlan.com/careers",
    "coindcx": "https://coindcx.com/careers",
    "krutrim": "https://krutrim.ai/careers",
    "ather energy": "https://www.atherenergy.com/careers",
    "lenskart": "https://www.lenskart.com/careers",
    "sarvam ai": "https://www.sarvam.ai/careers",
    "urban company": "https://www.urbancompany.com/careers",
    "zomato": "https://www.zomato.com/careers",
    "paytm": "https://paytm.com/careers",
    "dream11": "https://careers.dream11.com",
    "unacademy": "https://unacademy.com/careers",
    "clevertap": "https://clevertap.com/careers",
    "whatfix": "https://whatfix.com/careers",
    "chargebee": "https://www.chargebee.com/careers",
    "icertis": "https://www.icertis.com/careers",
    "druva": "https://www.druva.com/about/careers",
    "innovaccer": "https://innovaccer.com/careers",
    "harness": "https://www.harness.io/careers",
    "yellow.ai": "https://yellow.ai/careers",
    "gupshup": "https://www.gupshup.io/careers",
    "leadsquared": "https://www.leadsquared.com/careers",
    "keka": "https://www.keka.com/careers",
    "licious": "https://www.licious.in/careers",
    "lendingkart": "https://www.lendingkart.com/careers",
    "navi": "https://navi.com/careers",
    "onecode": "https://www.onecode.in/careers",
    "kreditbee": "https://kreditbee.in/careers",
    "turtlemint": "https://turtlemint.com/careers",
    "apna": "https://apna.co/careers",
    "blackbuck": "https://www.blackbuck.com/careers",
    "pixxel": "https://www.pixxel.space/careers",
    "skyroot aerospace": "https://skyroot.in/careers",
    "agnikul cosmos": "https://agnikul.in/careers",
    "fampay": "https://jobs.lever.co/fampay",
    "merkle science": "https://jobs.lever.co/merklescience",
    "drivetrain": "https://jobs.lever.co/drivetrain",
    "auxia": "https://jobs.lever.co/auxia",
    "mhtechin": "https://careers.mhtechin.com/",
    "bytedance": "https://joinbytedance.com",
    "nebo": "https://www.neboagency.com/careers/",
    "grass valley": "https://www.grassvalley.com/careers/",
    "jump trading": "https://www.jumptrading.com/careers/",
    # Global Tech & Startups
    "palantir": "https://jobs.lever.co/palantir",
    "supabase": "https://supabase.com/careers",
    "vercel": "https://vercel.com/careers",
    "resend": "https://resend.com/careers",
    "linear": "https://linear.app/careers",
    "modal": "https://modal.com/careers",
    "posthog": "https://posthog.com/careers",
    "railway": "https://railway.app/careers",
    "stripe": "https://stripe.com/jobs",
    "datadog": "https://careers.datadoghq.com",
}


def get_career_url(company: str | None = None, apply_url: str | None = None) -> str | None:
    """Resolve the canonical, active career portal URL for a company or job listing.

    Priority:
    1. Curated company mapping.
    2. ATS board extraction (Ashby, Greenhouse, Lever, SmartRecruiters, Workable).
    3. Dedicated careers subdomain or path.
    4. Fallback root domain.
    """
    if company:
        norm = company.strip().lower()
        if norm in KNOWN_COMPANY_CAREERS:
            return KNOWN_COMPANY_CAREERS[norm]

    if not apply_url:
        return None

    try:
        parsed = urlparse(apply_url)
        host = (parsed.netloc or "").lower()
        path = parsed.path or ""
        scheme = parsed.scheme or "https"

        if not host:
            return None

        # Ashby: jobs.ashbyhq.com/{company_slug}/...
        if "ashbyhq.com" in host:
            parts = [p for p in path.split("/") if p]
            if parts:
                return f"https://jobs.ashbyhq.com/{parts[0]}"
            return "https://jobs.ashbyhq.com"

        # Greenhouse: job-boards.greenhouse.io/{board}/... or boards.greenhouse.io/{board}/...
        if "greenhouse.io" in host:
            m = re.search(r"for=([^&]+)", parsed.query)
            if m:
                return f"https://job-boards.greenhouse.io/{m.group(1)}"
            parts = [p for p in path.split("/") if p]
            if parts:
                return f"{scheme}://{host}/{parts[0]}"
            return f"{scheme}://{host}"

        # Lever: jobs.lever.co/{company_slug}/...
        if "lever.co" in host:
            parts = [p for p in path.split("/") if p]
            if parts:
                return f"https://jobs.lever.co/{parts[0]}"
            return "https://jobs.lever.co"

        # SmartRecruiters: jobs.smartrecruiters.com/{company_slug}/...
        if "smartrecruiters.com" in host:
            parts = [p for p in path.split("/") if p]
            if parts:
                return f"https://jobs.smartrecruiters.com/{parts[0]}"
            return "https://jobs.smartrecruiters.com"

        # Workable: apply.workable.com/{company_slug}/...
        if "workable.com" in host:
            parts = [p for p in path.split("/") if p]
            if parts:
                return f"https://apply.workable.com/{parts[0]}"
            return "https://apply.workable.com"

        # Dedicated careers subdomains: careers.company.com or jobs.company.com
        if host.startswith("careers.") or host.startswith("jobs."):
            return f"{scheme}://{host}"

        # Paths with /careers or /jobs
        if "/careers" in path.lower():
            # Keep up to /careers
            idx = path.lower().find("/careers")
            return f"{scheme}://{host}{path[:idx + 8]}"

        if "/jobs" in path.lower():
            idx = path.lower().find("/jobs")
            return f"{scheme}://{host}{path[:idx + 5]}"

        # Fallback to root domain
        return f"{scheme}://{host}"
    except Exception:
        return apply_url
