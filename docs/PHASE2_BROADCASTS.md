# The Boss Has Spoken

Remote `/announce <channel> <text>`, `/schedule <ISO-time> <channel> <text>`,
`/announcements`, and `/cancelannouncement <id>` require an exact configured
`[announcements] admin_nodes` ID. Empty means deny. Node IDs identify senders
reported by the radio; this is an allowlist, not cryptographic proof of identity.
Only grant access on a trusted mesh. Local desktop operators control their own
server and are authorized separately through a private parent/child pipe.

Schedules require an explicit timezone, e.g. `2026-12-01T18:00:00-05:00`, from
5 seconds to 30 days ahead, with at most 20 pending jobs. Authorization, enabled
channel and the 200-byte UTF-8 limit are checked both at creation and dispatch.
A removed administrator or disabled channel prevents dispatch. Jobs more than
60 seconds late are skipped, avoiding a burst after downtime. Pending jobs
survive restarts. Jobs claimed before a crash are never replayed.

All broadcast attempts share a persistent cooldown (default/floor 60 seconds).
A job colliding with another broadcast is skipped, not delayed or retried.
Startup broadcasts are disabled by default. Configure `[startup] enabled`,
`channel`, `message` and `cooldown_seconds` (default 3600, minimum 300).
Blank startup text uses the existing clean-by-default public personality.
Custom operator text is sent verbatim. A failed/uncertain send still consumes
its cooldown. Clock rollback suppresses attempts until time catches up.

State lives in `sitdown-broadcasts.db` beside the server config. Keep this file
across restarts; deleting it resets anti-spam history. State storage failures
fail closed. Successful submission does not confirm over-the-air delivery.
Original TC²-BBS credit and GPL license remain unchanged.

Validation uses mock radios and temporary databases. Physical radio, delivery,
clock changes on the deployed host and restart behavior still need operator QA.
