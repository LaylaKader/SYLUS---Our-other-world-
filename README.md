# SYLUS — source backup

This repository contains a source snapshot of the SYLUS Floot project.

- Main builder: Floot project `c8585fd6-f2d8-406a-8516-0fa641894c89`
- Snapshot date: 2026-11-16
- Main app: unpublished; preview only
- This backup is a recovery copy, not a separate running deployment.
- Secrets and environment variable values are intentionally excluded.
- Database schema snapshots are included; personal conversation rows are not exported.

The snapshot is stored under `backup/floot-source/`. New implementation changes should be copied here after each coherent milestone. The Floot checkpoint is also named **Pre-expansion backup**; a later checkpoint will capture the new voice, media and Together features.

## Current integration notes

- Cloudflare Workers AI credentials are requested through Floot's secure connection flow; no secret belongs in this repository.
- Voice currently uses browser speech APIs as a no-cost prototype.
- Full incoming/background calls, multi-account isolation, protected-streaming integrations, and native Android support still require additional implementation and testing.
