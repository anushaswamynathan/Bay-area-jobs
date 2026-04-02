#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import date, datetime, timedelta
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import unquote

BASE_DIR = Path(__file__).resolve().parent
HOST = os.getenv("BAY_PM_JOBS_HOST", os.getenv("NIGHTLY_TODOS_HOST", "127.0.0.1"))
PORT = int(os.getenv("PORT", os.getenv("BAY_PM_JOBS_PORT", "4174")))
AUTO_REFRESH_MINUTES = max(15, int(os.getenv("BAY_PM_JOBS_AUTO_REFRESH_MINUTES", "60")))
REFRESH_REPORT_PATH = BASE_DIR / "data" / "refresh_report.json"


def utc_now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def today_key() -> str:
    return date.today().isoformat()


def yesterday_key_for(date_value: str) -> str:
    return (date.fromisoformat(date_value) - timedelta(days=1)).isoformat()


def default_search_preferences() -> dict:
    return {
        "roleName": "Product Manager",
        "city": "San Francisco",
        "state": "CA",
        "compMin": 190000,
        "compMax": 220000,
        "resultLimit": 50,
    }


def normalize_search_preferences(payload: dict | None, fallback: dict | None = None) -> dict:
    base = dict(fallback or default_search_preferences())
    payload = payload or {}
    role_name = str(payload.get("roleName", base["roleName"])).strip() or base["roleName"]
    city = str(payload.get("city", base["city"])).strip() or base["city"]
    state = str(payload.get("state", base["state"])).strip() or base["state"]
    comp_min = coerce_int(payload.get("compMin"), base["compMin"])
    comp_max = coerce_int(payload.get("compMax"), base["compMax"])
    result_limit = coerce_int(payload.get("resultLimit"), base["resultLimit"])
    result_limit = min(max(result_limit, 1), 100)
    if comp_min > comp_max:
        comp_min, comp_max = comp_max, comp_min
    return {
        "roleName": role_name,
        "city": city,
        "state": state,
        "compMin": comp_min,
        "compMax": comp_max,
        "resultLimit": result_limit,
    }


def search_preferences_to_criteria(preferences: dict, sources: list[str] | None = None) -> dict:
    location = ", ".join(part for part in [preferences.get("city", ""), preferences.get("state", "")] if part)
    return {
        "location": location or "San Francisco, CA",
        "radiusMiles": 50,
        "salary": f"${preferences['compMin']:,.0f}-${preferences['compMax']:,.0f}",
        "industries": ["Fintech", "Marketplaces"],
        "sources": sources or ["Company career pages", "LinkedIn", "Reputable job boards"],
        "ranking": "Public companies first, then private/startups",
    }


def create_seed_jobs() -> list[dict]:
    return [
        {
            "id": "uber-financial-products",
            "title": "Senior Product Manager, Financial Products",
            "company": "Uber",
            "companyStatus": "public",
            "companySizeHint": "Large public company",
            "companySharesNote": "NYSE: UBER",
            "location": "San Francisco, CA",
            "salary": "$190,000-$211,000",
            "salaryBandFit": "exact",
            "equityStatus": "Explicitly listed",
            "benefits": ["Equity award eligibility", "Bonus eligibility", "Comprehensive benefits package"],
            "recruiterName": "",
            "recruiterContact": "",
            "source": "Company career page",
            "sourceType": "company",
            "link": "https://www.uber.com/global/en/careers/list/145353/",
            "fitNote": "Large public company with fintech-adjacent product scope and strong compensation fit.",
            "isNewToday": True,
            "shownYesterday": False,
            "seenBefore": False,
            "applicationStatus": "open",
            "applied": False,
            "notInterested": False,
            "shortlisted": True,
        },
        {
            "id": "uber-courier-pricing",
            "title": "Senior Product Manager, Courier Pricing and Incentives",
            "company": "Uber",
            "companyStatus": "public",
            "companySizeHint": "Large public company",
            "companySharesNote": "NYSE: UBER",
            "location": "San Francisco, CA",
            "salary": "$190,000-$211,000",
            "salaryBandFit": "exact",
            "equityStatus": "Explicitly listed",
            "benefits": ["Equity award eligibility", "Bonus eligibility", "401(k)"],
            "recruiterName": "",
            "recruiterContact": "",
            "source": "Company career page",
            "sourceType": "company",
            "link": "https://www.uber.com/careers/list/154261",
            "fitNote": "Strong marketplace role at a public company with direct salary-band alignment.",
            "isNewToday": False,
            "shownYesterday": False,
            "seenBefore": False,
            "applicationStatus": "open",
            "applied": False,
            "notInterested": False,
            "shortlisted": False,
        },
        {
            "id": "airwallex-stablecoin",
            "title": "Senior Product Manager, Stablecoin",
            "company": "Airwallex",
            "companyStatus": "private",
            "companySizeHint": "Late-stage private company",
            "companySharesNote": "Private company, no public shares",
            "location": "San Francisco, CA",
            "salary": "$150,000-$220,000",
            "salaryBandFit": "overlap",
            "equityStatus": "Explicitly listed",
            "benefits": ["Equity", "Bonus", "Location-based benefits"],
            "recruiterName": "",
            "recruiterContact": "",
            "source": "Ashby",
            "sourceType": "job-board",
            "link": "https://jobs.ashbyhq.com/airwallex/426c17cb-4343-435d-a03e-c0b4e20b9109",
            "fitNote": "Excellent fintech relevance with compensation that overlaps the target band.",
            "isNewToday": True,
            "shownYesterday": False,
            "seenBefore": False,
            "applicationStatus": "open",
            "applied": False,
            "notInterested": False,
            "shortlisted": True,
        },
        {
            "id": "altruist-staff-pm",
            "title": "Senior / Staff Product Manager",
            "company": "Altruist",
            "companyStatus": "private",
            "companySizeHint": "Growth-stage private company",
            "companySharesNote": "Private company, no public shares",
            "location": "San Francisco, CA",
            "salary": "$203,000-$249,000",
            "salaryBandFit": "overlap",
            "equityStatus": "Explicitly listed for eligible positions",
            "benefits": ["Medical, dental, vision", "401(k) match", "Paid parental leave"],
            "recruiterName": "Marina Kostioutchenko, CFA",
            "recruiterContact": "https://www.linkedin.com/jobs/view/senior-staff-product-manager-at-altruist-4371342447",
            "source": "LinkedIn",
            "sourceType": "linkedin",
            "link": "https://www.linkedin.com/jobs/view/senior-staff-product-manager-at-altruist-4371342447",
            "fitNote": "High-quality fintech comp package, though the top end exceeds the preferred range.",
            "isNewToday": False,
            "shownYesterday": False,
            "seenBefore": False,
            "applicationStatus": "open",
            "applied": False,
            "notInterested": False,
            "shortlisted": False,
        },
        {
            "id": "traba-senior-pm",
            "title": "Senior Product Manager",
            "company": "Traba",
            "companyStatus": "private",
            "companySizeHint": "Startup",
            "companySharesNote": "Private company, no public shares",
            "location": "San Francisco, CA",
            "salary": "$180,000-$210,000",
            "salaryBandFit": "overlap",
            "equityStatus": "Explicitly listed",
            "benefits": ["Startup equity", "Health, dental, vision", "Flexible PTO", "Commuter benefits"],
            "recruiterName": "",
            "recruiterContact": "",
            "source": "Ashby",
            "sourceType": "job-board",
            "link": "https://jobs.ashbyhq.com/traba/b00513c3-56b8-4828-929c-2fe9f227b094",
            "fitNote": "Best marketplace startup fit in the current sample set.",
            "isNewToday": True,
            "shownYesterday": False,
            "seenBefore": False,
            "applicationStatus": "open",
            "applied": False,
            "notInterested": False,
            "shortlisted": True,
        },
        {
            "id": "airwallex-growth",
            "title": "Senior Product Manager, Growth",
            "company": "Airwallex",
            "companyStatus": "private",
            "companySizeHint": "Late-stage private company",
            "companySharesNote": "Private company, no public shares",
            "location": "San Francisco, CA",
            "salary": "$150,000-$220,000",
            "salaryBandFit": "overlap",
            "equityStatus": "Explicitly listed",
            "benefits": ["Equity", "Bonus", "Location-based benefits"],
            "recruiterName": "",
            "recruiterContact": "",
            "source": "Ashby",
            "sourceType": "job-board",
            "link": "https://jobs.ashbyhq.com/airwallex/458c1e45-697f-4770-8d0f-ab1d528b3baa",
            "fitNote": "Strong private fintech option with a broad growth charter.",
            "isNewToday": False,
            "shownYesterday": False,
            "seenBefore": False,
            "applicationStatus": "open",
            "applied": False,
            "notInterested": False,
            "shortlisted": False,
        },
    ]


def create_seed_state() -> dict:
    search_preferences = default_search_preferences()
    return {
        "schemaVersion": 2,
        "searchPreferences": search_preferences,
        "criteria": search_preferences_to_criteria(search_preferences),
        "digestsByDate": {
            today_key(): {
                "generatedAt": utc_now_iso(),
                "summary": "Public companies are ranked first, followed by high-signal private companies and startups.",
                "jobs": create_seed_jobs(),
            }
        },
        "lastUpdatedAt": utc_now_iso(),
    }


def coerce_int(value, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def coerce_string_list(value) -> list:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def is_open_application_status(value: str) -> bool:
    normalized = str(value or "open").strip().lower()
    closed_markers = {
        "closed",
        "expired",
        "inactive",
        "filled",
        "not accepting applications",
        "no longer accepting applications",
    }
    return normalized not in closed_markers


def job_key(job: dict) -> tuple[str, str, str]:
    return (
        str(job.get("company", "")).strip().lower(),
        str(job.get("title", "")).strip().lower(),
        str(job.get("link", "")).strip(),
    )


def normalize_job(job: dict, index: int) -> dict:
    company_status = str(job.get("companyStatus", "private")).strip().lower()
    if company_status not in {"public", "private"}:
        company_status = "private"

    recruiter_name = str(job.get("recruiterName", "")).strip()
    recruiter_contact = str(job.get("recruiterContact", "")).strip()
    title = str(job.get("title", "")).strip()
    company = str(job.get("company", "")).strip()
    link = str(job.get("link", "")).strip()
    location = str(job.get("location", "")).strip()
    salary = str(job.get("salary", "")).strip()
    source = str(job.get("source", "Imported")).strip() or "Imported"
    source_type = str(job.get("sourceType", "import")).strip() or "import"
    equity_status = str(job.get("equityStatus", "Unconfirmed")).strip() or "Unconfirmed"
    fit_note = str(job.get("fitNote", "")).strip()
    company_size_hint = str(job.get("companySizeHint", "")).strip()
    application_status = str(job.get("applicationStatus", "open")).strip() or "open"
    salary_band_fit = str(job.get("salaryBandFit", "overlap")).strip().lower()
    if salary_band_fit not in {"exact", "overlap"}:
        salary_band_fit = "overlap"

    company_shares_note = str(job.get("companySharesNote", "")).strip()
    if not company_shares_note:
        company_shares_note = (
            "Public company, public shares available"
            if company_status == "public"
            else "Private company, no public shares"
        )

    return {
        "id": str(job.get("id", "")).strip() or f"imported-job-{index}",
        "title": title,
        "company": company,
        "companyStatus": company_status,
        "companySizeHint": company_size_hint,
        "companySharesNote": company_shares_note,
        "location": location,
        "salary": salary,
        "salaryBandFit": salary_band_fit,
        "equityStatus": equity_status,
        "benefits": coerce_string_list(job.get("benefits")),
        "recruiterName": recruiter_name,
        "recruiterContact": recruiter_contact,
        "source": source,
        "sourceType": source_type,
        "link": link,
        "fitNote": fit_note,
        "isNewToday": bool(job.get("isNewToday", False)),
        "shownYesterday": bool(job.get("shownYesterday", False)),
        "seenBefore": bool(job.get("seenBefore", False)),
        "applicationStatus": application_status,
        "applied": bool(job.get("applied", False)),
        "notInterested": bool(job.get("notInterested", False)),
        "shortlisted": bool(job.get("shortlisted", False)),
    }


def ensure_state_shape(state: dict) -> dict:
    if "digestsByDate" not in state:
        return create_seed_state()

    state["schemaVersion"] = 2
    existing_sources = state.get("criteria", {}).get("sources", [])
    state["searchPreferences"] = normalize_search_preferences(
        state.get("searchPreferences"),
        {
            "roleName": state.get("searchPreferences", {}).get("roleName")
            or state.get("criteria", {}).get("roleName")
            or "Product Manager",
            "city": state.get("searchPreferences", {}).get("city") or "San Francisco",
            "state": state.get("searchPreferences", {}).get("state") or "CA",
            "compMin": coerce_int(state.get("searchPreferences", {}).get("compMin"), 190000),
            "compMax": coerce_int(state.get("searchPreferences", {}).get("compMax"), 220000),
            "resultLimit": coerce_int(state.get("searchPreferences", {}).get("resultLimit"), 50),
        },
    )
    state["criteria"] = search_preferences_to_criteria(state["searchPreferences"], existing_sources)

    for digest in state.get("digestsByDate", {}).values():
        normalized_jobs = []
        for index, job in enumerate(digest.get("jobs", []), start=1):
            normalized_jobs.append(normalize_job(job, index))
        digest["jobs"] = normalized_jobs
    return state


def merge_job_history(state: dict, date_value: str, jobs: list[dict]) -> list[dict]:
    previous_jobs = {}
    seen_any = set()
    shown_yesterday = set()
    for digest_date, digest in sorted(state.get("digestsByDate", {}).items()):
        if digest_date > date_value:
            continue
        for job in digest.get("jobs", []):
            key = job_key(job)
            previous_jobs[key] = job
            if digest_date < date_value:
                seen_any.add(key)
            if digest_date == yesterday_key_for(date_value):
                shown_yesterday.add(key)

    merged_jobs = []
    for job in jobs:
        key = job_key(job)
        previous = previous_jobs.get(key, {})
        job["applied"] = bool(previous.get("applied", job.get("applied", False)))
        job["notInterested"] = bool(previous.get("notInterested", job.get("notInterested", False)))
        job["shortlisted"] = bool(previous.get("shortlisted", job.get("shortlisted", False)))
        job["shownYesterday"] = key in shown_yesterday
        job["seenBefore"] = key in seen_any
        job["isNewToday"] = not job["shownYesterday"] and not job["seenBefore"]
        merged_jobs.append(job)
    return merged_jobs


def normalize_import_payload(payload: dict, state: dict | None = None) -> dict:
    state = state or create_seed_state()
    existing_sources = state.get("criteria", {}).get("sources", [])
    search_preferences = normalize_search_preferences(
        payload.get("searchPreferences"),
        state.get("searchPreferences") or default_search_preferences(),
    )
    criteria_payload = payload.get("criteria", {})
    if criteria_payload:
        if "location" in criteria_payload and "," in str(criteria_payload.get("location", "")):
            city, state_value = [part.strip() for part in str(criteria_payload["location"]).split(",", 1)]
            search_preferences["city"] = city or search_preferences["city"]
            search_preferences["state"] = state_value or search_preferences["state"]
        salary_string = str(criteria_payload.get("salary", "")).replace("$", "").replace(",", "")
        if "-" in salary_string:
            low, high = salary_string.split("-", 1)
            search_preferences["compMin"] = coerce_int(low, search_preferences["compMin"])
            search_preferences["compMax"] = coerce_int(high, search_preferences["compMax"])

    date_value = str(payload.get("date") or today_key()).strip() or today_key()
    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        raise ValueError("Jobs must be a list")

    normalized_jobs = []
    for index, job in enumerate(jobs, start=1):
        if not isinstance(job, dict):
            continue
        normalized_job = normalize_job(job, index)
        if (
            normalized_job["title"]
            and normalized_job["company"]
            and normalized_job["link"]
            and is_open_application_status(normalized_job["applicationStatus"])
        ):
            normalized_jobs.append(normalized_job)

    normalized_jobs = merge_job_history(state, date_value, normalized_jobs)
    summary = str(payload.get("summary", "")).strip() or (
        f"Up to {search_preferences['resultLimit']} {search_preferences['roleName']} roles in "
        f"{search_preferences['city']}, {search_preferences['state']}."
    )
    criteria_sources = coerce_string_list(criteria_payload.get("sources")) or existing_sources
    return {
        "date": date_value,
        "searchPreferences": search_preferences,
        "criteria": search_preferences_to_criteria(search_preferences, criteria_sources),
        "summary": summary,
        "jobs": normalized_jobs,
    }


def import_digest_payload(payload: dict) -> dict:
    state = load_state()
    normalized = normalize_import_payload(payload, state)
    state["searchPreferences"] = normalized["searchPreferences"]
    state["criteria"] = normalized["criteria"]
    state.setdefault("digestsByDate", {})[normalized["date"]] = {
        "generatedAt": utc_now_iso(),
        "summary": normalized["summary"],
        "jobs": normalized["jobs"],
    }
    state["lastUpdatedAt"] = utc_now_iso()
    save_state(state)
    return normalized


def resolve_data_dir() -> Path:
    candidates = []
    configured = os.getenv("BAY_PM_JOBS_DATA_DIR", os.getenv("NIGHTLY_TODOS_DATA_DIR"))
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.append(BASE_DIR / "data")
    candidates.append(Path(tempfile.gettempdir()) / "nightly-todos-data")

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write-test"
            probe.write_text("ok")
            probe.unlink()
            return candidate
        except OSError:
            continue
    raise RuntimeError("No writable data directory available")


DATA_DIR = resolve_data_dir()
STATE_PATH = DATA_DIR / "state.json"
REFRESH_STATUS = {
    "state": "idle",
    "message": "",
    "startedAt": None,
    "completedAt": None,
    "jobCount": 0,
    "date": None,
    "error": "",
}
REFRESH_LOCK = threading.Lock()


def load_json_file(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def merge_existing_flags(existing_jobs: list[dict], incoming_jobs: list[dict]) -> list[dict]:
    existing_by_id = {job.get("id"): job for job in existing_jobs if job.get("id")}
    merged_jobs = []
    for job in incoming_jobs:
        existing = existing_by_id.get(job.get("id"), {})
        merged = dict(job)
        merged["applied"] = bool(existing.get("applied", job.get("applied", False)))
        merged["notInterested"] = bool(existing.get("notInterested", job.get("notInterested", False)))
        merged["shortlisted"] = bool(existing.get("shortlisted", job.get("shortlisted", False)))
        merged_jobs.append(merged)
    return merged_jobs


def should_bootstrap_bundled_digest(state: dict, bundled_date: str, bundled_jobs: list[dict]) -> bool:
    current_dates = sorted(state.get("digestsByDate", {}))
    latest_current_date = current_dates[-1] if current_dates else ""
    if bundled_date > latest_current_date:
        return True

    current_digest = state.get("digestsByDate", {}).get(bundled_date, {})
    current_jobs = current_digest.get("jobs", [])
    current_role = (
        str(state.get("searchPreferences", {}).get("roleName", "")).strip().lower()
    )
    default_role = default_search_preferences()["roleName"].lower()

    looks_like_initial_seed = (
        latest_current_date == bundled_date
        and len(current_jobs) <= 6
        and current_role in {"", default_role}
    )
    return looks_like_initial_seed and len(bundled_jobs) > len(current_jobs)


def maybe_upgrade_from_bundled_digest(state: dict) -> dict:
    bundled_digest = load_json_file(BASE_DIR / "data" / "generated_digest.json")
    if not bundled_digest:
        return state

    bundled_date = str(bundled_digest.get("date", "")).strip()
    bundled_jobs = bundled_digest.get("jobs", [])
    if not bundled_date or not bundled_jobs:
        return state

    current_digest = state.get("digestsByDate", {}).get(bundled_date, {})
    current_jobs = current_digest.get("jobs", [])

    if not should_bootstrap_bundled_digest(state, bundled_date, bundled_jobs):
        return state

    state["searchPreferences"] = normalize_search_preferences(
        bundled_digest.get("searchPreferences"),
        state.get("searchPreferences"),
    )
    state["criteria"] = bundled_digest.get("criteria", state.get("criteria"))
    state.setdefault("digestsByDate", {})[bundled_date] = {
        "generatedAt": bundled_digest.get("generatedAt", utc_now_iso()),
        "summary": bundled_digest.get("summary", current_digest.get("summary", "")),
        "jobs": merge_existing_flags(current_jobs, bundled_jobs),
    }
    state["lastUpdatedAt"] = utc_now_iso()
    save_state(state)
    return state


def load_state() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_PATH.exists():
        state = create_seed_state()
        save_state(state)
    else:
        try:
            state = json.loads(STATE_PATH.read_text())
        except json.JSONDecodeError:
            state = create_seed_state()
            save_state(state)

    if not isinstance(state, dict):
        state = create_seed_state()
        save_state(state)

    state = ensure_state_shape(state)
    state = maybe_upgrade_from_bundled_digest(state)
    if today_key() not in state.get("digestsByDate", {}):
        state["digestsByDate"][today_key()] = {
            "generatedAt": utc_now_iso(),
            "summary": f"No new digest imported yet for {today_key()}.",
            "jobs": [],
        }
        state["lastUpdatedAt"] = utc_now_iso()
        save_state(state)
    return state


def save_state(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


class AppHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/api/state":
            self.send_json(load_state())
            return
        if self.path == "/api/refresh-status":
            self.send_json(get_refresh_status())
            return
        if self.path == "/api/source-health":
            self.send_json(get_source_health())
            return
        super().do_GET()

    def do_PATCH(self) -> None:
        if self.path.startswith("/api/jobs/"):
            self.handle_update_job()
            return
        if self.path == "/api/search-preferences":
            self.handle_update_search_preferences()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path == "/api/import-digest":
            self.handle_import_digest()
            return
        if self.path == "/api/refresh-digest":
            self.handle_refresh_digest()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def handle_import_digest(self) -> None:
        payload = self.read_json()
        try:
            normalized = import_digest_payload(payload)
        except ValueError as error:
            self.send_error(HTTPStatus.BAD_REQUEST, str(error))
            return
        self.send_json({"ok": True, "date": normalized["date"], "jobCount": len(normalized["jobs"])})

    def handle_update_search_preferences(self) -> None:
        payload = self.read_json()
        state = load_state()
        state["searchPreferences"] = normalize_search_preferences(payload, state.get("searchPreferences"))
        state["criteria"] = search_preferences_to_criteria(
            state["searchPreferences"],
            state.get("criteria", {}).get("sources", []),
        )
        state["lastUpdatedAt"] = utc_now_iso()
        save_state(state)
        self.send_json({"ok": True, "searchPreferences": state["searchPreferences"]})

    def handle_refresh_digest(self) -> None:
        queued = queue_refresh_job("Refreshing live job sources...")
        self.send_json(
            {"ok": True, "queued": queued, "status": get_refresh_status()},
            status=HTTPStatus.ACCEPTED if queued else HTTPStatus.OK,
        )

    def handle_update_job(self) -> None:
        date_value, job_id = self.parse_job_path(require_job_id=True)
        payload = self.read_json()
        state = load_state()
        digest = state.setdefault("digestsByDate", {}).get(date_value)
        if not digest:
            self.send_error(HTTPStatus.NOT_FOUND, "Digest not found")
            return

        for job in digest.get("jobs", []):
            if job["id"] != job_id:
                continue
            if "shortlisted" in payload:
                job["shortlisted"] = bool(payload["shortlisted"])
            if "applied" in payload:
                job["applied"] = bool(payload["applied"])
                if job["applied"]:
                    job["notInterested"] = False
            if "notInterested" in payload:
                job["notInterested"] = bool(payload["notInterested"])
                if job["notInterested"]:
                    job["applied"] = False
                    job["shortlisted"] = False
            state["lastUpdatedAt"] = utc_now_iso()
            save_state(state)
            self.send_json({"ok": True})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Job not found")

    def parse_job_path(self, require_job_id: bool) -> Tuple[str, Optional[str]]:
        pieces = [unquote(piece) for piece in self.path.split("/") if piece]
        if len(pieces) < 3:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid job path")
            raise ValueError("invalid job path")
        date_value = pieces[2]
        task_id = pieces[3] if len(pieces) > 3 else None
        if require_job_id and not task_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing job id")
            raise ValueError("missing job id")
        return date_value, task_id

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def translate_path(self, path: str) -> str:
        candidate = super().translate_path(path)
        return str(BASE_DIR / Path(candidate).name) if path != "/" else str(BASE_DIR / "index.html")


def run_server() -> None:
    ensure_auto_refresh_started()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Serving Bay PM Jobs on http://{HOST}:{PORT}")
    server.serve_forever()


def get_refresh_status() -> dict:
    with REFRESH_LOCK:
        return dict(REFRESH_STATUS)


def get_source_health() -> dict:
    if not REFRESH_REPORT_PATH.exists():
        return {"ok": False, "sources": {}, "updatedAt": None}
    try:
        payload = json.loads(REFRESH_REPORT_PATH.read_text())
    except json.JSONDecodeError:
        return {"ok": False, "sources": {}, "updatedAt": None}

    summary = {}
    for scope in ("previewFetch", "fetch"):
        for source_name, source_info in payload.get(scope, {}).items():
            entry = summary.setdefault(
                source_name,
                {"status": "unknown", "fetched": 0, "matched": 0, "error": "", "previewFetched": 0},
            )
            if scope == "previewFetch":
                entry["previewFetched"] = source_info.get("fetched", 0)
            else:
                entry["status"] = source_info.get("status", "unknown")
                entry["fetched"] = source_info.get("fetched", 0)
                entry["error"] = source_info.get("error", "")
    for source_name, source_info in payload.get("analysis", {}).get("sources", {}).items():
        entry = summary.setdefault(
            source_name,
            {"status": "unknown", "fetched": 0, "matched": 0, "error": "", "previewFetched": 0},
        )
        entry["matched"] = int(source_info.get("strict_kept", 0)) + int(source_info.get("fallback_kept", 0))
    return {
        "ok": True,
        "updatedAt": payload.get("generatedAt") or get_refresh_status().get("completedAt"),
        "sources": summary,
        "criteria": payload.get("criteria", {}),
    }


def queue_refresh_job(message: str) -> bool:
    with REFRESH_LOCK:
        if REFRESH_STATUS["state"] == "running":
            return False
        REFRESH_STATUS.update(
            {
                "state": "running",
                "message": message,
                "startedAt": utc_now_iso(),
                "completedAt": None,
                "jobCount": 0,
                "date": None,
                "error": "",
            }
        )
    threading.Thread(target=run_refresh_job, daemon=True).start()
    return True


def is_refresh_stale() -> bool:
    status = get_refresh_status()
    completed_at = status.get("completedAt")
    if not completed_at:
        return True
    try:
        completed = datetime.fromisoformat(completed_at)
    except ValueError:
        return True
    return (datetime.now().astimezone() - completed).total_seconds() >= AUTO_REFRESH_MINUTES * 60


def auto_refresh_loop() -> None:
    if is_refresh_stale():
        queue_refresh_job("Refreshing live job sources on startup...")
    while True:
        threading.Event().wait(AUTO_REFRESH_MINUTES * 60)
        if is_refresh_stale():
            queue_refresh_job("Scheduled refresh is running...")


def ensure_auto_refresh_started() -> None:
    threading.Thread(target=auto_refresh_loop, daemon=True).start()


def run_refresh_job() -> None:
    try:
        import refresh_jobs
        refresh_jobs.require_refresh_dependencies()
        criteria, sources = refresh_jobs.load_source_catalog()
        preview_source_list = refresh_jobs.preview_sources(sources)
        preview_jobs_by_source, preview_source_report = refresh_jobs.fetch_all_jobs(
            criteria,
            preview_source_list,
            use_cache=True,
            max_workers=refresh_jobs.PREVIEW_MAX_WORKERS,
        )
        preview_digest, preview_diagnostics = refresh_jobs.build_digest(
            preview_jobs_by_source,
            criteria,
            preview_source_list,
        )
        if preview_digest.get("jobs"):
            import_digest_payload(preview_digest)
            with REFRESH_LOCK:
                REFRESH_STATUS.update(
                    {
                        "state": "running",
                        "message": "Preview loaded. Enriching more sources...",
                        "jobCount": len(preview_digest["jobs"]),
                        "date": preview_digest["date"],
                        "error": "",
                    }
                )

        jobs_by_source, source_report = refresh_jobs.fetch_all_jobs(
            criteria,
            sources,
            use_cache=True,
            max_workers=refresh_jobs.FULL_MAX_WORKERS,
        )
        digest, diagnostics = refresh_jobs.build_digest(jobs_by_source, criteria, sources)
        refresh_jobs.GENERATED_DIGEST_PATH.write_text(json.dumps(digest, indent=2))
        refresh_jobs.GENERATED_REPORT_PATH.write_text(
            json.dumps(
                {
                    "generatedAt": utc_now_iso(),
                    "criteria": {
                        "roleName": criteria.role_name,
                        "city": criteria.city,
                        "state": criteria.state,
                        "salaryMin": criteria.salary_min,
                        "salaryMax": criteria.salary_max,
                        "resultLimit": criteria.max_jobs_per_day,
                    },
                    "previewFetch": preview_source_report,
                    "fetch": source_report,
                    "previewAnalysis": preview_diagnostics,
                    "analysis": diagnostics,
                },
                indent=2,
            )
        )
        import_digest_payload(digest)
        with REFRESH_LOCK:
            REFRESH_STATUS.update(
                {
                    "state": "completed",
                    "message": "Refresh complete.",
                    "completedAt": utc_now_iso(),
                    "jobCount": len(digest["jobs"]),
                    "date": digest["date"],
                    "error": "",
                }
            )
    except Exception as error:
        with REFRESH_LOCK:
            REFRESH_STATUS.update(
                {
                    "state": "failed",
                    "message": "Refresh failed.",
                    "completedAt": utc_now_iso(),
                    "error": str(error),
                }
            )


if __name__ == "__main__":
    run_server()
