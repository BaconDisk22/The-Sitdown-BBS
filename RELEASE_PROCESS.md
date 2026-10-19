# Phase 4: Automated Intel Mac Releases

GitHub Actions now has two paths:

- **Intel Mac test build**: every push to `main` creates a downloadable workflow artifact for testing.
- **Publish Intel Mac Release**: on version tags matching `v*` or manual dispatch, builds an Intel x86_64 `.app`, wraps it in a versioned `.dmg`, computes `SHA256SUMS.txt`, and publishes both under **GitHub → Releases**.

## Publishing the next beta after Stage 4

1. Merge the Stage 4 release-readiness pull request after CI checks pass. Confirm the Intel Mac test build succeeds on the merged main branch.
2. Open **Actions → Publish Intel Mac Release → Run workflow**.
3. Select the **main** branch, enter `v0.1.0-beta.2` and click **Run workflow**.
4. Wait for the run to succeed, then open **Releases** and download `The-Sitdown-BBS-Intel-Mac-v0.1.0-beta.2.dmg`.

Alternatively push an annotated version tag to `main`; a matching tag automatically triggers the workflow. Use new versions for each new release.

**Warning:** Builds are unsigned and unnotarized. macOS Gatekeeper may ask for approval via System Settings → Privacy & Security. Never disable Gatekeeper globally. This pipeline does not verify physical Meshtastic radio behavior or provide an Apple Developer signature. The workflow uses `GITHUB_TOKEN` with `contents: write` and requires GitHub Actions to have permission to publish releases.

## What's included in beta.2

- SDK disconnect detection with an opt-in desktop recovery countdown and capped retries.
- Hardware-free recovery regressions, database integrity checks, and verified SQLite-safe ZIP backups through **The Books**.
- Existing Jersey dashboard, demo mode, weather/MQTT, broadcasts, and radio transport options are retained.

**Limitations:** This beta is unsigned and unnotarized. No physical Meshtastic radio or macOS Tahoe verification is claimed. Test the DMG in Demo mode first. Do not overwrite the already published beta.1 release: always publish a new version.

## Release verification checklist

1. Check the **Publish Intel Mac Release** workflow run completes successfully.
2. Confirm GitHub Releases contains the versioned Intel Mac DMG and `SHA256SUMS.txt`.
3. Download and verify the checksum locally: `shasum -a 256 -c SHA256SUMS.txt` in the directory containing both files.
4. Install the DMG, open the app, and verify Demo mode and **The Books** backup on an Intel Mac.
5. Record actual TCP/USB radio tests separately when hardware becomes available.
