# Log D Modules watchdog

Generic coordination for one already-authorized campaign. See [current status](watchdog/STATUS.md), [infrastructure status](watchdog/INFRASTRUCTURE.json), and [recovery protocol](watchdog/RECOVERY.md).

This intentionally public repository contains only operational metadata and generic recovery instructions. Source documents, private locations, substantive prompts, mathematical work and results remain private.

The safety logic is adapted from the tested [McKay watchdog](https://github.com/tpuzz/mckay-watchdog). It verifies exact campaign bindings, stale heartbeats, expired ownership, incident deduplication, terminal delivery, and genuine recovery acknowledgement. Isolated test events use `LOGDMODULES_RECOVERY_TEST`; production recovery uses `LOGDMODULES_RECOVERY`.
