# NurseOps Now production ops

Scope: what runs today on Fly.io with synthetic data, and the plan for a real production system. Targets marked **Proposed** are starting points, not measured commitments. Owner of every item: Mike Chang.

## Identity and SSO plan
- **Today:** four demo accounts share one password stored as a Fly secret. Roles are enforced in the service layer.
- **Production:** sign-in through the health plan's identity provider using OIDC or SAML, with individual accounts. Identity-provider groups map to Intake, Nurse and Medical Director roles. `DEMO_MODE` is off and the shared password is removed.

## Secrets
- **Today:** Fly secrets hold `ANTHROPIC_API_KEY`, `SECRET_KEY`, `DEMO_PASSWORD` and `MCP_TOKEN`. The container refuses to start without `SECRET_KEY` and `DEMO_PASSWORD`. `.env` is never committed or copied into the image.
- **Production:** a managed secrets service, with scheduled rotation and access logs.

## Service levels and alerts
| Measure | Proposed target | Where it is seen |
| --- | --- | --- |
| Availability | 99.5% a month | Fly health check on `/health` |
| Non-AI API p95 | Under 500 ms | Load test, Fly metrics |
| AI review p95 | Under 90 s | `/api/ai/traces` |
| Unverified quote rate | Under 5% | `/api/ai/quality` |
| AI cost per day | Under the daily cap ($10 by default) | `/api/ai/quality`, Anthropic console |

The app raises quality alerts through `/api/ai/quality`, shown in debug mode. **Production:** send these and Fly health failures to a paging tool.

## Load test
`tools/scripts/load_test.py` exercises the non-AI paths. Result from the production image in a local container limited to 1 CPU and 2 GB, 2026-11-10, with 300 requests, 10 at a time and no errors:

| Path | Median | p95 |
| --- | --- | --- |
| `/health` | 3 ms | 14 ms |
| `/api/cases` | 27 ms | 58 ms |
| `/api/metrics` | 22 ms | 58 ms |

Memory stayed near 545 MB. This covers a local container with 3 cases, not Fly's network or AI calls, so repeat it against the live URL before relying on it.

## Backups and disaster recovery
- **Today:** SQLite, stored files and chat memory sit on one encrypted Fly volume with daily snapshots. Restore steps are in [runbooks/backup-restore.md](runbooks/backup-restore.md). The policy index is rebuilt in every image.
- **Production:** Postgres with point-in-time recovery and object storage for documents, both replicated to a second region. Run a restore test on a schedule.

## Retention
- **Today:** synthetic data only. A demo reset deletes all cases, decisions and audit entries.
- **Production:** retention periods for requests, decisions and audit logs must be set with compliance and legal against the plan's obligations before launch. The demo reset must stay disabled.

## Runbooks
- [Deploy to Fly.io](runbooks/deploy-fly.md)
- [Backup and restore](runbooks/backup-restore.md)
