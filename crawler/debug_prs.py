import urllib.request
import urllib.error
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://www.meity.gov.in/writereaddata/files/The%20Digital%20Personal%20Data%20Protection%20Act%202023.pdf'
req = urllib.request.Request(
    url, 
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36'}
)
try:
    with urllib.request.urlopen(req, context=ctx) as response:
        body = response.read()
        print(f"Status: {response.status}, Size: {len(body)}")
        if body.startswith(b"%PDF-"):
            print("Successfully got PDF bytes!")
            with open("test_india.pdf", "wb") as f:
                f.write(body)
        else:
            print("Not a PDF. Preview:")
            print(body[:300])
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.code}")
    print(e.read()[:300])