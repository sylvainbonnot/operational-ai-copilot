"""Check what metric families are exposed on /metrics."""
import httpx

resp = httpx.get("http://localhost:8000/metrics")
print(f"Status: {resp.status_code}")
print(f"Content-Type: {resp.headers.get('content-type')}")
print()
# Print first 60 lines
for i, line in enumerate(resp.text.splitlines()):
    if i >= 60:
        print("... (truncated)")
        break
    print(line)
