# CentralNJ operator verification checklist

This is a **manual validation plan**, not evidence that a device or message was verified. Do not publish MQTT messages or transmit over radio as part of this checklist without a separate, explicit operator decision.

## Before starting

- [ ] Confirm the Intel Mac app launches and the dashboard is readable.
- [ ] Open Settings and confirm **Allow operator send preflight** is **off** on a fresh launch.
- [ ] Click **CHECK SEND SAFETY** with the toggle off; it must deny transmission.
- [ ] Enable the toggle and check again; the offline check must still deny transmission because live radio readiness and operator confirmation are not supplied.
- [ ] Restart the app; the send-safety toggle must return to **off** (not persisted).

## Radio status (read-only observations)

- [ ] In Demo mode, confirm the interface does not claim a real radio connection.
- [ ] Run **Check Radio Connection** with a chosen USB device or TCP host only when the BBS is not using that connection.
- [ ] Treat USB enumeration and TCP reachability as transport observations, **not** Meshtastic handshake or delivery proof.
- [ ] Confirm status distinguishes server process, SDK session, and actual observed RX activity.

## MQTT monitor

- [ ] Leave the MQTT monitor disabled unless monitoring is explicitly intended.
- [ ] If enabled, configure only an authorized narrow subscription topic.
- [ ] Confirm broker counts are labeled separately from radio RX and do not imply successful two-way delivery.
- [ ] Do not put channel PSKs or broker credentials into repository commits or screenshots.

## Build and sign-off

- [ ] Check the **tests** GitHub Actions workflow.
- [ ] Check the **Intel macOS app and DMG** workflow and download its test artifact.
- [ ] Launch the packaged DMG on the target Intel Mac; CI alone does not prove hardware compatibility.
- [ ] Record the app revision, hardware model, Meshtastic firmware, and results before approving any actual transmit workflow.

**Release gate:** Do not describe two-way CentralNJ messaging as verified until a separately authorized, real end-to-end radio send/receive test is completed and recorded. Pull requests remain manual-review only; no auto-merge.
