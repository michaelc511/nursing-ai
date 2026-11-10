#!/usr/bin/env bash
set -euo pipefail
# Copy the synthetic sample faxes into ./inbox for a demo run (then: python -m app.cli poll).
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cp "$ROOT"/data/samples/*.pdf "$ROOT/inbox/"
ls "$ROOT/inbox"
