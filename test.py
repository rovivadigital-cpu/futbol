import logging
logging.basicConfig(level=logging.DEBUG)

from curl_cffi import requests as cffi_requests
s = cffi_requests.Session(impersonate="chrome131")
s.headers.update({
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    "Origin": "https://www.sofascore.com",
    "Referer": "https://www.sofascore.com/football",
})
r = s.get("https://api.sofascore.com/api/v1/sport/football/scheduled-events/2026-06-08", timeout=30)
print(r.status_code)
print(r.text[:300])
