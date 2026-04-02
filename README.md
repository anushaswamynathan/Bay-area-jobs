# Bay PM Jobs

A lightweight local web app for reviewing a daily Bay Area product manager job digest.

Current app behavior:

- shows a seeded daily digest for Bay Area PM roles
- ranks public companies ahead of private companies and startups
- captures salary, equity, benefits, recruiter details, source, and fit notes
- lets you shortlist roles in the UI
- keeps the digest grouped by day in a calendar view
- accepts imported live digests through the UI or a small CLI importer

## Run locally

```bash
python3 server.py
```

Then open [http://127.0.0.1:4174](http://127.0.0.1:4174)

## Data model

- app state is stored in [data/state.json](/Users/anusha/Documents/Playground/data/state.json)
- the server seeds a sample digest automatically if no digest data exists yet
- shortlist actions persist back into the same local state file
- imported digests replace or create a digest for the specified date
- imported digests automatically filter out jobs that are closed or no longer accepting applications

## Files

- [server.py](/Users/anusha/Documents/Playground/server.py) serves the app and stores digest state
- [index.html](/Users/anusha/Documents/Playground/index.html) defines the dashboard layout
- [app.js](/Users/anusha/Documents/Playground/app.js) renders jobs, filters, and shortlist state
- [styles.css](/Users/anusha/Documents/Playground/styles.css) contains the visual system
- [import_digest.py](/Users/anusha/Documents/Playground/import_digest.py) imports a JSON digest into app state
- [data/sample_digest.json](/Users/anusha/Documents/Playground/data/sample_digest.json) is a starter payload you can copy from

## Import a live digest

From the UI:

- open the app
- click `Import daily digest`
- paste a JSON payload and save it

From the terminal:

```bash
python3 import_digest.py data/sample_digest.json
```

Or pipe JSON in directly:

```bash
cat payload.json | python3 import_digest.py
```

Required per job:

- `title`
- `company`
- `link`

Useful optional fields:

- `applicationStatus`
- `companyStatus`
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

## Automation hook

The cleanest recurring setup is a Codex automation that:

- searches live Bay Area PM roles each morning
- builds a JSON digest in the schema above
- excludes jobs that are closed, expired, filled, inactive, or no longer accepting applications
- runs `python3 import_digest.py /path/to/generated-payload.json`

That keeps the app simple while making the daily refresh fully automatable.

## Open quickly

You can also run:

```bash
./open_bay_pm_jobs.command
```
