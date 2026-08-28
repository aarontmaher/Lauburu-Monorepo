import requests
import logging

logger = logging.getLogger(__name__)

class SyncthingHandler:
    def __init__(self, api_key=None, url="http://localhost:8384"):
        self.url = url
        self.api_key = api_key
        # Normally you parse this from ~/.config/syncthing/config.xml
        # but passing it directly is easier for the orchestrator instantiation.
        self.headers = {"X-API-Key": self.api_key} if self.api_key else {}
        self.is_paused = False

    def check_status(self):
        """Ping Syncthing to ensure the API is reachable."""
        try:
            r = requests.get(f"{self.url}/rest/system/status", headers=self.headers, timeout=5)
            if r.status_code == 200:
                return True
            else:
                logger.warning(f"Syncthing API returned {r.status_code}. Invalid API Key?")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Syncthing API unreachable at {self.url}: {e}")
            return False

    def pause_all_transfers(self):
        """Pauses all Syncthing device synchronizations to save bandwidth/power."""
        if not self.api_key:
            logger.warning("Syncthing API key missing, cannot pause.")
            return False
            
        logger.info("Pausing all Syncthing transfers to conserve bandwidth...")
        try:
            # Omitting the ?device= query param pauses all devices
            r = requests.post(f"{self.url}/rest/system/pause", headers=self.headers, timeout=5)
            if r.status_code == 200:
                self.is_paused = True
                return True
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to pause Syncthing: {e}")
            return False

    def resume_all_transfers(self):
        """Resumes all Syncthing device synchronizations."""
        if not self.api_key:
            return False
            
        logger.info("Resuming all Syncthing transfers...")
        try:
            r = requests.post(f"{self.url}/rest/system/resume", headers=self.headers, timeout=5)
            if r.status_code == 200:
                self.is_paused = False
                return True
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to resume Syncthing: {e}")
            return False
