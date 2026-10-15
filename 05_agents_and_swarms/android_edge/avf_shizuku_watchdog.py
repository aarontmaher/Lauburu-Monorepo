import subprocess
import time
import logging
import sys

# Configure logging for the Watchdog
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [SHIZUKU WATCHDOG] - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def check_memory_pressure():
    """
    Poll logcat for LMKD (Low Memory Killer Daemon) events indicating memory pressure.
    Requires 'rish' (Shizuku Root Shell) to be available in the PATH.
    """
    try:
        # We look specifically for the lmkd tag
        result = subprocess.run(
            ["rish", "-c", "logcat -d -s lmkd | tail -n 15"], 
            capture_output=True, 
            text=True,
            timeout=5
        )
        output = result.stdout.lower()
        if "kill" in output or "critical" in output or "pressure" in output:
            return True
    except subprocess.TimeoutExpired:
        logging.warning("rish logcat poll timed out. Shizuku binder may be under heavy load.")
    except FileNotFoundError:
        logging.error("rish binary not found. Shizuku must be configured and in PATH.")
        time.sleep(10) # Prevent rapid crash looping if rish is missing
    except Exception as e:
        logging.error(f"Unexpected error polling logcat: {e}")
        
    return False

def drop_caches():
    """
    Execute root Shizuku command to drop pagecache, dentries, and inodes to spare the AVF VM.
    """
    try:
        # sync first to ensure dirty pages are written to disk
        subprocess.run(["rish", "-c", "sync"], capture_output=True)
        # Drop caches
        subprocess.run(["rish", "-c", "echo 3 > /proc/sys/vm/drop_caches"], capture_output=True)
        logging.warning("CRITICAL MEMORY PRESSURE DETECTED: Dropped Android caches (pagecache, dentries, inodes) to protect AVF Uptime.")
        
        # Optional: Force-stop heavy background apps if needed (e.g., com.google.android.youtube)
        # subprocess.run(["rish", "-c", "am force-stop com.google.android.youtube"], capture_output=True)
    except Exception as e:
        logging.error(f"Failed to execute drop_caches via rish: {e}")

def main():
    logging.info("Starting AVF Shizuku Watchdog Daemon. Monitoring LMKD...")
    
    # Optional: Clear logcat at startup so we don't trigger on old LMKD events
    try:
        subprocess.run(["rish", "-c", "logcat -c"], capture_output=True)
        logging.info("Cleared historic logcat buffers.")
    except Exception:
        pass
        
    while True:
        if check_memory_pressure():
            drop_caches()
            # Sleep longer after dropping caches to allow system to stabilize
            time.sleep(10.0)
        else:
            # Poll every 2 seconds
            time.sleep(2.0)

if __name__ == "__main__":
    main()
