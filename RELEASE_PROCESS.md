# Phase 4: Automated Intel Mac Releases

GitHub Actions now has two paths:

- **Intel Mac test build**: every push to `main` creates a downloadable workflow artifact for testing.
- **Publish Intel Mac Release**: on version tags matching `v*` or manual dispatch, builds an Intel x86_64 `.app`, wraps it in a versioned `.dmg`, computes `SHA256SUMS.txt`, and publishes both under **GitHub → Releases**.

## Publishing an Intel Mac beta

1. Confirm the intended changes are merged and both checks and the Intel Mac test build succeed on that exact main commit. Beta 4 uses PR #98 merge commit `76a994f28777e8eb1537ce3a509af8660da866f2`.
2. Open **Actions → Publish Intel Mac Release → Run workflow**.
3. Select the **main** branch, enter `v0.1.0-beta.4` and click **Run workflow**.
4. Wait for the run to succeed, then open **Releases** and download `The-Sitdown-BBS-Intel-Mac-v0.1.0-beta.4.dmg`.

Alternatively push an annotated version tag to `main`; a matching tag automatically triggers the workflow. Use new versions for each new release.

**Warning:** Builds are unsigned and unnotarized. macOS Gatekeeper may ask for approval via System Settings → Privacy & Security. Never disable Gatekeeper globally. This pipeline does not verify physical Meshtastic radio behavior or provide an Apple Developer signature. The workflow uses `GITHUB_TOKEN` with `contents: write` and requires GitHub Actions to have permission to publish releases.

## What's included in beta.4

- Non-writing radio preflight: TCP port reachability or USB enumeration, with explicit unverified protocol/delivery status. Demo and active-session checks skip radio contact.
- CentralNJ setup guidance, credential-free MQTT diagnostics and recovery telemetry, and read-only connection observations.
- Default-off, session-only operator send preflight. It does not transmit, provide a message composer, or disable the existing BBS responses after an operator starts a real server.
- Offline acceptance reporting, conservative stable-release gates, safety regressions, and the Home dashboard navigation fix.
- See `docs/CENTRALNJ_OPERATOR_CHECKLIST.md` and `docs/V1_RELEASE_RUNBOOK.md` for hardware acceptance requirements.

### Retained from beta.3

- Stage 4 SDK disconnect detection, opt-in recovery countdown and capped retries remain included.
- Stage 5 dashboard performance improvements: avoid duplicate banner resampling and redundant navigation re-layout.
- More actionable, credential-safe TCP and USB transport error hints.
- Hardware-free recovery regressions, SQLite-safe ZIP backups, and a **Verify Backup** button using read-only ZIP and database integrity checks.
- Existing Jersey dashboard, demo mode, weather/MQTT, broadcasts, and radio transport options are retained.

**Limitations:** This beta is unsigned and unnotarized. No physical Meshtastic radio or macOS Tahoe verification is claimed. The Verify Backup feature does not restore or overwrite data. Test the DMG in Demo mode first. Do not overwrite the already published beta.1, beta.2, or beta.3 releases: always publish a new version.

## Release verification checklist

1. Check the **Publish Intel Mac Release** workflow run completes successfully.
2. Confirm GitHub Releases contains the versioned Intel Mac DMG and `SHA256SUMS.txt`.
3. Download and verify the checksum locally: `shasum -a 256 -c SHA256SUMS.txt` in the directory containing both files.
4. Install the DMG, open the app, and verify Demo mode, **The Books** backup, and **Verify Backup** on a test ZIP on an Intel Mac.
5. Record actual TCP/USB radio tests separately when hardware becomes available.
