# Bay PM Jobs

A lightweight web app and refresh pipeline for a daily San Francisco Bay Area product manager job digest.

Current app behavior:

- shows a daily digest ranked with public companies first, then private companies and startups
- captures salary, equity, benefits, recruiter details, source, and fit notes
- lets you shortlist roles in the UI
- keeps digests grouped by day in a calendar view
- imports live digests through the UI, CLI, or automated refresh script
- filters out jobs that are closed or no longer accepting applications
- caps each daily digest at 50 jobs

## Run locally

Install dependencies:

```bash
pip3 install -r requirements.txt
```

Start the app:

```bash
python3 server.py
```

Then open [http://127.0.0.1:4174](http://127.0.0.1:4174)

Quick launcher:

```bash
./open_bay_pm_jobs.command
```

## Refresh jobs from live sources

Run:

```bash
python3 refresh_jobs.py
```

That will:

- fetch configured sources
- normalize and dedupe jobs
- filter for Bay Area PM roles with salary overlap in the `$190k-$220k` band
- exclude closed roles
- write a digest to [data/generated_digest.json](/Users/anusha/Documents/Playground/bay-pm-jobs/data/generated_digest.json)
- import the digest into [data/state.json](/Users/anusha/Documents/Playground/bay-pm-jobs/data/state.json) for the app

## Sources

Configured source catalog:

- [data/source_catalog.json](/Users/anusha/Documents/Playground/bay-pm-jobs/data/source_catalog.json)

Current source types:

- `greenhouse`: public Greenhouse board API
- `lever`: public Lever postings API
- `html_search`: best-effort HTML search/listing adapters for LinkedIn, Indeed, Glassdoor, and major company career sites

Default configured sources include:

- LinkedIn
- Indeed
- Glassdoor
- Uber careers
- Walmart careers
- Google careers
- Apple jobs
- placeholder Greenhouse and Lever sources you can enable by filling in board/site values

## Important notes

- Greenhouse and Lever are the most reliable sources in this setup.
- LinkedIn, Indeed, Glassdoor, and many company career sites do not offer simple public job APIs for this use case, so this app uses best-effort HTML parsing there.
- HTML source structures can change and may need maintenance.
- Some sites may rate-limit or block automated requests.

## Data model

- app state is stored in [data/state.json](/Users/anusha/Documents/Playground/bay-pm-jobs/data/state.json)
- source configuration is stored in [data/source_catalog.json](/Users/anusha/Documents/Playground/bay-pm-jobs/data/source_catalog.json)
- a sample digest payload lives at [data/sample_digest.json](/Users/anusha/Documents/Playground/bay-pm-jobs/data/sample_digest.json)

Required per imported job:

- `title`
- `company`
- `link`

Useful optional fields:

- `applicationStatus`
- `companyStatus`
- `companySizeHint`
- `companySharesNote`
- `location`
- `salary`
- `equityStatus`
- `benefits`
- `recruiterName`
- `recruiterContact`
- `source`
- `sourceType`
- `fitNote`
- `salaryBandFit`
- `shortlisted`

## Files

- [server.py](/Users/anusha/Documents/Playground/bay-pm-jobs/server.py) serves the app and stores digest state
- [refresh_jobs.py](/Users/anusha/Documents/Playground/bay-pm-jobs/refresh_jobs.py) pulls jobs from configured live sources
- [import_digest.py](/Users/anusha/Documents/Playground/bay-pm-jobs/import_digest.py) imports a JSON digest into app state
- [index.html](/Users/anusha/Documents/Playground/bay-pm-jobs/index.html) defines the dashboard layout
- [app.js](/Users/anusha/Documents/Playground/bay-pm-jobs/app.js) renders jobs, filters, and shortlist state
- [styles.css](/Users/anusha/Documents/Playground/bay-pm-jobs/styles.css) contains the visual system
- [requirements.txt](/Users/anusha/Documents/Playground/bay-pm-jobs/requirements.txt) lists refresh dependencies

## Automation hook

The cleanest recurring setup is:

- install dependencies once
- run `python3 refresh_jobs.py` every morning
- let the app read the updated state file automatically

That keeps the UI simple while making the refresh path fully automatable.
