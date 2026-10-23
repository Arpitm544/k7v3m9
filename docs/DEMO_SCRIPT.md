# Wind Desk video outline

Record one unlisted YouTube video under 10 minutes. Target about 9 minutes. The first section presents the pilot to the customer; the second explains the implementation to a technical lead. Rehearse with the deployed application and review all claims before recording.

## Customer presentation about four minutes

### 0:00 to 0:35 Explain the decision

Open the Decision overview. Explain: “Your team needs a view of tomorrow's wind generation before making day-ahead purchases. Wind Desk reconstructs the forecast available at that decision time and shows how similar decisions performed during this historical pilot.”

State that this covers national wind data, not the utility's own demand or portfolio. The app does not calculate how much energy the utility must purchase.

### 0:35 to 1:35 Show a historical decision

Select 15 January 2026, cutoff 09:00. Point out delivery on 16 January. The default cutoff is a configurable pilot assumption, not an official market deadline.

Show the 7.93 GW average forecast, 190.3 GWh forecast energy, all 24 hours available, and the 07:30 publication. Explain: “These values only use publications available by the selected cutoff. A later revision cannot rewrite what the buyer knew.”

Inspect hourly data or hover over the chart to expose publication timestamps.

### 1:35 to 2:15 Reveal the outcome

Enable Compare actuals. Explain that actuals were observed afterward. The day has about 783 MW MAE and +352 MW bias at this cutoff. Positive error means wind was overpredicted. Each hourly actual averages two observed half-hours; forecasts were natively hourly in the downloaded data.

### 2:15 to 3:25 Explain the historical results

Open Forecast accuracy. At 09:00, the full January decision window has 744 matched hours, MAE about 2,039 MW, RMSE about 2,505 MW, and bias about +1,748 MW.

Explain MAE in plain language as average absolute miss size. Explain that RMSE gives larger misses more weight. Explain that these describe differences between the assigned datasets under the stated alignment assumptions, rather than proving all differences are pure forecast error.

Use the daily table to open 27 January: delivery on 28 January had the largest daily MAE, about 5,375 MW. Show how the chart supports this finding. Do not claim an example chosen before computation was representative of every day.

### 3:25 to 4:00 State the value and limits

Explain that the pilot makes available forecasts and historical forecast risk transparent. Overprediction can increase replacement power needs, but purchase quantities and costs require demand and price inputs that are outside the assignment. Month-wide accuracy is retrospective and is not presented as information known earlier in the month.

## Technical review about five minutes

### 4:00 to 4:50 Architecture

Show the repository directory map and explain the flow: public Elexon APIs → offline downloader → compressed snapshot plus provenance → FastAPI services → React charts.

Explain the fixed-file choice: one historical month does not need a database or live upstream requests. Explain how Docker provides local frontend/backend orchestration and how the Vercel deployment uses native Python and static frontend runtimes.

### 4:50 to 5:55 Correct selection and time semantics

Open `backend/app/analytics.py`. Show normalization to aware UTC, Europe/London cutoff construction, the next delivery day, and binary search for the latest publication no later than the cutoff. Show a unit test proving a later revision is excluded and an exactly-on-cutoff revision is included.

Explain that January decision dates imply deliveries through 1 February, and that the ingestion includes earlier forecast publications to support the first decision.

### 5:55 to 6:50 Accuracy and missing data

Show the hourly alignment, requirement for both actual half-hours, `forecast - actual` convention, and the pure metric function. Explain that missing values remain null and coverage has an explicit denominator. Month-wide metrics are computed from intervals, not an average of daily RMSEs.

Explain that a zero is a valid value, whereas a missing value is not silently changed to zero.

### 6:50 to 7:40 API and frontend

Open the API docs. Show date/cutoff validation and metadata. In the frontend, show aborted stale requests, loading/error states, the retrospective toggle, inspectable tables, and CSV export. Explain how the two independent deployment origins are configured and why local requests use a proxy.

### 7:40 to 8:30 Verification and reproducibility

Run `pytest` and the independent snapshot check. Show manifest source URLs, download time, record counts, and checksum. Explain duplicate conflict failure, bounded upstream retries, and the absence of generated business data.

If Docker containers have actually been verified by recording time, show the running app from Docker. Otherwise state that configuration was validated but the runtime still needs verification; do not describe it as tested.

### 8:30 to 9:00 Tradeoffs and handover

State the hourly alignment and configurable deadline assumptions. Mention dataset coverage/measurement comparability and that actuals are latest available outturns. Explain the small scope and absence of a calibrated uncertainty model. Acknowledge AI assistance as disclosed in the README. Finish with the run commands and deployed URL.

## Recording checklist

- Use the final deployed app when available and readable browser zoom.
- Hide private tabs, credentials, account identifiers, terminal history, and notifications.
- Show actual behavior; do not substitute slides for the working dashboard.
- Keep customer and technical sections individually below five minutes.
- Verify all quoted numbers at 09:00 before recording.
- Upload as unlisted and test the watch URL without signing in.
- Add the verified watch URL to README and the submission form.
