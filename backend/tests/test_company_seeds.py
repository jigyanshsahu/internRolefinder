from app.company_seeds import COMPANY_SEEDS
from app.aggregators import is_aggregator_domain


def test_company_seed_list_contains_all_requested_names():
    company_names = {seed["company_name"] for seed in COMPANY_SEEDS}
    assert len(COMPANY_SEEDS) == 120
    assert len(company_names) == 120
    assert {
        "Appening Infotech",
        "Guidanz",
        "CloudSEK",
        "Observe.AI",
        "Agnikul Cosmos",
        "Rapido",
    } <= company_names


def test_expanded_company_coverage_has_verified_websites():
    seeds_by_name = {seed["company_name"]: seed for seed in COMPANY_SEEDS}

    for company_name in (
        "Dream Monks",
        "Convertly",
        "SkillsCapital",
        "Velaris Intelligence",
        "Coffee Core",
        "Krutrim",
        "Classplus",
        "Plum",
        "Leegality",
        "Unlearn AI",
        "Detectify",
    ):
        assert seeds_by_name[company_name]["website_url"] is not None
        assert seeds_by_name[company_name]["website_url"].startswith("http")


def test_rejects_aggregators():
    for seed in COMPANY_SEEDS:
        careers = seed.get("careers_url")
        if careers:
            assert not is_aggregator_domain(careers)

    # Rejection of typical aggregator and non-direct platforms
    for agg in (
        "https://www.linkedin.com/jobs/view/123",
        "https://internshala.com/internship/detail/123",
        "https://wellfound.com/jobs",
        "https://www.naukri.com/job-listings",
        "https://www.indeed.com/viewjob?jk=123",
        "https://cutshort.io/job/123",
    ):
        assert is_aggregator_domain(agg) is True


def test_direct_career_sources_use_verified_official_lever_boards():
    seeds_by_name = {seed["company_name"]: seed for seed in COMPANY_SEEDS}

    assert seeds_by_name["Merkle Science"]["careers_url"] == "https://jobs.lever.co/merklescience"
    assert seeds_by_name["Drivetrain"]["careers_url"] == "https://jobs.lever.co/drivetrain"
    assert seeds_by_name["FamPay"]["careers_url"] == "https://jobs.lever.co/fampay"


def test_expanded_list_includes_verified_direct_sources():
    seeds_by_name = {seed["company_name"]: seed for seed in COMPANY_SEEDS}

    assert seeds_by_name["CloudSEK"]["careers_url"] == "https://job-boards.greenhouse.io/cloudsek"
    assert seeds_by_name["Entropik"]["careers_url"] == "https://apply.workable.com/entropik/"
    assert seeds_by_name["Observe.AI"]["careers_url"] == "https://job-boards.greenhouse.io/observeai"
    assert seeds_by_name["Unlearn AI"]["careers_url"] == "https://jobs.ashbyhq.com/unlearn.ai"
    assert seeds_by_name["Zluri"]["careers_url"] == "https://zluri.keka.com/careers/"
    assert seeds_by_name["SpotDraft"]["careers_url"] == "https://spotdraft.freshteam.com/jobs"
    assert seeds_by_name["Agnikul Cosmos"]["careers_url"] == "https://agnikul.zohorecruit.in/jobs/Careers"