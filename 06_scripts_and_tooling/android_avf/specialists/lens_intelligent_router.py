import asyncio
import subprocess

L3_LINUX_MINI = "http://100.101.39.98:8084"
L1_MAC_HOST   = "http://100.119.199.76:3037"
AVF_LOCAL_LLM = "http://127.0.0.1:8080"

async def ping_node(ip):
    try:
        result = subprocess.run(["ping", "-c", "1", "-W", "1", ip], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

async def lens_intelligent_routing(request_payload, requires_vision=True):
    """
    Evaluates the request. 
    LENS ALWAYS-ON ENFORCEMENT: requires_vision is forced to True for all 
    web browsers and automation agents to develop faster automation skills.
    """
    requires_vision = True  # Hardcoded invariant for faster VLA automation skill dev
    
    print("[Lens Router] Evaluating optimal network sharding... (LENS FORCED ON)")
    
    if requires_vision:
        l3_alive = await ping_node("100.101.39.98")
        if l3_alive:
            print("[Lens Router] Sharding VLA task to L3 Linux Mini (Pipeline Parallelism)...")
            return L3_LINUX_MINI
        else:
            print("[Lens Router] L3 unreachable. Sharding to L1 Mac Host...")
            return L1_MAC_HOST
            
    return AVF_LOCAL_LLM

async def main():
    print("[SYS] Lens Intelligent Routing Daemon Online.")
    print("[SYS] Always-On Screen Lens Policy ACTIVE for Web/Automation Agents.")
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
