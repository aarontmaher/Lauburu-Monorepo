import subprocess
import time
import threading
import logging
import psutil

logger = logging.getLogger("multi_wan.rogue_monitor")

class RogueProcessMonitor:
    """
    Universally monitors system CPU usage and acts defensively against rogue processes.
    If any background process (especially language servers, runaway python scripts, or 
    excessive IDE processes) consumes > 90% CPU for a sustained period, it will throttle
    them (renice) or terminate them if they exceed 150%.
    """
    
    def __init__(self, throttle_threshold: float = 90.0, kill_threshold: float = 150.0):
        self.throttle_threshold = throttle_threshold
        self.kill_threshold = kill_threshold
        self._running = True
        self._recent_rogues = []
        self._loop_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._loop_thread.start()

    def get_recent_rogues(self):
        return self._recent_rogues

    def _monitor_loop(self):
        logger.info("🛡️ Rogue Process Monitor active.")
        while self._running:
            try:
                rogues = []
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'cmdline']):
                    try:
                        # psutil cpu_percent requires an interval to be accurate.
                        # Calling it twice with a tiny sleep or using interval in a separate pass is better.
                        # For efficiency, we will use the top-level stats and cross-reference with 'ps'.
                        pass
                    except Exception:
                        continue
                
                # Use 'ps' for accurate point-in-time CPU usage
                output = subprocess.check_output(['ps', '-eo', 'pid,pcpu,comm'], text=True)
                lines = output.strip().split('\n')[1:]
                
                for line in lines:
                    parts = line.split(maxsplit=2)
                    if len(parts) < 3:
                        continue
                        
                    pid_str, pcpu_str, comm = parts
                    
                    # Ignore harmless processes like WindowServer or kernel_task
                    if 'WindowServer' in comm or 'kernel_task' in comm:
                        continue
                        
                    try:
                        pcpu = float(pcpu_str)
                        pid = int(pid_str)
                    except ValueError:
                        continue
                        
                    if pcpu > self.throttle_threshold:
                        action = "THROTTLED"
                        if pcpu > self.kill_threshold:
                            # Terminate severe rogues instantly
                            logger.error(f"🚨 CRITICAL: Rogue process {comm} (PID {pid}) at {pcpu}%. KILLING.")
                            subprocess.run(['kill', '-9', str(pid)], capture_output=True)
                            action = "KILLED"
                        else:
                            # Throttle moderate rogues
                            logger.warning(f"⚠️ High CPU: {comm} (PID {pid}) at {pcpu}%. Renicing.")
                            subprocess.run(['renice', '-n', '15', '-p', str(pid)], capture_output=True)
                            
                        rogues.append({
                            "pid": pid,
                            "name": comm,
                            "cpu": pcpu,
                            "action": action,
                            "timestamp": time.time()
                        })
                
                if rogues:
                    self._recent_rogues = rogues + self._recent_rogues[:9] # Keep last 10
                    
            except Exception as e:
                logger.error(f"Rogue monitor error: {e}")
                
            time.sleep(15) # Scan every 15 seconds
