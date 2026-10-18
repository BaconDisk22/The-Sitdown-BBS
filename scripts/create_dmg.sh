#!/bin/bash
# Hosted macOS occasionally returns Resource busy while preparing the image.
# Retry only that transient error; all other failures remain fatal.
set -euo pipefail
output=$1
volume=$2
log=$(mktemp)
trap 'rm -f "$log"' EXIT
for attempt in 1 2 3; do
  if hdiutil create -volname "$volume" -srcfolder dmg-staging -ov -format UDZO "$output" >"$log" 2>&1; then
    cat "$log"
    exit 0
  fi
  cat "$log" >&2
  if ! grep -q 'Resource busy' "$log" || [[ "$attempt" == 3 ]]; then
    exit 1
  fi
  sleep 5
done
