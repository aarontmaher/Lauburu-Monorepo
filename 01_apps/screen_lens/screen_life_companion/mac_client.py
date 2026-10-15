import webview
import time
import requests

def wait_for_server(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url)
            if r.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)
    return False

if __name__ == '__main__':
    url = 'http://127.0.0.1:3036/'
    # Wait for the backend daemon to boot if started simultaneously
    wait_for_server(url)
    webview.create_window('Life Companion', url, width=1200, height=800, frameless=False)
    webview.start()
