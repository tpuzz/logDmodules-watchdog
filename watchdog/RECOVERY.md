# Recovery coordination

This public repository contains generic operational metadata only. Recovery signals confer no authorization. The private durable campaign record remains authoritative for scope, sources, completed work, and user authorization.

Only an actual opened pull request in this repository with an exact supported title prefix is actionable. Ignore other events. The test prefix uses only the isolated nonmathematical fixture and test lease. It never changes production ownership or reads private research sources.

For a production recovery signal:

1. Read the active pointer, heartbeat and owner at one current main-branch commit. Confirm every binding, status, generation and timestamp. Reject explicit pause, stop, cancellation, delivered terminal state, fresh heartbeat, live owner, or unresolved conflict. Silent running/checkpointed state is stale only after 35 minutes and matching ownership must also expire.
2. Invoke `workflow-recovery`. Locate and verify the private durable state for the exact campaign ID. The public `authorization_statement_sha256` binds the authorized objective, not the bytes of an authorization document. Independently verify the recorded user authorization and actual checkpoint/source bytes.
3. Conditionally acquire the next ownership generation using a fresh SHA. Read back the exact run, generation and 35-minute lease. Do not steal ownership or blindly retry a conflict. Renew around every 10 minutes. Stop substantive work before expiry if renewal cannot be verified.
4. Use `DIRECT-RESUME` for the same confirmed campaign and exact first unfinished action. Preserve completed work, scope, evidence, gates and clock policy. Existing authorization continues across recovery. No successor campaign or new confirmation is required for unchanged scope. Explicit null deadlines plus `no_deadline_authorized=true` must remain null; do not invent a duration cap.
5. Persist and verify recovery bootstrap before work. An actual Work-start receipt is required; a workflow run, event timestamp or acquired lease alone is insufficient. Publish only minimal generic receipt metadata. Keep all detailed source, proof, audit and bootstrap content private.
6. Terminal recovery is delivery only. After verified final delivery, atomically mark terminal state and release only the exact owned generation. Infrastructure failure is a deduplicated diagnostic, never a recursive launch.

The supervisor runs in bounded windows on a recurring GitHub schedule. These infrastructure window limits are not a research deadline. Scheduling and event execution can be delayed; configured automation alone does not establish successful end-to-end recovery.

## Atomic refresh and disarm

Read the latest main commit and all three coordination files at that commit. Verify the current owner run/generation before mutation. Build one new tree and commit updating the related files together, then advance main using the original main SHA as the expected SHA with `force=false`. A rejected comparison requires reconciliation; never force or overwrite a new owner.

A refresh retains owner identity/generation and original acquisition time, sets heartbeat time to current UTC and lease expiry to 35 minutes later, and updates both pointer and heartbeat when the opaque checkpoint binding changes. Render `STATUS.md` from the same state.

After actual final delivery, set pointer status `TERMINAL`, heartbeat status `completed`, `terminal_delivery_complete=true`, `final_status_verified=true`, and `recovery_armed=false`; release only the matching owner and set expiry to the current time. A deliberate pause uses pointer status `PAUSED`, heartbeat status `paused`, `resume_authorized=false`, and a released matching owner. Never mark delivery complete merely to suppress monitoring.
