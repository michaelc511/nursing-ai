# Backup and restore (Fly.io)

All live data is on the volume `nurseops_data`, mounted at `/data`: `app.db`, `assist_memory.db`, `storage/` and `inbox/`. Fly takes daily snapshots.

## See snapshots
1. `fly volumes list`, and note the volume id.
2. `fly volumes snapshots list <volume id>`

## Take a snapshot now
`fly volumes snapshots create <volume id>`. Do this before a risky change.

## Restore
1. Stop the app: `fly scale count 0`
2. Create a volume from the snapshot: `fly volumes create nurseops_data --snapshot-id <snapshot id> --size 1 --region sjc --yes`
3. Delete the damaged volume, after confirming its id: `fly volumes destroy <old volume id>`. This can't be undone.
4. Start the app: `fly scale count 1`
5. Sign in and confirm that the case queue matches what you expect.

## Rebuild the demo
For synthetic demo data, a restore usually isn't needed. Use the hidden demo reset to refill the queue, or run `fly ssh console -C "python -m app.cli reset-demo --yes"`.
