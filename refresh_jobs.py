#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

DEPENDENCY_ERROR = ""

try:
    import requests
except ModuleNotFoundError:
    requests = None
    DEPENDENCY_ERROR = "Missing dependency: requests. Run `pip3 install -r requirements.txt`."

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    BeautifulSoup = None
    if not DEPENDENCY_ERROR:
        DEPENDENCY_ERROR = "Missing dependency: beautifulsoup4. Run `pip3 install -r requirements.txt`."

import import_digest
import server

BASE_DIR = Path(__file__).resolve().parent
SOURCE_CATALOG_PATH = BASE_DIR / "data" / "source_catalog.json"
GENERATED_DIGEST_PATH = BASE_DIR / "data" / "generated_digest.json"
GENERATED_REPORT_PATH = BASE_DIR / "data" / "refresh_report.json"
REQUEST_TIMEOUT_SECONDS = 20
DETAIL_FETCH_TIMEOUT_SECONDS = 12
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)

PUBLIC_COMPANIES = {
    "airbnb": ("public", "Large public company", "NASDAQ: ABNB"),
    "alphabet": ("public", "Large public company", "NASDAQ: GOOGL"),
    "amazon": ("public", "Large public company", "NASDAQ: AMZN"),
    "apple": ("public", "Large public company", "NASDAQ: AAPL"),
    "booking.com": ("public", "Large public company", "NASDAQ: BKNG"),
    "block": ("public", "Large public company", "NYSE: XYZ"),
    "coinbase": ("public", "Large public company", "NASDAQ: COIN"),
    "doordash": ("public", "Large public company", "NASDAQ: DASH"),
    "ebay": ("public", "Large public company", "NASDAQ: EBAY"),
    "etsy": ("public", "Large public company", "NASDAQ: ETSY"),
    "google": ("public", "Large public company", "NASDAQ: GOOGL"),
    "instacart": ("public", "Large public company", "NASDAQ: CART"),
    "klarna": ("private", "Late-stage private company", "Private company, no public shares"),
    "linkedin": ("public", "Large public company", "Microsoft subsidiary, public via NASDAQ: MSFT"),
    "microsoft": ("public", "Large public company", "NASDAQ: MSFT"),
    "meta": ("public", "Large public company", "NASDAQ: META"),
    "nexhealth": ("private", "Growth-stage private company", "Private company, no public shares"),
    "paypal": ("public", "Large public company", "NASDAQ: PYPL"),
    "pinterest": ("public", "Large public company", "NYSE: PINS"),
    "postmates": ("public", "Large public company", "Uber subsidiary, public via NYSE: UBER"),
    "shopify": ("public", "Large public company", "NASDAQ: SHOP"),
    "square": ("public", "Large public company", "NYSE: XYZ"),
    "stripe": ("private", "Late-stage private company", "Private company, no public shares"),
    "toast": ("public", "Large public company", "NYSE: TOST"),
    "walmart": ("public", "Large public company", "NYSE: WMT"),
    "robinhood": ("public", "Large public company", "NASDAQ: HOOD"),
    "sofi": ("public", "Large public company", "NASDAQ: SOFI"),
    "wayfair": ("public", "Large public company", "NYSE: W"),
    "uber": ("public", "Large public company", "NYSE: UBER"),
    "affirm": ("public", "Large public company", "NASDAQ: AFRM"),
    "brex": ("private", "Late-stage private company", "Private company, no public shares"),
    "chime": ("private", "Late-stage private company", "Private company, no public shares"),
    "gusto": ("private", "Late-stage private company", "Private company, no public shares"),
    "lyft": ("public", "Large public company", "NASDAQ: LYFT"),
    "mercari": ("public", "Large public company", "TSE: 4385"),
    "poshmark": ("public", "Large public company", "NAVER-owned subsidiary"),
    "stubhub": ("private", "Growth-stage private company", "Private company, no public shares"),
}

BENEFIT_PATTERNS = [
    r"401\(k\)",
    r"bonus",
    r"commuter",
    r"dental",
    r"equity",
    r"espp",
    r"gym",
    r"health",
    r"medical",
    r"parental leave",
    r"pto",
    r"rsu",
    r"vision",
    r"wellness",
]
EQUITY_PATTERNS = [r"\bequity\b", r"\brsu[s]?\b", r"\bespp\b", r"stock options?"]
RECRUITER_PATTERNS = [
    r"recruiter[:\s]+([A-Z][A-Za-z.\- ]+)",
    r"hiring manager[:\s]+([A-Z][A-Za-z.\- ]+)",
]
CLOSED_PATTERNS = [
    "no longer accepting applications",
    "applications have closed",
    "this job is closed",
    "job expired",
    "position filled",
]
SALARY_PATTERNS = [
    re.compile(
        r"\$ ?(?P<min>\d{2,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(?:-|to)\s*\$ ?(?P<max>\d{2,3}(?:,\d{3})+|\d+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\$ ?(?P<min>\d{2,3}(?:\.\d+)?)k\s*(?:-|to)\s*\$ ?(?P<max>\d{2,3}(?:\.\d+)?)k",
        re.IGNORECASE,
    ),
]


@dataclass
class Criteria:
    role_name: str
    city: str
    state: str
    title_keywords: list[str]
    preferred_industries: list[str]
    bay_area_keywords: list[str]
    salary_min: int
    salary_max: int
    min_benefits_count: int
    max_jobs_per_day: int
    target_jobs_per_day: int
    fallback_salary_min: int
    fallback_salary_max: int


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())

    def get_text(self) -> str:
        return " ".join(self.parts)


def build_title_keywords(role_name: str, fallback_keywords: list[str]) -> list[str]:
    normalized_role = " ".join(role_name.lower().split())
    keywords = [normalized_role] if normalized_role else []
    default_keywords = [" ".join(keyword.lower().split()) for keyword in fallback_keywords]

    if normalized_role in {"", "product manager"}:
        keywords.extend(default_keywords)

    seen = []
    for keyword in keywords:
        if keyword and keyword not in seen:
            seen.append(keyword)
    return seen


def load_source_catalog() -> tuple[Criteria, list[dict]]:
    payload = json.loads(SOURCE_CATALOG_PATH.read_text())
    criteria = payload["criteria"]
    search_preferences = server.load_state().get("searchPreferences", server.default_search_preferences())
    role_name = search_preferences.get("roleName", "Product Manager")
    city = search_preferences.get("city", "San Francisco")
    state_name = search_preferences.get("state", "CA")
    location_keywords = [f"{city}".lower(), f"{city}, {state_name}".lower(), state_name.lower()]
    return (
        Criteria(
            role_name=role_name,
            city=city,
            state=state_name,
            title_keywords=build_title_keywords(role_name, criteria.get("titleKeywords", [])),
            preferred_industries=[item.lower() for item in criteria["preferredIndustries"]],
            bay_area_keywords=location_keywords,
            salary_min=int(search_preferences.get("compMin", criteria["salaryMin"])),
            salary_max=int(search_preferences.get("compMax", criteria["salaryMax"])),
            min_benefits_count=int(criteria["minBenefitsCount"]),
            max_jobs_per_day=int(search_preferences.get("resultLimit", criteria.get("maxJobsPerDay", 50))),
            target_jobs_per_day=int(search_preferences.get("resultLimit", criteria.get("targetJobsPerDay", 50))),
            fallback_salary_min=int(min(search_preferences.get("compMin", criteria["salaryMin"]), criteria.get("fallbackSalaryMin", 170000))),
            fallback_salary_max=int(max(search_preferences.get("compMax", criteria["salaryMax"]), criteria.get("fallbackSalaryMax", 240000))),
        ),
        payload["sources"],
    )


def require_refresh_dependencies() -> None:
    if DEPENDENCY_ERROR:
        raise RuntimeError(DEPENDENCY_ERROR)


def requests_session():
    require_refresh_dependencies()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def fetch_url(session: requests.Session, url: str) -> requests.Response:
    response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response


def fetch_detail_url(session: requests.Session, url: str) -> requests.Response:
    response = session.get(url, timeout=DETAIL_FETCH_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response


def clean_html_text(value: str) -> str:
    if BeautifulSoup is not None:
        return re.sub(r"\s+", " ", BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)).strip()
    parser = TextExtractor()
    parser.feed(value or "")
    return re.sub(r"\s+", " ", parser.get_text()).strip()


def extract_salary(text: str) -> tuple[str, int | None, int | None]:
    for pattern in SALARY_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        low = normalize_salary_number(match.group("min"))
        high = normalize_salary_number(match.group("max"))
        if low and high:
            salary = f"${low:,.0f}-${high:,.0f}"
            return salary, int(low), int(high)
    return "", None, None


def normalize_salary_number(value: str) -> float | None:
    cleaned = value.lower().replace(",", "").strip()
    if cleaned.endswith("k"):
        return float(cleaned[:-1]) * 1000
    try:
        number = float(cleaned)
    except ValueError:
        return None
    if number < 1000:
        number *= 1000
    return number


def salary_band_fit(low: int | None, high: int | None, criteria: Criteria) -> tuple[str, bool]:
    if low is None or high is None:
        return "overlap", False
    overlaps = high >= criteria.salary_min and low <= criteria.salary_max
    if not overlaps:
        return "overlap", False
    exact = low >= criteria.salary_min and high <= criteria.salary_max
    return ("exact" if exact else "overlap"), True


def infer_company_metadata(company: str, source: dict) -> tuple[str, str, str]:
    explicit_status = str(source.get("companyStatus", "")).strip().lower()
    explicit_size = str(source.get("companySizeHint", "")).strip()
    explicit_shares = str(source.get("companySharesNote", "")).strip()
    if explicit_status in {"public", "private"}:
        status = explicit_status
        size = explicit_size or ("Large public company" if status == "public" else "Private company")
        shares = explicit_shares or (
            "Public company, public shares available"
            if status == "public"
            else "Private company, no public shares"
        )
        return status, size, shares

    company_key = company.lower().strip()
    if company_key in PUBLIC_COMPANIES:
        status, size, shares = PUBLIC_COMPANIES[company_key]
        return status, size, shares
    return "private", explicit_size or "Private company", explicit_shares or "Private company, no public shares"


def collect_benefits(text: str) -> list[str]:
    matches = []
    lowered = text.lower()
    for pattern in BENEFIT_PATTERNS:
        if re.search(pattern, lowered):
            matches.append(pattern.replace(r"\b", "").replace(r"\(", "(").replace(r"\)", ")"))
    seen = []
    for match in matches:
        label = match.upper() if match in {"espp", "pto"} else match.title()
        if label not in seen:
            seen.append(label)
    return seen


def infer_equity_status(text: str, company_status: str) -> str:
    lowered = text.lower()
    if any(re.search(pattern, lowered) for pattern in EQUITY_PATTERNS):
        return "Explicitly listed"
    if company_status == "public":
        return "Unconfirmed, likely part of public-company compensation"
    return "Unconfirmed"


def infer_application_status(text: str) -> str:
    lowered = text.lower()
    for pattern in CLOSED_PATTERNS:
        if pattern in lowered:
            return "no longer accepting applications"
    return "open"


def infer_recruiter(text: str) -> tuple[str, str]:
    for pattern in RECRUITER_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip(), ""
    email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE)
    if email_match:
        return "", email_match.group(0)
    linkedin_match = re.search(r"https?://(?:www\.)?linkedin\.com/[^\s\"']+", text)
    if linkedin_match:
        return "", linkedin_match.group(0)
    return "", ""


def build_fit_note(company_status: str, industries: Iterable[str], title: str, source_name: str) -> str:
    industry_text = ", ".join(sorted(set(item for item in industries if item)))
    if company_status == "public" and industry_text:
        return f"Public-company option with relevance to {industry_text}; surfaced via {source_name}."
    if industry_text:
        return f"Relevant to {industry_text}; surfaced via {source_name}."
    return f"Surfaced via {source_name}."


def matches_location(location: str, criteria: Criteria) -> bool:
    lowered = location.lower()
    return any(keyword in lowered for keyword in criteria.bay_area_keywords)


def infer_location_from_text(text: str, criteria: Criteria) -> str:
    lowered = text.lower()
    for keyword in criteria.bay_area_keywords:
        if keyword in lowered:
            return keyword.title()
    return ""


def matches_title(title: str, criteria: Criteria) -> bool:
    lowered = title.lower()
    return any(keyword in lowered for keyword in criteria.title_keywords)


def collect_job_text(title: str, description: str, salary: str, benefits: list[str], location: str) -> str:
    return " ".join([title, description, salary, location, *benefits]).strip()


def should_keep_job(job: dict, criteria: Criteria) -> tuple[bool, str]:
    if not matches_title(job["title"], criteria):
        return False, "title_mismatch"
    if not matches_location(job["location"], criteria):
        return False, "location_mismatch"
    if not server.is_open_application_status(job["applicationStatus"]):
        return False, "closed"

    band_fit, overlaps = salary_band_fit(job["salaryMin"], job["salaryMax"], criteria)
    job["salaryBandFit"] = band_fit
    if not overlaps:
        return False, "salary_out_of_range"

    if len(job["benefits"]) < criteria.min_benefits_count:
        return False, "missing_benefits"

    if job["equityStatus"] == "Unconfirmed" and job["companyStatus"] != "public":
        return False, "missing_equity"

    return True, "kept"


def job_matches_fallback(job: dict, criteria: Criteria) -> tuple[bool, str]:
    if not matches_title(job["title"], criteria):
        return False, "title_mismatch"
    if not matches_location(job["location"], criteria):
        return False, "location_mismatch"
    if not server.is_open_application_status(job["applicationStatus"]):
        return False, "closed"

    low = job["salaryMin"]
    high = job["salaryMax"]
    if low is None or high is None:
        return False, "missing_salary"
    overlaps = high >= criteria.fallback_salary_min and low <= criteria.fallback_salary_max
    if not overlaps:
        return False, "fallback_salary_out_of_range"

    if job["companyStatus"] == "public":
        return True, "fallback_kept"

    if bool(job["benefits"]):
        return True, "fallback_kept"
    return False, "missing_benefits"


def dedupe_jobs(jobs: list[dict]) -> list[dict]:
    deduped = {}
    for job in jobs:
        key = (job["company"].lower(), job["title"].lower(), job["link"])
        if key not in deduped:
            deduped[key] = job
    return list(deduped.values())


def job_priority(job: dict) -> tuple:
    source_name = job.get("source", "").lower()
    preferred_source_rank = 0
    if "linkedin" in source_name:
        preferred_source_rank = 0
    elif "careers" in source_name or job.get("sourceType") == "company":
        preferred_source_rank = 1
    else:
        preferred_source_rank = 2

    salary_low = job.get("salaryMin") or 0
    strict_overlap_penalty = 0 if job["salaryBandFit"] == "exact" else 1
    public_rank = 0 if job["companyStatus"] == "public" else 1
    fallback_rank = 1 if job.get("matchTier") == "fallback" else 0
    return (
        fallback_rank,
        public_rank,
        strict_overlap_penalty,
        preferred_source_rank,
        -salary_low,
        job["company"].lower(),
        job["title"].lower(),
    )


def normalize_job_record(job: dict, source: dict, criteria: Criteria) -> tuple[dict | None, str]:
    company = job.get("company") or source.get("company") or "Unknown company"
    metadata_source = {
        "companyStatus": job.get("companyStatus") or source.get("companyStatus"),
        "companySizeHint": job.get("companySizeHint") or source.get("companySizeHint"),
        "companySharesNote": job.get("companySharesNote") or source.get("companySharesNote"),
    }
    company_status, company_size_hint, company_shares_note = infer_company_metadata(company, metadata_source)
    industries = [item.lower() for item in (job.get("industries") or source.get("industries", []))]
    body_text = job.get("description", "")
    full_text = collect_job_text(
        job.get("title", ""),
        body_text,
        job.get("salary", ""),
        job.get("benefits", []),
        job.get("location", ""),
    )
    location = job.get("location", "").strip() or infer_location_from_text(full_text, criteria)

    salary_text = job.get("salary", "")
    salary_low = job.get("salaryMin")
    salary_high = job.get("salaryMax")
    if not salary_text or salary_low is None or salary_high is None:
        extracted_salary, salary_low, salary_high = extract_salary(full_text)
        if extracted_salary:
            salary_text = extracted_salary

    benefits = job.get("benefits") or collect_benefits(full_text)
    recruiter_name = job.get("recruiterName", "")
    recruiter_contact = job.get("recruiterContact", "")
    if not recruiter_name and not recruiter_contact:
        recruiter_name, recruiter_contact = infer_recruiter(full_text)

    normalized = {
        "id": job.get("id") or f"{source['name'].lower().replace(' ', '-')}-{abs(hash(job.get('link', '')))}",
        "title": job.get("title", "").strip(),
        "company": company,
        "companyStatus": company_status,
        "companySizeHint": company_size_hint,
        "companySharesNote": company_shares_note,
        "location": location,
        "salary": salary_text,
        "salaryMin": salary_low,
        "salaryMax": salary_high,
        "salaryBandFit": "overlap",
        "equityStatus": job.get("equityStatus") or infer_equity_status(full_text, company_status),
        "benefits": benefits,
        "recruiterName": recruiter_name,
        "recruiterContact": recruiter_contact,
        "source": source["name"],
        "sourceType": source.get("sourceType", "import"),
        "link": job.get("link", "").strip(),
        "fitNote": job.get("fitNote") or build_fit_note(company_status, industries, job.get("title", ""), source["name"]),
        "applicationStatus": job.get("applicationStatus") or infer_application_status(full_text),
        "isNewToday": True,
        "matchTier": "strict",
        "shortlisted": False,
    }

    keep, reason = should_keep_job(normalized, criteria)
    if not keep:
        return None, reason

    normalized["salary"] = normalized["salary"] or ""
    return normalized, "kept"


def fetch_greenhouse_jobs(session: requests.Session, source: dict) -> list[dict]:
    jobs = []
    for board in source.get("boards", []):
        url = f"https://boards-api.greenhouse.io/v1/boards/{board['boardToken']}/jobs?content=true"
        response = fetch_url(session, url)
        payload = response.json()
        for item in payload.get("jobs", []):
            content_text = clean_html_text(item.get("content", ""))
            metadata_values = [str(value.get("value", "")) for value in item.get("metadata", [])]
            text_blob = " ".join([content_text, *metadata_values])
            salary, low, high = extract_salary(text_blob)
            jobs.append(
                {
                    "id": f"greenhouse-{item.get('id')}",
                    "title": item.get("title", ""),
                    "company": board.get("company", ""),
                    "companyStatus": board.get("companyStatus", ""),
                    "companySizeHint": board.get("companySizeHint", ""),
                    "companySharesNote": board.get("companySharesNote", ""),
                    "industries": board.get("industries", []),
                    "location": item.get("location", {}).get("name", ""),
                    "salary": salary,
                    "salaryMin": low,
                    "salaryMax": high,
                    "benefits": collect_benefits(text_blob),
                    "equityStatus": infer_equity_status(text_blob, board.get("companyStatus", "private")),
                    "link": item.get("absolute_url", ""),
                    "description": text_blob,
                    "applicationStatus": "open",
                }
            )
    return jobs


def fetch_lever_jobs(session: requests.Session, source: dict) -> list[dict]:
    jobs = []
    for site in source.get("sites", []):
        url = f"https://api.lever.co/v0/postings/{site['site']}?mode=json"
        response = fetch_url(session, url)
        payload = response.json()
        for item in payload:
            description_parts = [
                item.get("descriptionPlain", ""),
                item.get("additionalPlain", ""),
                item.get("salaryDescriptionPlain", ""),
            ]
            for list_item in item.get("lists", []):
                description_parts.append(clean_html_text(list_item.get("content", "")))
            text_blob = " ".join(part for part in description_parts if part)
            salary_range = item.get("salaryRange") or {}
            salary_low = salary_range.get("min")
            salary_high = salary_range.get("max")
            salary = ""
            if salary_low and salary_high:
                salary = f"${salary_low:,.0f}-${salary_high:,.0f}"
            if not salary:
                salary, salary_low, salary_high = extract_salary(text_blob)
            jobs.append(
                {
                    "id": f"lever-{item.get('id')}",
                    "title": item.get("text", ""),
                    "company": site.get("company", ""),
                    "companyStatus": site.get("companyStatus", ""),
                    "companySizeHint": site.get("companySizeHint", ""),
                    "companySharesNote": site.get("companySharesNote", ""),
                    "industries": site.get("industries", []),
                    "location": item.get("categories", {}).get("location", ""),
                    "salary": salary,
                    "salaryMin": int(salary_low) if salary_low else None,
                    "salaryMax": int(salary_high) if salary_high else None,
                    "benefits": collect_benefits(text_blob),
                    "equityStatus": infer_equity_status(text_blob, site.get("companyStatus", "private")),
                    "link": item.get("hostedUrl", ""),
                    "description": text_blob,
                    "applicationStatus": "open",
                }
            )
    return jobs


def extract_links_from_listing(html: str, base_url: str, source: dict) -> list[str]:
    require_refresh_dependencies()
    soup = BeautifulSoup(html, "html.parser")
    links = []
    patterns = [re.compile(pattern) for pattern in source.get("detailLinkPatterns", [])]
    allowed_hosts = set(source.get("allowedHosts", []))
    for anchor in soup.select("a[href]"):
        href = urljoin(base_url, anchor.get("href", ""))
        parsed = urlparse(href)
        host = parsed.netloc.lower()
        if allowed_hosts and not any(allowed in host for allowed in allowed_hosts):
            continue
        if patterns and not any(pattern.search(parsed.path) for pattern in patterns):
            continue
        links.append(href.split("#", 1)[0])
    deduped = []
    for link in links:
        if link not in deduped:
            deduped.append(link)
    return deduped[: int(source.get("maxDetailPages", 20))]


def parse_jobposting_json_ld(soup: BeautifulSoup) -> list[dict]:
    jobs = []
    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text()
        if not raw.strip():
            continue
        try:
            payload = json.loads(unescape(raw))
        except json.JSONDecodeError:
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                jobs.append(item)
    return jobs


def parse_html_detail(session: requests.Session, source: dict, detail_url: str) -> dict | None:
    require_refresh_dependencies()
    response = fetch_detail_url(session, detail_url)
    soup = BeautifulSoup(response.text, "html.parser")
    text_content = soup.get_text(" ", strip=True)
    job_postings = parse_jobposting_json_ld(soup)
    job_posting = job_postings[0] if job_postings else {}

    title = (
        job_posting.get("title")
        or (soup.find("meta", property="og:title") or {}).get("content")
        or (soup.find("title").get_text(strip=True) if soup.find("title") else "")
    )
    company = source.get("company") or ""
    hiring_org = job_posting.get("hiringOrganization") or {}
    if isinstance(hiring_org, dict):
        company = hiring_org.get("name") or company
    location = ""
    job_location = job_posting.get("jobLocation")
    if isinstance(job_location, dict):
        address = job_location.get("address") or {}
        if isinstance(address, dict):
            parts = [
                address.get("addressLocality", ""),
                address.get("addressRegion", ""),
                address.get("addressCountry", ""),
            ]
            location = ", ".join(part for part in parts if part)
    if not location:
        location = source.get("defaultLocation", "")

    description = clean_html_text(job_posting.get("description", "") or text_content)
    salary = ""
    salary_low = None
    salary_high = None
    base_salary = job_posting.get("baseSalary")
    if isinstance(base_salary, dict):
        salary_value = base_salary.get("value") or {}
        if isinstance(salary_value, dict):
            salary_low = normalize_salary_number(str(salary_value.get("minValue", "")).strip())
            salary_high = normalize_salary_number(str(salary_value.get("maxValue", "")).strip())
            if salary_low and salary_high:
                salary = f"${salary_low:,.0f}-${salary_high:,.0f}"
    if not salary:
        salary, salary_low, salary_high = extract_salary(description)

    return {
        "title": title,
        "company": company,
        "location": location,
        "salary": salary,
        "salaryMin": int(salary_low) if salary_low else None,
        "salaryMax": int(salary_high) if salary_high else None,
        "benefits": collect_benefits(description),
        "equityStatus": infer_equity_status(description, source.get("companyStatus", "")),
        "link": detail_url,
        "description": description,
        "applicationStatus": infer_application_status(text_content),
    }


def fetch_html_search_jobs(session: requests.Session, source: dict) -> list[dict]:
    jobs = []
    for listing_url in source.get("listingUrls", []):
        try:
            response = fetch_url(session, listing_url)
        except requests.RequestException:
            continue
        detail_links = extract_links_from_listing(response.text, listing_url, source)
        for detail_url in detail_links:
            try:
                job = parse_html_detail(session, source, detail_url)
            except requests.RequestException:
                continue
            if job:
                jobs.append(job)
    return jobs


def fetch_source_jobs(session: requests.Session, source: dict) -> list[dict]:
    source_type = source["type"]
    if source_type == "greenhouse":
        return fetch_greenhouse_jobs(session, source)
    if source_type == "lever":
        return fetch_lever_jobs(session, source)
    if source_type == "html_search":
        return fetch_html_search_jobs(session, source)
    return []


def build_digest(jobs_by_source: dict[str, list[dict]], criteria: Criteria, sources: list[dict]) -> tuple[dict, dict]:
    normalized_jobs = []
    fallback_jobs = []
    diagnostics = {"sources": {}, "summary": {}}
    for source in sources:
        if not source.get("enabled", True):
            continue
        source_name = source["name"]
        source_diag = diagnostics["sources"].setdefault(
            source_name,
            {
                "fetched": len(jobs_by_source.get(source_name, [])),
                "strict_kept": 0,
                "fallback_kept": 0,
                "duplicates_removed": 0,
                "rejections": {},
            },
        )
        for job in jobs_by_source.get(source["name"], []):
            normalized, reason = normalize_job_record(job, source, criteria)
            if normalized:
                normalized_jobs.append(normalized)
                source_diag["strict_kept"] += 1
                continue
            source_diag["rejections"][reason] = source_diag["rejections"].get(reason, 0) + 1

            company = job.get("company") or source.get("company") or "Unknown company"
            metadata_source = {
                "companyStatus": job.get("companyStatus") or source.get("companyStatus"),
                "companySizeHint": job.get("companySizeHint") or source.get("companySizeHint"),
                "companySharesNote": job.get("companySharesNote") or source.get("companySharesNote"),
            }
            company_status, company_size_hint, company_shares_note = infer_company_metadata(company, metadata_source)
            industries = [item.lower() for item in (job.get("industries") or source.get("industries", []))]
            body_text = job.get("description", "")
            full_text = collect_job_text(
                job.get("title", ""),
                body_text,
                job.get("salary", ""),
                job.get("benefits", []),
                job.get("location", ""),
            )
            location = job.get("location", "").strip() or infer_location_from_text(full_text, criteria)
            salary_text = job.get("salary", "")
            salary_low = job.get("salaryMin")
            salary_high = job.get("salaryMax")
            if not salary_text or salary_low is None or salary_high is None:
                extracted_salary, salary_low, salary_high = extract_salary(full_text)
                if extracted_salary:
                    salary_text = extracted_salary
            fallback_job = {
                "id": job.get("id") or f"{source['name'].lower().replace(' ', '-')}-{abs(hash(job.get('link', '')))}",
                "title": job.get("title", "").strip(),
                "company": company,
                "companyStatus": company_status,
                "companySizeHint": company_size_hint,
                "companySharesNote": company_shares_note,
                "location": location,
                "salary": salary_text,
                "salaryMin": salary_low,
                "salaryMax": salary_high,
                "salaryBandFit": "overlap",
                "equityStatus": job.get("equityStatus") or infer_equity_status(full_text, company_status),
                "benefits": job.get("benefits") or collect_benefits(full_text),
                "recruiterName": job.get("recruiterName", ""),
                "recruiterContact": job.get("recruiterContact", ""),
                "source": source["name"],
                "sourceType": source.get("sourceType", "import"),
                "link": job.get("link", "").strip(),
                "fitNote": f"{build_fit_note(company_status, industries, job.get('title', ''), source['name'])} Added as a near-match to fill the daily digest.",
                "applicationStatus": job.get("applicationStatus") or infer_application_status(full_text),
                "isNewToday": True,
                "matchTier": "fallback",
                "shortlisted": False,
            }
            fallback_keep, fallback_reason = job_matches_fallback(fallback_job, criteria)
            if fallback_keep:
                fallback_jobs.append(fallback_job)
                source_diag["fallback_kept"] += 1
            else:
                source_diag["rejections"][fallback_reason] = source_diag["rejections"].get(fallback_reason, 0) + 1

    deduped_jobs = dedupe_jobs(normalized_jobs)
    deduped_fallback_jobs = dedupe_jobs(fallback_jobs)
    strict_keys = {(job["company"].lower(), job["title"].lower(), job["link"]) for job in deduped_jobs}
    backfill = [
        job
        for job in deduped_fallback_jobs
        if (job["company"].lower(), job["title"].lower(), job["link"]) not in strict_keys
    ]
    deduped_jobs.sort(key=job_priority)
    backfill.sort(key=job_priority)

    combined_jobs = list(deduped_jobs)
    if len(combined_jobs) < criteria.target_jobs_per_day:
        combined_jobs.extend(backfill[: criteria.target_jobs_per_day - len(combined_jobs)])

    limited_jobs = combined_jobs[: criteria.max_jobs_per_day]
    strict_count = len(deduped_jobs)
    fallback_count = max(0, len(limited_jobs) - strict_count)
    diagnostics["summary"] = {
        "strict_matches": strict_count,
        "fallback_matches": fallback_count,
        "final_jobs": len(limited_jobs),
        "target_jobs_per_day": criteria.target_jobs_per_day,
        "max_jobs_per_day": criteria.max_jobs_per_day,
    }
    criteria_sources = [source["name"] for source in sources if source.get("enabled", True)]
    digest = {
        "date": server.today_key(),
        "summary": (
            f"Daily digest for {criteria.role_name} roles in {criteria.city}, {criteria.state}. "
            f"Refreshed from {len(criteria_sources)} configured sources, capped at {criteria.max_jobs_per_day} results."
        ),
        "searchPreferences": {
            "roleName": criteria.role_name,
            "city": criteria.city,
            "state": criteria.state,
            "compMin": criteria.salary_min,
            "compMax": criteria.salary_max,
            "resultLimit": criteria.max_jobs_per_day,
        },
        "criteria": {
            "location": f"{criteria.city}, {criteria.state}",
            "salary": f"${criteria.salary_min:,.0f}-${criteria.salary_max:,.0f}",
            "industries": ["Fintech", "Marketplaces"],
            "sources": criteria_sources,
            "ranking": "Public companies first, then private/startups",
        },
        "jobs": limited_jobs,
    }
    strict_keys = {(job["company"].lower(), job["title"].lower(), job["link"]) for job in deduped_jobs}
    fallback_keys = {(job["company"].lower(), job["title"].lower(), job["link"]) for job in deduped_fallback_jobs}
    for source_name, source_diag in diagnostics["sources"].items():
        fetched_jobs = jobs_by_source.get(source_name, [])
        source_diag["duplicates_removed"] = max(
            0,
            (source_diag["strict_kept"] + source_diag["fallback_kept"]) - len(
                {
                    (job.get("company", "").lower(), job.get("title", "").lower(), job.get("link", ""))
                    for job in fetched_jobs
                }
            ),
        )
    return digest, diagnostics


def fetch_all_jobs(criteria: Criteria, sources: list[dict]) -> tuple[dict, dict]:
    session = requests_session()
    collected = {}
    source_report = {}
    enabled_sources = [source for source in sources if source.get("enabled", True)]
    total_sources = len(enabled_sources)
    for index, source in enumerate(enabled_sources, start=1):
        print(f"[{index}/{total_sources}] Fetching {source['name']}...", flush=True)
        if not source.get("enabled", True):
            continue
        try:
            jobs = fetch_source_jobs(session, source)
            collected[source["name"]] = jobs
            source_report[source["name"]] = {"status": "ok", "fetched": len(jobs)}
            print(
                f"[{index}/{total_sources}] {source['name']}: fetched {len(jobs)} candidate jobs",
                flush=True,
            )
        except requests.RequestException as error:
            collected[source["name"]] = []
            source_report[source["name"]] = {"status": "error", "error": str(error)}
            print(
                f"[{index}/{total_sources}] {source['name']}: error {error}",
                flush=True,
            )
    return collected, source_report


def main() -> int:
    if DEPENDENCY_ERROR:
        print(DEPENDENCY_ERROR, file=sys.stderr)
        return 1
    criteria, sources = load_source_catalog()
    jobs_by_source, source_report = fetch_all_jobs(criteria, sources)
    digest, diagnostics = build_digest(jobs_by_source, criteria, sources)
    GENERATED_DIGEST_PATH.write_text(json.dumps(digest, indent=2))
    GENERATED_REPORT_PATH.write_text(
        json.dumps(
            {
                "criteria": {
                    "roleName": criteria.role_name,
                    "city": criteria.city,
                    "state": criteria.state,
                    "salaryMin": criteria.salary_min,
                    "salaryMax": criteria.salary_max,
                    "resultLimit": criteria.max_jobs_per_day,
                },
                "fetch": source_report,
                "analysis": diagnostics,
            },
            indent=2,
        )
    )
    import_digest.import_payload_to_state(digest)

    print(
        json.dumps(
            {
                "ok": True,
                "output": str(GENERATED_DIGEST_PATH),
                "report": str(GENERATED_REPORT_PATH),
                "jobs": len(digest["jobs"]),
                "sources": source_report,
                "analysis": diagnostics["summary"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
