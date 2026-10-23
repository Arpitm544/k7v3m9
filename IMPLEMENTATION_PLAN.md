# REint wind forecast application implementation plan

Build a historical decision dashboard that answers two questions: what wind forecast was available when the buyer made a day-ahead decision, and how accurate was that forecast when compared with actual generation? Deliver a small, reliable React and Python application within the assignment's 16-hour limit, including deployment, documentation, and the required video.

This is a proposed implementation plan. Requirements below come from the supplied assignment; architecture, cutoff defaults, and interface choices are recommendations. No application has been implemented yet. The workspace was empty when inspected.

## 1. Required scope

- React frontend and Python backend.
- Elexon FUELHH actual generation, filtered to fuelType WIND.
- Elexon WINDFOR forecasts, retaining startTime, publishTime, and generation.
- National wind generation only, with data relevant to purchase decisions made in January 2026.
- Show the latest forecast available at the selected decision time and quantify forecast error.
- Use Docker and deploy the sample application to Vercel or Heroku.
- Public GitHub repository with an anonymous name.
- README covering directories, startup instructions, deployment URL, and explicit AI-tool disclosure if applicable.
- Unlisted YouTube video, maximum 10 minutes: customer presentation up to 5 minutes, technical review up to 5 minutes.
- Submission form with publicly accessible links, verified in incognito mode.

Do not add demand, prices, weather, solar, authentication, trade execution, or a machine learning model. The supplied datasets cannot determine the utility's required purchase volume or costs. Explain how wind overprediction can increase procurement exposure without pretending to calculate a complete purchasing recommendation.

## 2. Resolve the time semantics before building charts

### Decision dates and delivery dates

Interpret the specified month literally as decision dates from 1 January through 31 January 2026. Each decision applies to the following delivery day, giving delivery dates from 2 January through 1 February. Document this interpretation prominently. Keep the date mapping in a single function so it is easy to change if the evaluator intended January delivery dates instead.

Use Europe/London for user-facing dates and cutoff controls; store timezone-aware UTC timestamps internally. Fetch forecast publications far enough before the first decision to find an eligible forecast, extending the lookback if necessary. Fetch actuals through the final delivery day. January has 48 half-hour intervals per delivery day, so the expected total is 1,488 intervals across these 31 delivery days.

### Decision cutoff

The brief gives no auction venue or gate-closure time. Provide a configurable decision time, with 09:00 Europe/London as a clearly labeled demonstration assumption. Do not claim this is an official market deadline. The selected decision date plus cutoff forms the as-of timestamp.

For each target half-hour on the next delivery day:

1. Keep forecast records with the matching startTime and publishTime less than or equal to the as-of timestamp.
2. Choose the record with the greatest eligible publishTime.
3. If none exists, return an explicit missing forecast rather than zero or a later forecast.
4. Join the actual generation by the same normalized startTime for retrospective evaluation.

Retain publication timestamps in API responses and chart tooltips. Show the publication range and oldest forecast age if the selected half-hours use different publications. Investigate revision metadata during the data spike and define a deterministic duplicate/conflict rule rather than arbitrarily dropping differing records.

The decision view must distinguish forecast information available at the cutoff from actuals observed afterward. Put actuals behind a labeled retrospective comparison toggle. Month-wide accuracy is retrospective; do not present it as knowledge available to an early-January buyer. If a decision-time accuracy summary is added, use only outcomes demonstrably available before that cutoff; omit this feature if historical actual availability cannot be established.

## 3. Suggested architecture

Use React with TypeScript and Vite, Recharts for charts, and ordinary CSS or Tailwind for layout. Use FastAPI, Pydantic, httpx, and pytest on the backend. Keep analytics in pure Python functions; add pandas only if inspection shows it saves meaningful implementation time.

Data flow:

```text
Elexon FUELHH and WINDFOR
           |
offline download and normalization script
           |
versioned historical snapshot and provenance manifest
           |
FastAPI selection and accuracy services
           |
React decision and accuracy views
```

Download the historical data once rather than making Elexon requests on every page view. Preserve all forecast publication versions needed for selection. Serve normalized snapshots from read-only files bundled with the backend. A database, background worker, and scheduled refresh are unnecessary for this fixed historical month.

Use two Vercel projects if that makes setup simpler: one static React project and one Python FastAPI project. Configure a frontend API URL and an explicit backend CORS origin. Test this deployment arrangement during the first two hours. Vercel supports FastAPI as a Python function; keep ingestion outside request handlers. Docker provides a reproducible local runtime; Vercel deployment uses its native build/runtime rather than the Docker image.

Suggested structure:

```text
frontend/
  src/components/
  src/pages/
  src/lib/api.ts
  src/types.ts
  Dockerfile
backend/
  app/main.py
  app/models.py
  app/services/selection.py
  app/services/metrics.py
  app/repository.py
  data/
  tests/
  requirements.txt
  Dockerfile
scripts/
  fetch_data.py
docker-compose.yml
.env.example
README.md
```

## 4. Data pipeline

Start with a small request to each assigned dataset endpoint. Verify request parameter names, response envelope, units, publication history, interval coverage, and whether date filters act on publication time or target time. The documentation pages require JavaScript and direct sample API responses were not available through the research tool; these details still need runtime verification.

Then implement the downloader:

- Request bounded chunks according to verified endpoint limits; use timeouts and bounded retries for transient errors.
- Preserve raw responses outside the deployed frontend and normalize the fields used by the app.
- Filter actuals to WIND even if server-side filtering is available.
- Preserve all distinct forecast publications; never collapse to today's latest forecast during ingestion.
- Normalize timestamps, sort records, remove exact duplicates, and flag conflicting duplicates for inspection.
- Validate numeric values and units. Flag suspicious records rather than silently replacing them.
- Report expected, present, missing, duplicate, and conflicting intervals.
- Save a manifest with source URLs, request ranges, download timestamp, row counts, and a checksum or snapshot version.
- Use half-open target ranges internally to avoid double-counting chunk boundaries.

Use these logical records:

```text
actual:   start_time, generation_mw, available revision metadata
forecast: start_time, publish_time, generation_mw, available revision metadata
selected: start_time, publish_time, forecast_mw, actual_mw, error_mw, status
```

Derive lead time and forecast age rather than storing redundant values. Keep missing values null throughout the API and charts.

## 5. User interface

### Decision view

Provide decision-date and decision-time controls, with the derived delivery date directly underneath. Default to one verified, fully populated example day.

- Summary: forecast average MW, forecast energy MWh, available intervals out of 48, and forecast freshness.
- Main chart: next-day half-hourly forecast; optional retrospective actual overlay.
- Tooltip: target time, forecast MW, publication time, and actual/error only in retrospective mode.
- Clear gaps for missing intervals, with a visible incomplete-data notice.
- Brief explanation that lower actual wind than forecast can increase the need for replacement procurement.

### Accuracy view

Apply the same cutoff policy to every decision date in the selected January range. Show MAE, RMSE, bias, matched interval count, coverage, daily errors, and forecast-versus-actual comparison. Keep units and sign conventions visible. Include concise explanatory text beside metrics.

Do not add an inferred confidence band to the forecast in the MVP. It would require a defensible calibration method and creates an unnecessary risk of using future observations.

Both views need loading, API failure, empty-result, and partial-data states. Ensure readable chart axes, keyboard-operable controls, consistent colors, and a usable narrow-screen layout.

## 6. Accuracy definitions

For every interval with both an eligible forecast F and actual A, define error e = F - A, measured in MW.

- MAE = mean(abs(e)): typical absolute error.
- RMSE = sqrt(mean(e squared)): gives larger misses more weight.
- Bias = mean(e): positive means wind was overforecast; negative means it was underforecast.
- Coverage = matched intervals / expected intervals, alongside separate forecast and actual availability counts.
- Interval energy = generation in MW multiplied by 0.5 hours, giving MWh.

Compute range-wide metrics from matched intervals directly. Do not average daily RMSE values or give incomplete days equal weight by accident. Return null metrics when no pairs exist. Label energy totals as partial when intervals are missing. Avoid MAPE because actual generation close to zero can make it misleading.

Example for explaining the sign: forecast 10,000 MW and actual 9,000 MW means a positive 1,000 MW error and a wind shortfall of 500 MWh over that half hour. This is an illustrative calculation, not a result from the downloaded data.

## 7. Minimal API

```text
GET /api/health
GET /api/metadata
GET /api/decision?date=2026-01-15&cutoff=09:00
GET /api/accuracy?from=2026-01-01&to=2026-01-31&cutoff=09:00
```

Metadata should expose supported decision dates, time zone, units, snapshot provenance, and data-quality counts. Decision responses should expose the derived delivery date, as-of timestamp, interval data, publication metadata, and completeness. Accuracy responses should expose the selection policy, metric definitions, sample counts, daily summaries, and aggregate metrics. Validate dates and cutoff values; reject unsupported ranges with helpful errors. Make clear whether date ranges are inclusive.

## 8. Sixteen-hour execution budget

| Time | Work | Completion checkpoint |
|---|---|---|
| 0–1.5 h | Inspect both APIs, verify data semantics, scaffold repository | Real sample data and written date/cutoff assumptions |
| 1.5–2 h | Deploy minimal React and Python health endpoint | Hosted frontend can reach hosted backend |
| 2–4 h | Download and normalize full historical snapshot | Manifest and coverage report generated |
| 4–6.5 h | Implement selection, metrics, validation, and core tests | Correct API results for a verified example day |
| 6.5–9.5 h | Build decision and accuracy views | Complete browser flow using real API data |
| 9.5–11 h | Add missing/error states and polish | Readable, explainable dashboard |
| 11–12.5 h | Docker, integration checks, production redeploy | Local container flow and deployed flow both work |
| 12.5–13.5 h | README and evidence-backed findings | Reviewer can run and understand the project |
| 13.5–15 h | Rehearse, record, and upload video | Unlisted video under 10 minutes |
| 15–16 h | Incognito checks, submission preparation, contingency | All required links accessible and ready |

At hour 9, cut optional features if the main flow is unfinished. Drop CSV export, forecast-revision exploration, and additional charts before cutting tests of time selection, documentation, deployment, or video preparation. Stop at the assignment's 16-hour ceiling and document any limitations.

## 9. Verification checklist

- A forecast published after the cutoff is never selected.
- A forecast exactly at the cutoff is eligible under the documented inclusive policy.
- Different forecast revisions choose the latest eligible publication for each target interval.
- Missing eligible forecasts and missing actuals stay missing and reduce coverage.
- Duplicate handling does not multiply joined rows or bias metrics.
- Hand-calculated examples validate MAE, RMSE, bias, and MW-to-MWh conversion.
- Empty matched sets produce null metrics rather than division errors.
- Decision date 31 January maps to delivery date 1 February; the first decision maps correctly too.
- UTC and Europe/London values represent the same selected instant.
- API rejects dates outside the configured decision range and malformed cutoff values.
- API errors produce a usable frontend state.
- A real browser smoke check covers both views and their controls.
- Docker starts the application from documented commands.
- The production frontend reaches the production Python API, including after a fresh load.
- README links, public repository, deployed site, and unlisted video open without account access.

Use small synthetic fixtures for deterministic backend tests and a separate smoke check against the historical snapshot. Do not make unit tests depend on Elexon's availability.

## 10. Presentation and handover

Aim for a 9-minute video to leave margin under the limit.

Customer section, about 4 minutes: explain the buying decision, select a historical decision time, show the eligible forecast, reveal the eventual actuals, explain error magnitude and bias, and finish with two or three findings measured from the real dataset. Avoid claims about savings or optimal purchases without supporting inputs.

Technical section, about 5 minutes: explain the data pipeline and architecture, walk through the as-of selection rule and tests, explain the metrics and missing-data policy, show API boundaries and Docker startup, and describe deployment, tradeoffs, AI assistance, and next steps.

README should contain the product purpose, screenshots, deployed URL, video link, directory map, exact local and Docker commands, environment variables, data-download command, source attribution, data semantics, cutoff assumption, formulas, tests, limitations, and AI disclosure. Use an anonymous repository name and check for secrets and unnecessary personal identifiers before publishing.

Keep publication and submission as separate final actions after the app and video are ready for review. This planning request does not itself authorize creating a public repository, publishing a deployment, uploading a video, or submitting the form.

## References

- Assignment source: `REint Full Stack SWE challenge v4 Shared.docx`.
- Assigned actuals documentation: https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream
- Assigned forecast documentation: https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream
- Elexon API developer portal: https://developer.data.elexon.co.uk/
- Vercel FastAPI documentation: https://vercel.com/docs/frameworks/backend/fastapi
- Vercel Python runtime documentation: https://vercel.com/docs/functions/runtimes/python
