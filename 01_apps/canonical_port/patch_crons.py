import re
with open("backend/agents/cron_scheduler.py", "r") as f:
    content = f.read()

replacement = """    # 3. 15-min Self-Healing & Hardware Keepalive Check (900s)
    async def _self_healing_check():
        logger.info("Cron: Executing 15-min Self-Healing & Hardware Keepalive Check")
        try:
            from agents.crons.daemon_supervisor import supervisor
            result = await supervisor.run_monitoring_cycle()
            logger.info(f"Daemon Supervisor result: {result}")
        except Exception as e:
            logger.error(f"Failed to run daemon supervisor: {e}")
        await asyncio.sleep(0)"""

content = re.sub(
    r"\s+# 3\. 15-min Self-Healing & Hardware Keepalive Check \(900s\)\n\s+async def _self_healing_check\(\):\n\s+logger\.info\(\"Cron: Executing 15-min Self-Healing & Hardware Keepalive Check\"\)\n\s+await asyncio\.sleep\(0\)",
    replacement,
    content
)

with open("backend/agents/cron_scheduler.py", "w") as f:
    f.write(content)
