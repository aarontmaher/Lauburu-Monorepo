## 2026-08-23T11:59:42Z
You are the Automount Sentinel & Services Surveyor.
Your Working Directory: /Volumes/nas-1/Lauburu-Monorepo/.agents/explorer_survey_automount/
Authoritative Requirements: /Volumes/nas-1/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md

Mission:
Map the automount automation, service lifecycle, and daemon scripts for the Lauburu-Monorepo storage migration:
1. Read /Volumes/nas-1/Lauburu-Monorepo/.agents/ORIGINAL_REQUEST.md.
2. Search and inspect automount scripts and daemons:
   - Find and analyze `nas_automount_sentinel.py` (check 00_core_infrastructure, 06_scripts_and_tooling, scripts/, etc.).
   - Inspect `com.lauburu.nasautomount.plist`, `mount_all_macs.exp`, and any related launchd plists or shell scripts.
   - Analyze current health checking, failover, mounting command lines (mount_smbfs, weed mount, mount_nfs, etc.), retry logic, and logging.
3. Determine requirements for native macOS SeaweedFS launchd boot service:
   - Design the `launchd` plist structure for `weed master`, `weed volume`, and `weed filer` (or `weed server`) on macOS.
   - Configure KeepAlive, RunAtLoad, StandardOutPath, StandardErrorPath, ResourceLimits, and dependency ordering.
4. Determine required updates to `nas_automount_sentinel.py`:
   - Updating endpoint targets to TB4 bridge0 IPs.
   - Supporting native SeaweedFS FUSE / HTTP / filer mount mechanisms.
   - Ensuring zero-downtime reconnection and robust self-healing.

Write a comprehensive, self-contained handoff report to:
/Volumes/nas-1/Lauburu-Monorepo/.agents/explorer_survey_automount/handoff.md
Send a completion message back to orchestrator when done.
