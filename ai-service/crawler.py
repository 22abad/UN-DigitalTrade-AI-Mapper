import asyncio
import os
import re
import time
from datetime import datetime
from html.parser import HTMLParser
from playwright.async_api import async_playwright, Page, BrowserContext
from typing import Dict, Optional, Any
from urllib.parse import urljoin, urlparse
from playwright_stealth import stealth_async
from collections import deque

import httpx

# ── Constants ─────────────────────────────────────────────────────────────────

DOWNLOADS_DIR = "./downloads"
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

INVALID_URL_PATTERNS = [
    r"javascript:",
    r"mailto:",
    r"tel:",
    r"fax:",
]

_HTTPX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
}

# Generic download-endpoint patterns (CMS-agnostic).
# Matches Joomla mediaform.download, WordPress attachment endpoints,
# Drupal file/download, generic ?download= params, etc.
_DOWNLOAD_LINK_PATTERNS = [
    r"[?&]task=\w+\.download",     # Joomla: ?task=mediaform.download
    r"[?&]action=download",        # generic: ?action=download
    r"[?&]download=(?!0)",         # generic: ?download=1 (skip =0)
    r"[?&]type=pdf",               # generic: ?type=pdf
    r"[?&]format=pdf",             # generic: ?format=pdf
    r"[?&]file=",                  # file param
    r"[?&]attachment=",            # attachment param
    r"/download/\w",               # path segment /download/...
    r"/dl/\w",                     # short path /dl/...
    r"/files/\w",                  # /files/...
    r"\.pdf(\?|$)",                # .pdf with optional query
    r"\.docx?(\?|$)",              # .doc/.docx
    r"drive\.google\.com/file/d/", # Google Drive file links
    r"drive\.google\.com/open\?",  # Google Drive open links
    r"docs\.google\.com/",         # Google Docs links
]

_GDRIVE_FILE_RE = re.compile(
    r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)"
)
_GDRIVE_OPEN_RE = re.compile(
    r"drive\.google\.com/open\?(?:.*&)?id=([a-zA-Z0-9_-]+)"
)
_GDOCS_RE = re.compile(
    r"docs\.google\.com/(?:document|spreadsheets|presentation)/d/([a-zA-Z0-9_-]+)"
)


def _gdrive_to_download_url(url: str) -> str | None:
    """Convert a Google Drive/Docs viewer URL to a direct-download URL."""
    m = _GDRIVE_FILE_RE.search(url)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    m = _GDRIVE_OPEN_RE.search(url)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    m = _GDOCS_RE.search(url)
    if m:
        doc_type = re.search(r"docs\.google\.com/(\w+)/d/", url)
        kind = doc_type.group(1) if doc_type else "document"
        return f"https://docs.google.com/{kind}/d/{m.group(1)}/export?format=pdf"
    return None

_MIN_TEXT_CHARS = int(os.getenv("CRAWLER_MIN_TEXT_CHARS", "300"))


# ── Layer 1: httpx HTML parser ────────────────────────────────────────────────

class _LinkExtractor(HTMLParser):
    """Stdlib HTML parser: extracts hrefs and visible body text."""

    _SKIP = {"script", "style", "noscript", "head", "meta", "link", "iframe", "svg", "path"}

    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.links: list[str] = []
        self._text_parts: list[str] = []
        self._depth_skip = 0     # skip counter for nested skip-tags

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._depth_skip += 1
            return
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href and not any(re.match(p, href) for p in INVALID_URL_PATTERNS):
                self.links.append(urljoin(self.base_url, href))

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._depth_skip:
            self._depth_skip -= 1

    def handle_data(self, data):
        if self._depth_skip:
            return
        text = data.strip()
        if text:
            self._text_parts.append(text)

    @property
    def text(self) -> str:
        return re.sub(r"[ \t]{2,}", " ", " ".join(self._text_parts)).strip()


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_JS_INLINE_RE = re.compile(r"\(function\s*\(.*?\}\s*\)\s*;?", re.DOTALL)
_BLANK_LINES_RE = re.compile(r"\n{3,}")

def _clean_text(text: str) -> str:
    """Strip any HTML/JS artifacts that slipped through the parser."""
    text = _HTML_TAG_RE.sub(" ", text)
    text = _JS_INLINE_RE.sub(" ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()


def _classify_links(links: list[str]) -> tuple[list[str], list[str]]:
    """Split links into (pdf_or_download_links, other_links)."""
    download, other = [], []
    for link in links:
        if any(re.search(pat, link) for pat in _DOWNLOAD_LINK_PATTERNS):
            download.append(link)
        else:
            other.append(link)
    return download, other


def _save_bytes(content: bytes, url: str, content_type: str = "") -> str:
    """Save raw bytes to DOWNLOADS_DIR, infer filename from URL."""
    parsed = urlparse(url)
    name = os.path.basename(parsed.path).split("?")[0] or f"doc_{int(time.time())}"
    if "pdf" in content_type and not name.lower().endswith(".pdf"):
        name += ".pdf"
    local_path = os.path.join(DOWNLOADS_DIR, name)
    with open(local_path, "wb") as f:
        f.write(content)
    return local_path


def _sniff_redirect(html: str, base_url: str) -> str | None:
    """Extract redirect target from tiny HTML (meta-refresh or JS location assign)."""
    # <meta http-equiv="refresh" content="0; url=...">
    m = re.search(
        r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\']?\d+;\s*url=([^"\'>\s]+)',
        html, re.I,
    )
    if m:
        return urljoin(base_url, m.group(1).strip("'\""))
    # window.location[.href] = "..."  /  document.location = "..."
    m = re.search(
        r'(?:window|document)\.location(?:\.href)?\s*=\s*["\']([^"\']+)["\']', html,
    )
    if m:
        return urljoin(base_url, m.group(1))
    return None


_BINARY_TYPES = (
    "application/pdf",
    "application/octet-stream",
    "application/msword",
    "application/vnd.openxmlformats",
    "application/zip",
)


async def _httpx_fetch(url: str, *, _client: httpx.AsyncClient | None = None, _depth: int = 0) -> Dict[str, Any] | None:
    """
    Layer 1 — plain async HTTP, no browser.

    Uses a single AsyncClient across hops so session cookies set by the
    first page visit are automatically carried to download endpoints
    (required for Joomla mediaform.download and similar CMS gating).

    Strategy per response:
      1. Binary / PDF content-type         → save and return {"type": "pdf"}
      2. Content-Disposition: attachment   → save regardless of content-type
      3. Tiny HTML + redirect signal       → follow meta-refresh or JS location
      4. HTML with download links          → follow best candidate (one hop)
      5. HTML with enough text             → return {"type": "text"}
      6. Anything else                     → return None (fall through to Playwright)
    """
    ts = lambda: datetime.now().strftime("%H:%M:%S")

    # Depth cap: avoid infinite redirect loops
    if _depth > 3:
        return None

    owned_client = _client is None
    client = _client or httpx.AsyncClient(
        headers=_HTTPX_HEADERS,
        follow_redirects=True,
        timeout=30.0,
    )

    try:
        print(f"{ts()}  [http] GET {url}")
        resp = await client.get(url)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "").lower()
        content_disp = resp.headers.get("content-disposition", "").lower()
        body = resp.content
        print(f"{ts()}  [http] {resp.status_code}  type={content_type[:50]}  "
              f"disp={content_disp[:40] or '-'}  bytes={len(body):,}")

        # ── 1. Binary content-type ───────────────────────────────────────────
        if any(t in content_type for t in _BINARY_TYPES):
            local_path = _save_bytes(body, url, content_type)
            print(f"{ts()}  [http] saved binary → {local_path}")
            return {"type": "pdf", "url": url, "pdf_path": local_path}

        # ── 2. Content-Disposition: attachment (content-type may lie) ────────
        if "attachment" in content_disp or (
            "filename" in content_disp and "html" not in content_type
        ):
            local_path = _save_bytes(body, url, content_type)
            print(f"{ts()}  [http] saved attachment → {local_path}")
            return {"type": "pdf", "url": url, "pdf_path": local_path}

        if "html" not in content_type:
            return None

        html = resp.text

        # ── 3. Tiny HTML — check for redirect signals ─────────────────────
        if len(html.strip()) < 500:
            redirect_target = _sniff_redirect(html, str(resp.url))
            if redirect_target:
                print(f"{ts()}  [http] micro-redirect → {redirect_target}")
                return await _httpx_fetch(redirect_target, _client=client, _depth=_depth + 1)
            print(f"{ts()}  [http] tiny response ({len(html)} chars), no redirect signal")
            return None

        # ── 4. Normal HTML — parse links ──────────────────────────────────
        extractor = _LinkExtractor(str(resp.url))
        extractor.feed(html)
        download_links, _ = _classify_links(extractor.links)

        if download_links and _depth == 0:
            target = download_links[0]
            gdrive_dl = _gdrive_to_download_url(target)
            if gdrive_dl:
                print(f"{ts()}  [http] Google Drive link → {gdrive_dl}")
                target = gdrive_dl
            print(f"{ts()}  [http] found download link → {target}")
            result = await _httpx_fetch(target, _client=client, _depth=_depth + 1)
            if result is not None:
                result["all_pdf_links"] = download_links
                return result
            # httpx got empty/gated response — log what the server actually said
            # to distinguish "login required" from "JS-gated redirect"
            try:
                gated_resp = await client.get(target)
                gated_body = gated_resp.text
                extractor_g = _LinkExtractor(target)
                extractor_g.feed(gated_body)
                gate_text = extractor_g.text.strip()
                print(f"{ts()}  [http] gate response text: {gate_text!r}")
            except Exception:
                pass
            # Try browser-level HTTP (cookie-aware, no JS execution)
            print(f"{ts()}  [http] escalating to Playwright APIRequest")
            result = await _playwright_api_request(url, target)
            if result is not None:
                return result
            # If session cookies still not enough, try navigating the lightweight
            # component URL directly in Playwright — avoids crashing on the heavy main page
            print(f"{ts()}  [http] escalating to Playwright component navigation")
            result = await _playwright_component_download(target)
            # Only propagate a successful download — auth/error results fall through
            # to the page text that _LinkExtractor already captured below.
            if result is not None and result.get("type") == "pdf":
                return result
            if result is not None and result.get("type") == "error":
                print(f"{ts()}  [http] component download error (not fatal): {result.get('message', '')[:80]}")

        # ── 5. Text extraction ────────────────────────────────────────────
        page_text = _clean_text(extractor.text)
        print(f"{ts()}  [http] extracted text  chars={len(page_text)}")
        if len(page_text) >= _MIN_TEXT_CHARS:
            return {"type": "text", "url": url, "text": page_text}

        return None

    except Exception as exc:
        print(f"{ts()}  [http] failed ({type(exc).__name__}): {exc}")
        return None

    finally:
        if owned_client:
            await client.aclose()


# ── Layer 1.5: Playwright APIRequestContext ───────────────────────────────────
#
# Pure HTTP through the Playwright browser engine — no page rendering, no crash
# risk. Used specifically when a download endpoint is session-gated: we visit
# the origin page first (HTTP only, no JS execution) to collect Set-Cookie
# headers, then replay the download request with those cookies attached.

async def _playwright_api_request(origin_url: str, download_url: str) -> Dict[str, Any] | None:
    """
    Visit `origin_url` via Playwright's APIRequestContext to establish session
    cookies, then fetch `download_url` with those cookies.  No browser window
    or JS engine is involved — this is pure HTTP, identical to a browser's
    XMLHttpRequest/fetch with the same cookie jar.
    """
    ts = lambda: datetime.now().strftime("%H:%M:%S")
    try:
        async with async_playwright() as p:
            # APIRequest is a standalone HTTP client inside the Playwright runtime.
            # It shares cookie storage with any BrowserContext created from the
            # same Playwright instance, but requires no browser launch.
            request = await p.request.new_context(
                base_url=f"{urlparse(origin_url).scheme}://{urlparse(origin_url).netloc}",
                extra_http_headers=_HTTPX_HEADERS,
                ignore_https_errors=True,
            )
            try:
                # Step 1 — prime the cookie jar (mirrors what the browser does
                # when the user visits the page before clicking download).
                print(f"{ts()}  [api-req] prime cookies  {origin_url}")
                seed = await request.get(origin_url)
                print(f"{ts()}  [api-req] seed {seed.status}  cookies established")

                # Step 2 — fetch the download endpoint with the session cookie.
                print(f"{ts()}  [api-req] download  {download_url}")
                resp = await request.get(download_url)
                content_type = resp.headers.get("content-type", "").lower()
                content_disp = resp.headers.get("content-disposition", "").lower()
                body = await resp.body()
                print(f"{ts()}  [api-req] {resp.status}  type={content_type[:50]}  "
                      f"disp={content_disp[:40] or '-'}  bytes={len(body):,}")

                if any(t in content_type for t in _BINARY_TYPES):
                    local_path = _save_bytes(body, download_url, content_type)
                    print(f"{ts()}  [api-req] saved → {local_path}")
                    return {"type": "pdf", "url": origin_url, "pdf_path": local_path}

                if "attachment" in content_disp:
                    local_path = _save_bytes(body, download_url, content_type)
                    print(f"{ts()}  [api-req] saved attachment → {local_path}")
                    return {"type": "pdf", "url": origin_url, "pdf_path": local_path}

                # If we still got HTML, check for redirect in it
                if "html" in content_type:
                    html = body.decode("utf-8", errors="replace")
                    redirect = _sniff_redirect(html, download_url)
                    if redirect:
                        print(f"{ts()}  [api-req] redirect → {redirect}")
                        resp2 = await request.get(redirect)
                        body2 = await resp2.body()
                        ct2 = resp2.headers.get("content-type", "").lower()
                        if any(t in ct2 for t in _BINARY_TYPES) or "attachment" in resp2.headers.get("content-disposition", "").lower():
                            local_path = _save_bytes(body2, redirect, ct2)
                            print(f"{ts()}  [api-req] saved redirect target → {local_path}")
                            return {"type": "pdf", "url": origin_url, "pdf_path": local_path}

                return None
            finally:
                await request.dispose()

    except Exception as exc:
        print(f"{ts()}  [api-req] failed ({type(exc).__name__}): {exc}")
        return None


# ── Layer 1.75: Playwright component navigation ───────────────────────────────
#
# Navigate Playwright directly to the download/component URL — bypasses the
# heavy main page (which crashes) by hitting the lightweight tmpl=component
# endpoint instead.  Sets up a download intercept so if the server streams a
# file we catch it; if it shows a login form we surface a clear auth error.

async def _playwright_component_download(download_url: str) -> Dict[str, Any] | None:
    """
    Navigate to the lightweight download/component URL in Playwright.
    The component page may show file metadata and require clicking a link
    to trigger the actual file stream — we enumerate all links on the page
    and try each one with a download intercept before giving up.
    """
    ts = lambda: datetime.now().strftime("%H:%M:%S")
    try:
        async with async_playwright() as p:
            browser = await p.webkit.launch(headless=True)
            context = await browser.new_context(
                user_agent=_HTTPX_HEADERS["User-Agent"],
                accept_downloads=True,
            )
            page = await context.new_page()
            print(f"{ts()}  [pw-component] navigating → {download_url}")
            await page.goto(download_url, wait_until="domcontentloaded", timeout=20000)

            page_text = (await page.evaluate("document.body.innerText") or "").strip()
            print(f"{ts()}  [pw-component] page says: {page_text[:120]!r}")

            # Auth wall — surface immediately, no point trying further
            lower = page_text.lower()
            if any(k in lower for k in ("log in", "login", "sign in", "access denied",
                                         "not authorized", "permission", "register")):
                await context.close()
                return {
                    "type": "error",
                    "message": f"Authentication required to download. Server: {page_text[:120]}",
                }

            # Collect all links on the component page
            links = await page.evaluate(
                "Array.from(document.querySelectorAll('a[href]')).map(a => a.href)"
            )
            # Prioritise links that look like downloads or PDFs
            download_links, other_links = _classify_links(links)
            ordered = download_links + other_links
            print(f"{ts()}  [pw-component] found {len(ordered)} links to try")

            for href in ordered:
                if any(re.match(p2, href) for p2 in INVALID_URL_PATTERNS):
                    continue
                if href.rstrip("/").endswith("#") or href == download_url:
                    continue
                print(f"{ts()}  [pw-component] trying link → {href}")

                # Step A — direct HTTP request via the browser context's cookie jar.
                # This is the right approach for signed/token URLs (format=raw, get.file, etc.)
                # because it downloads the bytes without navigating the page.
                try:
                    resp = await context.request.get(href, timeout=20000)
                    ct = resp.headers.get("content-type", "").lower()
                    cd = resp.headers.get("content-disposition", "").lower()
                    body = await resp.body()
                    print(f"{ts()}  [pw-component] direct GET → {resp.status}  type={ct[:40]}  bytes={len(body):,}")

                    if any(t in ct for t in _BINARY_TYPES) or "attachment" in cd:
                        dest = os.path.join(DOWNLOADS_DIR, f"doc_{int(time.time())}.pdf")
                        # Try to get filename from Content-Disposition
                        fn_match = re.search(r'filename[^;=\n]*=\s*["\']?([^"\';\n]+)', cd)
                        if fn_match:
                            dest = os.path.join(DOWNLOADS_DIR, fn_match.group(1).strip())
                        with open(dest, "wb") as f:
                            f.write(body)
                        print(f"{ts()}  [pw-component] saved → {dest}")
                        await context.close()
                        return {"type": "pdf", "url": download_url, "pdf_path": dest}
                except Exception as req_err:
                    print(f"{ts()}  [pw-component] direct GET failed: {req_err}")

                # Step B — fallback: page navigation + download intercept
                try:
                    async with page.expect_download(timeout=12000) as dl_info:
                        await page.goto(href, wait_until="domcontentloaded", timeout=12000)
                    dl = await dl_info.value
                    dest = os.path.join(
                        DOWNLOADS_DIR,
                        dl.suggested_filename or f"doc_{int(time.time())}.pdf",
                    )
                    await dl.save_as(dest)
                    print(f"{ts()}  [pw-component] download intercepted → {dest}")
                    await context.close()
                    return {"type": "pdf", "url": download_url, "pdf_path": dest}
                except Exception:
                    try:
                        await page.goto(download_url, wait_until="domcontentloaded", timeout=10000)
                    except Exception:
                        pass

            await context.close()
            return None

    except Exception as exc:
        print(f"{ts()}  [pw-component] failed ({type(exc).__name__}): {exc}")
        return None


# ── Layer 2: Playwright browser helpers ───────────────────────────────────────

async def _initialize_browser_context(playwright_instance: Any, proxy: Optional[dict] = None) -> BrowserContext:
    launch_args: dict = {"headless": True}
    if proxy:
        launch_args["proxy"] = proxy
    # WebKit instead of Chromium — Chromium crashes on macOS ARM with SIGTRAP
    browser = await playwright_instance.webkit.launch(**launch_args)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        locale="en-US",
        viewport={"width": 1920, "height": 1080},
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
        },
    )
    return context


async def _wait_for_page_load(page: Page, timeout: int) -> None:
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
        await page.wait_for_load_state("domcontentloaded", timeout=timeout)
    except Exception:
        pass


async def _download_pdf(page: Page, pdf_url: str, filename: Optional[str] = None) -> Optional[str]:
    try:
        parsed_url = urlparse(pdf_url)
        if not filename:
            filename = os.path.basename(parsed_url.path) or f"downloaded_pdf_{int(time.time())}.pdf"
        local_path = os.path.join(DOWNLOADS_DIR, filename)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": domain,
            "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        response = await page.request.get(pdf_url, headers=headers, timeout=30000)
        if response.ok:
            with open(local_path, "wb") as f:
                f.write(await response.body())
            print(f"{datetime.now().strftime('%H:%M:%S')}  [playwright] PDF saved: {local_path}")
            return local_path
        return None
    except Exception as e:
        print(f"[playwright] PDF download error {pdf_url}: {e}")
        return None


async def _extract_html_content(page: Page) -> str:
    selectors = [
        "main", "article", "section[role=main]", "[role=main]",
        ".main-content", ".mainContent", ".content-main",
        "#content", ".content", ".entry-content", ".post-content", ".body-content",
        "body",
    ]
    best_text = ""
    for selector in selectors:
        try:
            element = await page.locator(selector).first.all()
            if element:
                text_content = await element[0].text_content()
                if text_content and text_content.strip():
                    cleaned = re.sub(r"\s*\n\s*", "\n", text_content).strip()
                    if len(cleaned) > 100:
                        best_text = cleaned
                        break
        except Exception:
            continue

    # Law table fallback: many government portals render legislation in HTML tables.
    # If the best text so far is short (likely a nav dump), check whether the page
    # has substantive tables and prefer their joined text instead.
    if len(best_text) < 1000:
        try:
            table_text = await page.evaluate("""
                () => {
                    const out = [];
                    for (const tbl of document.querySelectorAll('table')) {
                        const rows = tbl.querySelectorAll('tr');
                        if (rows.length < 3) continue;
                        const cells = Array.from(rows).flatMap(r =>
                            Array.from(r.querySelectorAll('td, th'))
                                .map(c => c.innerText.trim())
                                .filter(t => t.length > 15)
                        );
                        if (cells.length >= 5)
                            out.push(cells.join('\\n'));
                    }
                    return out.join('\\n\\n');
                }
            """)
            if table_text and len(table_text.strip()) > len(best_text):
                best_text = re.sub(r"\s*\n\s*", "\n", table_text).strip()
        except Exception:
            pass

    if best_text:
        return best_text

    body = await page.evaluate("document.body.innerText")
    if body:
        return re.sub(r"\s*\n\s*", "\n", body).strip()
    return ""


# ── Public API ─────────────────────────────────────────────────────────────────

async def fetch_legal_content(
    url: str,
    timeout: int = 60000,
    max_retries: int = 3,
    proxy: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Fetch legal content from a URL using a two-layer strategy:

    Layer 1 — httpx (fast, crash-free):
        Plain HTTP GET. Handles direct PDFs, CMS download-endpoint links
        (Joomla, WordPress, Drupal, etc.), and plain-HTML law pages.
        Returns immediately on success.

    Layer 2 — Playwright WebKit (JS-rendered pages):
        Falls back here only when httpx returns insufficient content.
        Crashes ("Page crashed", "Target closed") abort all retries
        immediately — retrying an identical browser against a crashing
        page wastes time and never recovers.
        Only timeout / network errors trigger the retry loop.
    """
    ts = lambda: datetime.now().strftime("%H:%M:%S")

    if any(re.match(pattern, url) for pattern in INVALID_URL_PATTERNS):
        return {"type": "error", "message": f"Invalid URL: {url}"}

    # ── Layer 1: httpx ───────────────────────────────────────────────────────
    print(f"{ts()}  [crawler] layer-1 httpx  {url}")
    result = await _httpx_fetch(url)
    if result is not None:
        print(f"{ts()}  [crawler] layer-1 success  type={result['type']}")
        return result
    print(f"{ts()}  [crawler] layer-1 insufficient — escalating to Playwright")

    # ── Layer 2: Playwright ──────────────────────────────────────────────────
    for attempt in range(1, max_retries + 1):
        async with async_playwright() as p:
            context = None
            try:
                context = await _initialize_browser_context(p, proxy=proxy)
                page = await context.new_page()
                await stealth_async(page)
                page.set_default_timeout(timeout)

                if url.lower().split("?")[0].endswith(".pdf"):
                    print(f"{ts()}  [playwright] direct PDF URL")
                    pdf_path = await _download_pdf(page, url)
                    if pdf_path:
                        return {"type": "pdf", "url": url, "pdf_path": pdf_path}

                print(f"{ts()}  [playwright] attempt {attempt}/{max_retries}  {url}")
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                except Exception as nav_err:
                    err = str(nav_err).lower()
                    if "err_aborted" in err or "navigation was aborted" in err or "timeout" in err:
                        pdf_path = await _download_pdf(page, url)
                        if pdf_path:
                            return {"type": "pdf", "url": url, "pdf_path": pdf_path}
                    raise nav_err

                # Check if the navigated URL is itself a PDF
                is_pdf = page.url.lower().split("?")[0].endswith(".pdf")
                if not is_pdf:
                    try:
                        if await page.evaluate("document.contentType") == "application/pdf":
                            is_pdf = True
                    except Exception:
                        pass
                if is_pdf:
                    pdf_path = await _download_pdf(page, page.url)
                    if pdf_path:
                        return {"type": "pdf", "url": url, "pdf_path": pdf_path}

                await _wait_for_page_load(page, timeout)

                pdf_links = await page.evaluate(
                    "Array.from(document.querySelectorAll('a[href$=\".pdf\"]')).map(a => a.href)"
                )
                valid_pdf_links = [l for l in pdf_links if not any(re.match(p, l) for p in INVALID_URL_PATTERNS)]
                if valid_pdf_links:
                    pdf_path = await _download_pdf(page, urljoin(page.url, valid_pdf_links[0]))
                    if pdf_path:
                        return {"type": "pdf", "url": url, "pdf_path": pdf_path, "all_pdf_links": valid_pdf_links}

                # Google Drive / Docs links (viewer URLs, not direct .pdf hrefs)
                all_links = await page.evaluate(
                    "Array.from(document.querySelectorAll('a[href]')).map(a => a.href)"
                )
                for link in all_links:
                    dl_url = _gdrive_to_download_url(link)
                    if dl_url:
                        print(f"{ts()}  [playwright] Google Drive link → {dl_url}")
                        pdf_path = await _download_pdf(page, dl_url)
                        if pdf_path:
                            return {"type": "pdf", "url": url, "pdf_path": pdf_path}

                content = await _extract_html_content(page)
                if content:
                    return {"type": "text", "url": url, "text": _clean_text(content)}

                return {"type": "error", "message": "No useful content found"}

            except Exception as exc:
                err = str(exc).lower()
                # Browser crash — identical retry will crash again; give up now
                if "crashed" in err or "target closed" in err or "browser has been closed" in err:
                    print(f"{ts()}  [playwright] fatal crash — aborting retries: {exc}")
                    return {
                        "type": "error",
                        "message": f"Browser crashed on this page (layer-1 httpx also returned insufficient content). URL: {url}",
                    }
                print(f"{ts()}  [playwright] attempt {attempt}/{max_retries} failed: {exc}")
                if attempt == max_retries:
                    return {"type": "error", "message": str(exc)}
            finally:
                if context:
                    await context.close()


async def crawl_for_pdpa_pdf(
    start_url: str,
    keyword: str = "Personal Data Protection",
    max_depth: int = 2,
    timeout: int = 60000,
) -> Optional[str]:
    """Recursive PDF search — tries httpx layer on each hop before launching a browser."""
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])

    while queue:
        url, depth = queue.popleft()
        if url in visited or depth > max_depth:
            continue
        visited.add(url)
        print(f"[crawl] depth={depth}  {url}")

        # Try httpx first on every hop
        result = await _httpx_fetch(url)
        if result and result["type"] == "pdf":
            return result["pdf_path"]

        try:
            async with async_playwright() as p:
                context = await _initialize_browser_context(p)
                page = await context.new_page()
                await stealth_async(page)

                await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                await page.wait_for_timeout(5000)

                title = await page.title()
                print(f"[crawl] title: {title}")
                if "Cloudflare" in title or "Just a moment" in title:
                    print("[crawl] Cloudflare challenge — waiting 10s")
                    await page.wait_for_timeout(10000)

                if page.url.lower().endswith(".pdf") and keyword.lower() in page.url.lower():
                    pdf_path = await _download_pdf(page, page.url)
                    if pdf_path:
                        return pdf_path

                links = await page.evaluate(
                    "Array.from(document.querySelectorAll('a')).map(a => ({href: a.href, text: a.innerText}))"
                )
                for link in links:
                    href, text = link["href"], link["text"]
                    if not href or href in visited:
                        continue
                    if href.lower().endswith(".pdf") and (
                        keyword.lower() in href.lower() or keyword.lower() in text.lower()
                    ):
                        print(f"[crawl] hit PDF: {href}")
                        pdf_path = await _download_pdf(page, href)
                        if pdf_path:
                            return pdf_path
                    if urlparse(href).netloc == urlparse(start_url).netloc:
                        queue.append((href, depth + 1))

                await context.close()
        except Exception as exc:
            print(f"[crawl] error at {url}: {exc}")

    return None


if __name__ == "__main__":
    async def main():
        result = await fetch_legal_content(
            "https://prc.cm/en/multimedia/documents/10271-law-n-2024-017-of-23-12-2024-web",
            timeout=60000,
        )
        print(f"type={result['type']}")
        if result["type"] == "pdf":
            print(f"pdf_path={result['pdf_path']}")
        elif result["type"] == "text":
            print(f"text preview: {result['text'][:300]}")
        else:
            print(f"error: {result['message']}")

    asyncio.run(main())
