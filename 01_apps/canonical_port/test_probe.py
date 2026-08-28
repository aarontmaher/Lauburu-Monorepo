import urllib.request
import json
try:
    url = "http://127.0.0.1:4000/api/v1/apps/spec-03/status"
    req = urllib.request.Request(url, headers={"User-Agent": "CanonicalPort/3.0"})
    with urllib.request.urlopen(req, timeout=1.0) as resp:
        if resp.status == 200:
            res_dict = json.loads(resp.read().decode("utf-8"))
            print(res_dict)
except Exception as e:
    print("Error:", e)
