"""Quick test: can we fetch nopCommerce from inside Docker?"""
try:
    from curl_cffi import requests
    r = requests.get("https://demo.nopcommerce.com/", impersonate="chrome", timeout=20)
    print(f"curl_cffi: Status={r.status_code}, Length={len(r.text)}")
    if "<title>" in r.text:
        start = r.text.find("<title>") + 7
        end = r.text.find("</title>")
        print(f"Title: {r.text[start:end]}")
except Exception as e:
    print(f"curl_cffi FAILED: {e}")

try:
    import httpx
    r2 = httpx.get("https://demo.nopcommerce.com/", timeout=15, follow_redirects=True)
    print(f"httpx: Status={r2.status_code}, Length={len(r2.text)}")
except Exception as e2:
    print(f"httpx FAILED: {e2}")
