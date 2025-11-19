# Scheduling options

## Prefect deployments
Run `poetry run python prefect_flows.py` to build deployments:
- `researcher-weekly` (cron: `0 8 * * MON`, tz `Europe/Helsinki`)
- `reader-daily` (cron: `0 8 TUE-FRI`, tz `Europe/Helsinki`)
- `publisher-daily` (cron: `5 8 TUE-FRI`, tz `Europe/Helsinki`)

Start a Prefect worker/agent that polls the default work queue:
```bash
prefect worker start -p default-agent-pool
```

## Cron fallback
If Prefect is unavailable, add the following to `crontab -e`:
```
0 8 * * MON cd /opt/ai-news && /usr/bin/env poetry run python agents/researcher.py >> logs/researcher.log 2>&1
0 8 * * TUE-FRI cd /opt/ai-news && /usr/bin/env poetry run python agents/reader.py >> logs/reader.log 2>&1
5 8 * * TUE-FRI cd /opt/ai-news && /usr/bin/env poetry run python agents/publisher.py >> logs/publisher.log 2>&1
```
Ensure the system timezone is set to `Europe/Helsinki` (EET/EEST) to honor daylight saving shifts.
