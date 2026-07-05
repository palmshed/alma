# Release Checklist

- [ ] Version updated (`VERSION`, `__init__.py`, `pyproject.toml`)
- [ ] CI passed
- [ ] Smoke passed (`alma verify --platform --application`)
- [ ] E2E passed (`alma verify ui --browser` against deployed app)
- [ ] `alma verify` passed locally (platform + application + UI)
- [ ] Production deployment healthy (`/api/health`)
- [ ] Release artifacts archived (CI retains screenshots, HAR, console, report)
- [ ] GitHub Release published with changelog
