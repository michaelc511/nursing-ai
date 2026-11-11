# Deploy NurseOps Now to Fly.io

App `nurseops-now`, region `sjc`, one machine, volume `nurseops_data` at `/data`, URL https://nurseops-now.fly.dev. Run commands from the repository root.

## First deploy
1. `fly launch --no-deploy --copy-config --name nurseops-now --region sjc --org personal --ha=false --yes`
2. `fly volumes create nurseops_data --size 1 --region sjc --yes`
3. Stage the secrets:
   - `grep '^ANTHROPIC_API_KEY=' .env | fly secrets import --stage`
   - `fly secrets set SECRET_KEY="$(openssl rand -hex 32)" --stage`
   - `fly secrets set DEMO_PASSWORD='<a strong password you keep>' --stage`
   - `fly secrets set MCP_TOKEN='<a long random token you keep>' --stage`
4. `fly deploy --ha=false`

Never set `DEMO_AUTOFILL` on Fly: it hands the password to every visitor.

## Check it
- `curl https://nurseops-now.fly.dev/health` returns `{"status":"ok"}`.
- `curl -i https://nurseops-now.fly.dev/api/auth/demo` returns 404.
- Sign in, click the invisible spot just right of the **NurseOps Now** title, and confirm the reset to fill the queue. This runs real Claude on 3 cases, about $0.30.
- POST to `/mcp` without a token returns 401.

## Sign-in lockout
Three wrong passwords from one network address lock sign-in from that address for 24 hours. To clear lockouts: `fly ssh console -C "python -m app.cli unlock-logins"`

## Update
Ship the code, then run `fly deploy --ha=false` from the terminal.

## Roll back
`fly releases --image`, then `fly deploy --image <previous image> --ha=false`.

## Stop and start
- Stop: `fly scale count 0`
- Start: `fly scale count 1`

The machine also stops when idle and starts on the next request, so the first request after a pause is slower. Open the site a few minutes before a presentation.

## Costs and usage
Fly's app **Metrics** page and billing page show hosting. The Anthropic console shows AI spend. The app stops AI calls at its daily cap, `DAILY_COST_CAP_USD`.
