# Source organization

The existing implementation is organized into six cumulative feature branches. Each branch includes the previous branch and adds one logical part. These commits organize the completed code for review; they do not represent the original development timeline. Commit dates are the actual dates the commits were created.

| Branch | Adds | Depends on |
|---|---|---|
| `feature/project-setup` | Ignore rules, environment example, dependency locks, React/Vite configuration, Python package scaffolding | Initial commit |
| `feature/elexon-data` | Reproducible downloader, public historical snapshot, provenance manifest | Project setup |
| `feature/forecast-analytics` | As-of forecast selection, metrics, FastAPI endpoints, Vercel entrypoint | Elexon data |
| `feature/dashboard-ui` | Overview, accuracy and methodology views, responsive styles, screenshot | Forecast analytics |
| `test/validation` | Analytics and API tests, independent snapshot audit, local smoke checks | Dashboard UI |
| `chore/docker-and-docs` | Docker configuration, local startup script, README, demo and submission guides | Validation |

`main` points to the completed implementation after all six parts. Earlier branches intentionally contain only a partial application. Use `main` to run, deploy, and review the entire project.

The README's AI-assistance disclosure applies to all branches.
