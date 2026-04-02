#!/usr/bin/env python3

import json
import os
import tempfile
from datetime import date, datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import unquote

BASE_DIR = Path(__file__).resolve().parent
HOST = os.getenv("BAY_PM_JOBS_HOST", os.getenv("NIGHTLY_TODOS_HOST", "127.0.0.1"))
PORT = int(os.getenv("PORT", os.getenv("BAY_PM_JOBS_PORT", "4174")))


def utc_now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def today_key() -> str:
    return date.today().isoformat()


def create_seed_state() -> dict:
    initial_jobs = [
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
            "benefits": [
                "Equity award eligibility",
                "Bonus eligibility",
                "Comprehensive benefits package",
            ],
            "recruiterName": "",
            "recruiterContact": "",
            "source": "Company career page",
            "sourceType": "company",
            "link": "https://www.uber.com/global/en/careers/list/145353/",
            "fitNote": "Large public company with fintech-adjacent product scope and strong compensation fit.",
            "isNewToday": True,
            "applied": False,
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
            "benefits": [
                "Equity award eligibility",
                "Bonus eligibility",
                "401(k)",
            ],
            "recruiterName": "",
            "recruiterContact": "",
            "source": "Company career page",
            "sourceType": "company",
            "link": "https://www.uber.com/careers/list/154261",
            "fitNote": "Strong marketplace role at a public company with direct salary-band alignment.",
            "isNewToday": False,
            "applied": False,
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
            "benefits": [
                "Equity",
                "Bonus",
                "Location-based benefits",
            ],
            "recruiterName": "",
            "recruiterContact": "",
            "source": "Ashby",
            "sourceType": "job-board",
            "link": "https://jobs.ashbyhq.com/airwallex/426c17cb-4343-435d-a03e-c0b4e20b9109",
            "fitNote": "Excellent fintech relevance with compensation that overlaps the target band.",
            "isNewToday": True,
            "applied": False,
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
            "benefits": [
                "Medical, dental, vision",
                "401(k) match",
                "Paid parental leave",
            ],
            "recruiterName": "Marina Kostioutchenko, CFA",
            "recruiterContact": "https://www.linkedin.com/jobs/view/senior-staff-product-manager-at-altruist-4371342447",
            "source": "LinkedIn",
            "sourceType": "linkedin",
            "link": "https://www.linkedin.com/jobs/view/senior-staff-product-manager-at-altruist-4371342447",
            "fitNote": "High-quality fintech comp package, though the top end exceeds the preferred range.",
            "isNewToday": False,
            "applied": False,
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
            "benefits": [
                "Startup equity",
                "Health, dental, vision",
                "Flexible PTO",
                "Commuter benefits",
            ],
            "recruiterName": "",
            "recruiterContact": "",
            "source": "Ashby",
            "sourceType": "job-board",
            "link": "https://jobs.ashbyhq.com/traba/b00513c3-56b8-4828-929c-2fe9f227b094",
            "fitNote": "Best marketplace startup fit in the current sample set.",
            "isNewToday": True,
            "applied": False,
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
            "benefits": [
                "Equity",
                "Bonus",
                "Location-based benefits",
            ],
            "recruiterName": "",
            "recruiterContact": "",
            "source": "Ashby",
            "sourceType": "job-board",
            "link": "https://jobs.ashbyhq.com/airwallex/458c1e45-697f-4770-8d0f-ab1d528b3baa",
            "fitNote": "Strong private fintech option with a broad growth charter.",
            "isNewToday": False,
            "applied": False,
            "shortlisted": False,
        },
    ]

    return {
        "schemaVersion": 1,
        "criteria": {
            "location": "San Francisco Bay Area",
            "salary": "$190,000-$220,000",
            "industries": ["Fintech", "Marketplaces"],
            "sources": ["Company career pages", "LinkedIn", "Reputable job boards"],
            "ranking": "Public companies first, then private/startups",
        },
        "digestsByDate": {
            today_key(): {
                "generatedAt": utc_now_iso(),
                "summary": "Public companies are ranked first, followed by high-signal private companies and startups.",
                "jobs": initial_jobs,
            }
        },
        "lastUpdatedAt": utc_now_iso(),
    }


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
        "applicationStatus": application_status,
        "applied": bool(job.get("applied", False)),
        "shortlisted": bool(job.get("shortlisted", False)),
    }


def normalize_import_payload(payload: dict) -> dict:
    criteria = payload.get("criteria", {})
    date_value = str(payload.get("date") or today_key()).strip() or today_key()
    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("At least one job is required")

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

    if not normalized_jobs:
        raise ValueError("No valid jobs were provided")

    return {
        "date": date_value,
        "criteria": {
            "location": str(criteria.get("location", "San Francisco Bay Area")).strip()
            or "San Francisco Bay Area",
            "salary": str(criteria.get("salary", "$190,000-$220,000")).strip()
            or "$190,000-$220,000",
            "industries": coerce_string_list(criteria.get("industries"))
            or ["Fintech", "Marketplaces"],
            "sources": coerce_string_list(criteria.get("sources"))
            or ["Company career pages", "LinkedIn", "Reputable job boards"],
            "ranking": str(
                criteria.get("ranking", "Public companies first, then private/startups")
            ).strip()
            or "Public companies first, then private/startups",
        },
        "summary": str(payload.get("summary", "")).strip()
        or "Imported digest with public companies ranked ahead of private companies and startups.",
        "jobs": normalized_jobs,
    }


def resolve_data_dir() -> Path:
    candidates = []
    configured = os.getenv("NIGHTLY_TODOS_DATA_DIR")
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


def load_state() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STATE_PATH.exists():
        state = create_seed_state()
        save_state(state)
        return state

    try:
        state = json.loads(STATE_PATH.read_text())
    except json.JSONDecodeError:
        state = create_seed_state()
        save_state(state)
        return state

    if "digestsByDate" not in state:
        state = create_seed_state()
        save_state(state)
        return state

    digests = state.setdefault("digestsByDate", {})
    if today_key() not in digests:
        seed = create_seed_state()
        digests[today_key()] = seed["digestsByDate"][today_key()]
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
        super().do_GET()

    def do_PATCH(self) -> None:
        if self.path.startswith("/api/jobs/"):
            self.handle_update_job()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path == "/api/import-digest":
            self.handle_import_digest()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def handle_import_digest(self) -> None:
        payload = self.read_json()
        try:
            normalized = normalize_import_payload(payload)
        except ValueError as error:
            self.send_error(HTTPStatus.BAD_REQUEST, str(error))
            return

        state = load_state()
        state["criteria"] = normalized["criteria"]
        state.setdefault("digestsByDate", {})[normalized["date"]] = {
            "generatedAt": utc_now_iso(),
            "summary": normalized["summary"],
            "jobs": normalized["jobs"],
        }
        state["lastUpdatedAt"] = utc_now_iso()
        save_state(state)
        self.send_json({"ok": True, "date": normalized["date"], "jobCount": len(normalized["jobs"])})

    def handle_update_job(self) -> None:
        date_value, job_id = self.parse_job_path(require_job_id=True)
        payload = self.read_json()
        state = load_state()
        digest = state.setdefault("digestsByDate", {}).get(date_value)
        if not digest:
            self.send_error(HTTPStatus.NOT_FOUND, "Digest not found")
            return

        for job in digest.get("jobs", []):
            if job["id"] == job_id:
                if "shortlisted" in payload:
                    job["shortlisted"] = bool(payload["shortlisted"])
                if "applied" in payload:
                    job["applied"] = bool(payload["applied"])
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
        job_id = pieces[3] if len(pieces) > 3 else None
        if require_job_id and not job_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing job id")
            raise ValueError("missing job id")
        return date_value, job_id

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
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Serving Bay PM Jobs on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
