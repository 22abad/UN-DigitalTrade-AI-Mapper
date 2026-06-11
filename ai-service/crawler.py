from __future__ import annotations
import asyncio
import json
import os
import re
import ssl
import urllib.request
import uuid
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext
from typing import Dict, Optional, Any
from urllib.parse import urljoin, urlparse, quote
from collections import deque

# ── playwright-stealth 跨版本兼容 ──────────────────────────────────
# 1.x API:  from playwright_stealth import stealth_async; await stealth_async(page)
# 2.x API:  from playwright_stealth import Stealth; await Stealth().apply_stealth_async(page)
try:
    from playwright_stealth import Stealth
    _stealth = Stealth()
except ImportError:
    from playwright_stealth import stealth_async
    _stealth = type("_StealthCompat", (), {"stealth_async": staticmethod(stealth_async)})()

# macOS 常有自签名证书问题，统一 SSL context
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE
async def _apply_stealth(page: Page) -> None:
    if hasattr(_stealth, 'apply_stealth_async'):
        await _stealth.apply_stealth_async(page)
    elif hasattr(_stealth, 'stealth_async'):
        await _stealth.stealth_async(page)
    else:
        # fallback: inject basic evasion scripts manually
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
        """)

# 定义下载目录
DOWNLOADS_DIR = "./downloads"
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

# 定义无效 URL 模式
INVALID_URL_PATTERNS = [
    r"javascript:",
    r"mailto:",
    r"tel:",
    r"fax:",
]

async def _initialize_browser_context(playwright_instance: Any, proxy: Optional[dict] = None) -> BrowserContext:
    """
    初始化浏览器上下文，并注入 stealth 插件。
    """
    launch_args = {
        "headless": True,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-position=0,0",
            "--ignore-certifcate-errors",
            "--ignore-certifcate-errors-spki-list",
        ]
    }
    if proxy:
        launch_args["proxy"] = proxy
    browser = await playwright_instance.chromium.launch(**launch_args)
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
    """
    等待页面加载完成，处理 JS 渲染。
    """
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
        await page.wait_for_load_state("domcontentloaded", timeout=timeout)
    except Exception:
        pass

async def _download_file(page: Page, file_url: str, filename: Optional[str] = None) -> Optional[str]:
    """
    下载文件（PDF / Word / 任意类型）到本地。
    """
    try:
        parsed_url = urlparse(file_url)
        filename = f"downloaded_{uuid.uuid4().hex}.bin"
        downloads_root = Path(DOWNLOADS_DIR).resolve()
        local_path = (downloads_root / filename).resolve()
        if downloads_root not in local_path.parents:
            raise ValueError("Invalid download filename")
        
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": domain,
            "Accept": "application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        response = await page.request.get(file_url, headers=headers, timeout=30000)
        if response.ok:
            with open(local_path, "wb") as f:
                f.write(await response.body())
            print(f"文件已下载到: {local_path}")
            return str(local_path)
        return None
    except Exception as e:
        print(f"下载文件时发生错误 {file_url}: {e}")
        return None


async def _read_docx(path: str) -> Optional[str]:
    """用 python-docx 提取 .docx 文本。"""
    try:
        from docx import Document
        doc = Document(path)
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        return text if text.strip() else None
    except Exception as e:
        print(f"读取 docx 失败 {path}: {e}")
        return None

async def _extract_html_content(page: Page) -> str:
    """
    提取 HTML 页面正文。
    """
    selectors = [
        # Site-generic content selectors
        "main", "article", "section[role=main]", "[role=main]",
        ".main-content", ".mainContent", ".content-main",
        "#content", ".content", ".entry-content", ".post-content", ".body-content",
        # SSO / Singapore legislation selectors
        ".legis .body", ".legis", ".prov1Txt", ".pTxt", ".def",
        "body"
    ]
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if await element.count() > 0:
                text_content = await element.text_content()
                if text_content and text_content.strip():
                    cleaned_text = re.sub(r'\s*\n\s*', '\n', text_content).strip()
                    if len(cleaned_text) > 100:
                        return cleaned_text
        except Exception:
            continue
    
    body_content = await page.evaluate("document.body.innerText")
    if body_content:
        return re.sub(r'\s*\n\s*', '\n', body_content).strip()
    return ""


# ── 已知受限站点的替代数据源 Fallback 映射 ─────────────────────────
# 当主 URL 爬取失败时，自动尝试替代来源获取同类内容
KNOWN_ALTERNATIVES: dict[str, list[dict]] = {
    "ratchakitcha.soc.go.th": [
        {
            "source": "ocs.go.th",
            "type": "search_ocs",
            "priority": 1,
            "note": "Thai Council of State law database (no Cloudflare)",
        },
    ],
    "meity.gov.in": [
        {
            "source": "digitalindia.gov.in",
            "type": "web",
            "priority": 1,
            "note": "Digital India portal — alternative to MEITY",
        },
        {
            "source": "mygov.in",
            "type": "web",
            "priority": 2,
            "note": "MyGov India — general government portal",
        },
    ],
    "indiacode.nic.in": [
        {
            "source": "digitalindia.gov.in",
            "type": "web",
            "priority": 1,
            "note": "Digital India portal — alternative to India Code",
        },
    ],
    "india.gov.in": [
        {
            "source": "mygov.in",
            "type": "web",
            "priority": 1,
            "note": "MyGov India — alternative national portal",
        },
    ],
    "mdes.go.th": [
        {
            "source": "ocs.go.th",
            "type": "search_ocs",
            "priority": 1,
            "note": "Thai Council of State law database — alternative to MDES",
        },
    ],
}

# ── 泰国 OCS (Office of the Council of State) 法律库爬取 ─────────────
# OCS 网站 (https://www.ocs.go.th/searchlaw) 不依赖 Cloudflare，
# 可替代被 Cloudflare 保护的 ratchakitcha.soc.go.th（泰王國政府公報）。
# 其 SPA 阅读器 (https://searchlaw.ocs.go.th) 提供泰文 + 英文双语法律全文。

OCS_BASE = "https://www.ocs.go.th"
OCS_SEARCH = f"{OCS_BASE}/searchlaw"
OCS_SEARCH_ENG = f"{OCS_BASE}/searchlaw-law-eng"
OCS_DOC_READER = "https://searchlaw.ocs.go.th/council-of-state/#/public/doc"


async def search_ocs_law(
    query: str,
    search_topic: bool = True,
    max_results: int = 10,
    timeout: int = 30000,
) -> list[dict]:
    """在泰国 OCS 法律库按关键词搜索，返回法律列表。

    Args:
        query: 搜索关键词（泰文或英文）
        search_topic: True=按标题搜, False=按内容搜
        max_results: 最大返回条数
        timeout: 页面加载超时(ms)

    Returns:
        list of {title, year, doc_url, status, published_date, lang}
    """
    results: list[dict] = []
    async with async_playwright() as p:
        context = await _initialize_browser_context(p)
        try:
            page = await context.new_page()
            await _apply_stealth(page)

            encoded_q = quote(query)
            topic_param = "&topic=on" if search_topic else ""
            url = f"{OCS_SEARCH}?q={encoded_q}{topic_param}"
            print(f"[OCS 搜索] {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            await page.wait_for_timeout(4000)

            # OCS 的 SPA 异步加载结果列表，等待结果 DOM 出现
            try:
                await page.wait_for_selector(
                    'a[href*="/public/doc"]',
                    timeout=10000,
                )
            except Exception:
                # 可能无结果或页面结构不同
                body = await page.evaluate("document.body?.innerText || ''")
                if "ไม่พบข้อมูล" in body or "No results" in body:
                    print("[OCS 搜索] 未找到结果")
                    return []
                # fallback: 试着多等一会
                await page.wait_for_timeout(5000)

            # 提取所有法律文档链接
            links = await page.locator('a[href*="/public/doc"]').all()
            visited_ids: set[str] = set()
            for link in links:
                href = (await link.get_attribute("href")) or ""
                text = (await link.inner_text()).strip()
                if not text or not href:
                    continue
                # 每个 doc id 只取第一个标题
                doc_id = href.split("/public/doc/")[-1].split("?")[0]
                if doc_id in visited_ids:
                    continue
                visited_ids.add(doc_id)
                # 拼接完整 URL
                full_url = f"{OCS_DOC_READER}/{doc_id}"

                results.append({
                    "title": text,
                    "doc_id": doc_id,
                    "doc_url": full_url,
                    "lang": "th",
                    "source": "ocs.go.th",
                })
                if len(results) >= max_results:
                    break

            print(f"[OCS 搜索] 找到 {len(results)} 条结果")
            return results

        finally:
            await context.close()


async def fetch_ocs_law_document(
    doc_id: str,
    lang: str = "th",
    timeout: int = 30000,
) -> Optional[str]:
    """从 OCS SPA 阅读器提取法律全文（泰文或英文）。

    OCS 的 document viewer 是 React SPA，需要用 Playwright 渲染后
    才能获取全文。支持 ?lang=en 参数切换到英文版。

    Args:
        doc_id: OCS 文档 ID（从 search_ocs_law 返回的 doc_id）
        lang: "th"=泰文, "en"=英文
        timeout: 页面加载 + 渲染超时(ms)

    Returns:
        法律全文文本，失败返回 None
    """
    lang_param = "?lang=en" if lang == "en" else ""
    url = f"{OCS_DOC_READER}/{doc_id}{lang_param}"

    async with async_playwright() as p:
        context = await _initialize_browser_context(p)
        try:
            page = await context.new_page()
            await _apply_stealth(page)

            print(f"[OCS 文档] 正在加载: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            # SPA 需要额外时间渲染
            await page.wait_for_timeout(5000)

            # 检查页面是否成功加载
            title = await page.title()
            if "404" in title:
                print(f"[OCS 文档] 404 — doc_id 无效: {doc_id}")
                return None

            # 如果请求英文版，尝试点击 "Latest Translation" 按钮加载翻译内容
            if lang == "en":
                try:
                    trans_btn = page.locator(
                        'button:has-text("Translation"),'
                        'a:has-text("Latest Translation"),'
                        '[role="tab"]:has-text("Translation")'
                    ).first
                    if await trans_btn.count() > 0:
                        await trans_btn.click()
                        print("[OCS 文档] 点击了 Translation 按钮")
                        await page.wait_for_timeout(3000)
                except Exception:
                    pass

            # 获取全文 — 使用 body.innerText 获取所有可见文本
            body = await page.evaluate("document.body?.innerText || ''")
            if len(body) < 200:
                # 可能内容在某个深层容器里，等更久再试一次
                await page.wait_for_timeout(3000)
                body = await page.evaluate("document.body?.innerText || ''")

            if len(body) < 100:
                print(f"[OCS 文档] 提取的文本过短 ({len(body)} chars)，可能被拦截")
                return None

            print(f"[OCS 文档] 成功提取 {len(body)} 字符 ({lang})")
            return body

        finally:
            await context.close()


async def fetch_thai_law_by_keyword(
    query: str,
    lang: str = "th",
    timeout: int = 30000,
) -> Dict[str, Any]:
    """一站式泰国法律获取：关键词搜索 → 选取第一条 → 拉取全文。

    这是推荐给上层 /api/extract 调用的高级接口。
    自动处理：OCS 搜索 → SPA 渲染 → 全文提取。

    Args:
        query: 法律名称关键词（泰文）
        lang: "th"=泰文, "en"=英文
        timeout: 超时(ms)

    Returns:
        与 fetch_legal_content 同结构的 dict
    """
    results = await search_ocs_law(query, timeout=timeout)
    if not results:
        return {
            "type": "error",
            "message": f"OCS 未找到与 '{query}' 相关的法律",
        }

    best = results[0]
    text = await fetch_ocs_law_document(best["doc_id"], lang=lang, timeout=timeout)
    if not text:
        return {
            "type": "error",
            "message": f"OCS 文档提取失败: {best['doc_url']}",
        }

    return {
        "type": "text",
        "url": best["doc_url"],
        "text": text,
        "metadata": {
            "title": best["title"],
            "doc_id": best["doc_id"],
            "lang": lang,
            "source": "ocs.go.th",
        },
    }



# ── Wayback Machine 回溯取证 ────────────────────────────────────────
# 当源站被 WAF/Cloudflare 阻断时，通过 Internet Archive 获取历史快照。
# 三层策略：
#   1. CDX API 查询最近快照
#   2. 获取快照内容
#   3. 返回带时间戳的归档元数据

WAYBACK_CDX = "https://web.archive.org/cdx/search/cdx"
WAYBACK_AVAIL = "https://archive.org/wayback/available"
WAYBACK_WEB = "https://web.archive.org/web"


async def fetch_wayback_closest(url: str, max_retries: int = 2) -> Optional[dict]:
    """通过 Wayback Machine CDX API 查找最近的可用快照。"""
    _opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_SSL_CTX))
    _opener.addheaders = [("User-Agent", "Mozilla/5.0 (compatible; RDTII/1.0)")]

    for attempt in range(max_retries):
        try:
            def _fetch_avail():
                avail_url = f"{WAYBACK_AVAIL}?url={url}"
                resp = _opener.open(avail_url, timeout=15)
                return json.loads(resp.read())

            data = await asyncio.to_thread(_fetch_avail)
            snapshots = data.get("archived_snapshots", {})
            closest = snapshots.get("closest", {})
            if closest.get("available") and closest.get("url"):
                ts = closest.get("timestamp", "")
                archive_url = closest["url"]
                print(f"[Wayback] 快照: {ts} → {archive_url}")
                return {
                    "timestamp": ts.replace("-", "").replace(":", "").replace(" ", ""),
                    "archive_url": archive_url,
                    "statuscode": "200",
                    "source": "wayback_availability",
                }

            # CDX fallback
            def _fetch_cdx():
                cdx_url = f"{WAYBACK_CDX}?url={url}&output=json&limit=5&fl=timestamp,original,statuscode&sort=reverse"
                resp = _opener.open(cdx_url, timeout=15)
                return json.loads(resp.read())

            rows = await asyncio.to_thread(_fetch_cdx)
            if len(rows) > 1:
                for row in rows[1:]:
                    ts, orig, sc = row[0], row[1], row[2] if len(row) > 2 else "200"
                    if sc in ("200", "302"):
                        archive_url = f"{WAYBACK_WEB}/{ts}/{orig}"
                        print(f"[Wayback CDX] 快照: {ts} ({sc})")
                        return {
                            "timestamp": ts,
                            "archive_url": archive_url,
                            "statuscode": sc,
                            "source": "wayback_cdx",
                        }
        except Exception as e:
            print(f"[Wayback] 查询失败 (attempt {attempt+1}): {e}")
            await asyncio.sleep(1)

    return None


async def fetch_wayback_content(url: str, timeout: int = 30000) -> Dict[str, Any]:
    """从 Wayback Machine 获取法律内容。

    三部曲：
        1. CDX → 找最近快照
        2. 获取快照 HTML/文本
        3. 返回内容 + 归档元数据

    Returns:
        同 fetch_legal_content 格式，附加 archive_timestamp 字段
    """
    snapshot = await fetch_wayback_closest(url)
    if not snapshot:
        return {"type": "error", "message": "Wayback Machine 中未找到该 URL 的快照"}

    archive_url = snapshot["archive_url"]
    print(f"[Wayback] 正在获取快照内容: {archive_url}")

    # 尝试直接用 HTTP 获取文本（避免启动 Playwright）
    import html as html_mod

    _opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_SSL_CTX))
    _opener.addheaders = [
        ("User-Agent", "Mozilla/5.0 (compatible; RDTII/1.0; +https://github.com/22abad/UN-DigitalTrade-AI-Mapper)"),
    ]

    try:
        def _fetch():
            resp = _opener.open(archive_url, timeout=int(timeout / 1000))
            return resp.read().decode("utf-8", errors="replace")

        raw_html = await asyncio.to_thread(_fetch)
        text = re.sub(r'<[^>]+>', ' ', raw_html)
        text = html_mod.unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 200:
            # Detect garbage (Wayback wrapper JS, block pages)
            garbage_signals = ["window.addEventListener", "archive_analytics",
                               "webpackJsonp", "performing security"]
            if any(s in text[:500].lower() for s in garbage_signals):
                print(f"[Wayback] HTTP 获取成功但内容为 Wayback 包装页面 ({len(text)} 字符)")
            else:
                print(f"[Wayback] HTTP 获取成功: {len(text)} 字符 (归档于 {snapshot['timestamp']})")
                return {
                    "type": "text",
                    "url": archive_url,
                    "original_url": url,
                    "text": text,
                    "metadata": {
                        "source": "wayback_machine",
                        "archive_timestamp": snapshot["timestamp"],
                        "archive_url": archive_url,
                    },
                }
    except Exception as e:
        print(f"[Wayback] HTTP 获取失败: {e}")

    # HTTP 失败 → 用 Playwright 渲染（JS 站点）
    print(f"[Wayback] HTTP 不满足，启动 Playwright 渲染快照...")
    return await _fetch_wayback_with_playwright(archive_url, snapshot)


async def _fetch_wayback_with_playwright(archive_url: str, snapshot: dict) -> Dict[str, Any]:
    """用 Playwright 渲染 Wayback 快照页面。"""
    async with async_playwright() as p:
        context = await _initialize_browser_context(p)
        try:
            page = await context.new_page()
            await _apply_stealth(page)

            await page.goto(archive_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            body = await page.evaluate("document.body?.innerText || ''")
            if len(body) > 200:
                print(f"[Wayback Playwright] 成功: {len(body)} 字符")
                return {
                    "type": "text",
                    "url": archive_url,
                    "original_url": snapshot.get("original", archive_url),
                    "text": body,
                    "metadata": {
                        "source": "wayback_machine",
                        "archive_timestamp": snapshot["timestamp"],
                        "archive_url": archive_url,
                    },
                }
            return {"type": "error", "message": f"Wayback 快照无内容 ({len(body)} chars)"}
        finally:
            await context.close()


async def fetch_google_cache(url: str) -> Optional[str]:
    """Google Cache 快速取证——轻量级，无需 Playwright。

    注意：Google Cache 可能返回旧版或不可用。
    """
    import html as html_mod

    _opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_SSL_CTX))
    _opener.addheaders = [("User-Agent", "Mozilla/5.0 (compatible; RDTII/1.0)")]

    cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}"
    try:
        def _fetch():
            resp = _opener.open(cache_url, timeout=15)
            return resp.read().decode("utf-8", errors="replace")
        text = await asyncio.to_thread(_fetch)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = html_mod.unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 200:
            return text
    except Exception as e:
        print(f"[Google Cache] 失败: {e}")
    return None


# ── 法律时间戳核实 ──────────────────────────────────────────────────
# 三重验证 LLM 声称的 `last_update` 日期：
#   1. Wayback Machine CDX — 查该 URL 历史变更
#   2. HTTP Last-Modified 头
#   3. 多个来源交叉比对

async def verify_law_timeline(
    url: str,
    llm_claimed_date: str = "",
) -> dict:
    """核实法律文档的版本时间戳。

    Args:
        url: 法律文档的 URL
        llm_claimed_date: LLM 提取的 last_update 字符串

    Returns:
        {
            "verified": bool,          # 是否通过验证
            "sources_checked": int,    # 核实的来源数
            "best_date": str,          # 最佳确认日期
            "verification_log": str,   # 核验过程描述（用于 audit trail）
            "source_details": [        # 每个来源的详细结果
                {"source": str, "date": str, "status": str}
            ]
        }
    """
    from datetime import datetime

    source_details: list[dict] = []

    # 1. Wayback Machine CDX — 查看历史变更
    snapshot = await fetch_wayback_closest(url)
    wb_date = ""
    if snapshot:
        ts = snapshot["timestamp"]
        if len(ts) >= 8:
            try:
                wb_date = datetime.strptime(ts[:8], "%Y%m%d").strftime("%Y-%m-%d")
            except ValueError:
                wb_date = ts[:8]
        source_details.append({
            "source": "wayback_machine",
            "date": wb_date,
            "status": "found" if wb_date else "no_date",
        })

    # 2. HTTP Last-Modified 头
    http_date = ""
    _opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_SSL_CTX))
    try:
        def _fetch_head():
            req = urllib.request.Request(url, method="HEAD")
            resp = _opener.open(req, timeout=10)
            return resp.headers.get("Last-Modified", "")
        http_date_str = await asyncio.to_thread(_fetch_head)
        if http_date_str:
            try:
                parsed = datetime.strptime(http_date_str, "%a, %d %b %Y %H:%M:%S %Z")
                http_date = parsed.strftime("%Y-%m-%d")
            except ValueError:
                http_date = http_date_str
        source_details.append({
            "source": "http_last_modified",
            "date": http_date or "unavailable",
            "status": "found" if http_date else "header_missing",
        })
    except Exception as e:
        source_details.append({
            "source": "http_last_modified",
            "date": "",
            "status": f"error: {str(e)[:60]}",
        })

    # 3. 交叉比较
    verified = False
    best_date = llm_claimed_date
    verification_log_parts: list[str] = []

    all_dates = [d for d in [llm_claimed_date, wb_date, http_date] if d]
    unique_dates = set(all_dates)

    if llm_claimed_date:
        verification_log_parts.append(f"LLM 声称: {llm_claimed_date}")
    if wb_date:
        verification_log_parts.append(f"Wayback 归档: {wb_date}")
    if http_date:
        verification_log_parts.append(f"HTTP 头: {http_date}")

    if len(unique_dates) == 1 and len(all_dates) >= 2:
        verified = True
        verification_log_parts.append("✅ 所有来源日期一致")
    elif llm_claimed_date and wb_date and llm_claimed_date != wb_date:
        verification_log_parts.append(f"⚠️ LLM 声称 ({llm_claimed_date}) 与 Wayback ({wb_date}) 不一致")
        # 偏向信任 Wayback Machine
        best_date = wb_date
    elif llm_claimed_date and http_date and llm_claimed_date != http_date:
        verification_log_parts.append(f"⚠️ LLM 声称 ({llm_claimed_date}) 与 HTTP 头 ({http_date}) 不一致")
        best_date = http_date

    log_str = "; ".join(verification_log_parts)

    return {
        "verified": verified,
        "sources_checked": len(source_details),
        "best_date": best_date,
        "verification_log": log_str,
        "source_details": source_details,
    }


async def _precheck_url(url: str) -> str | None:
    """Check if a URL is dead before launching Playwright.

    Returns an error description string if the URL is dead
    (HTTP 404/410, DNS failure), or None if it's alive or uncertain.
    """
    import urllib.error
    _opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_SSL_CTX))
    _opener.addheaders = [("User-Agent", "Mozilla/5.0 (compatible; RDTII/1.0)")]

    def _check_sync() -> str | None:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with _opener.open(req, timeout=10) as resp:
                if resp.status in (404, 410):
                    return f"HTTP {resp.status}"
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return f"HTTP {e.code}"
            return None
        except urllib.error.URLError as e:
            reason = str(e.reason)
            if any(s in reason for s in [
                "Name or service not known", "nodename nor servname",
                "Temporary failure", "No address associated",
            ]):
                return f"DNS failure: {reason}"
            return None
        except Exception:
            return None
        return None

    try:
        return await asyncio.to_thread(_check_sync)
    except Exception:
        return None


# ── HTTP(S) direct fetch fallback ───────────────────────────────────────────
# Some government sites (e.g. sso.agc.gov.sg) use CDN WAFs (CloudFront)
# that block Playwright while allowing simple HTTP clients like httpx.
# This fallback tries plain HTTP before giving up.


async def _try_http_fallback(url: str, timeout: int = 30000) -> dict | None:
    """Fetch a URL via plain HTTP(S) — bypasses Playwright for WAF-blocked SSR sites.

    Tries two strategies:
      1. SSO-specific: look for the .legis container (Singapore legislation)
      2. Generic: extract <body> content

    Returns the same dict format as fetch_legal_content on success, or None.
    """
    import httpx

    print(f"[HTTP Fallback] 直接 HTTP 获取: {url}")
    try:
        client = httpx.Client(
            verify=False,
            timeout=httpx.Timeout(timeout / 1000),
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        )
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text
        if len(html) < 1000:
            print(f"[HTTP Fallback] 内容过短 ({len(html)} 字符)，跳过")
            return None

        import re as _re
        import html as _html

        # Strategy 1: SSO-specific .legis container
        raw = None
        body_match = _re.search(
            r'<div\s+class="legis[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>',
            html, _re.DOTALL | _re.IGNORECASE,
        )
        if body_match:
            raw = body_match.group(1)

        # Strategy 2: generic <body> fallback
        if not raw:
            body_match = _re.search(r'<body[^>]*>(.*?)</body>', html, _re.DOTALL | _re.IGNORECASE)
            raw = body_match.group(1) if body_match else html

        text = _re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=_re.DOTALL | _re.IGNORECASE)
        text = _re.sub(r'<style[^>]*>.*?</style>', '', text, flags=_re.DOTALL | _re.IGNORECASE)
        text = _re.sub(r'<[^>]+>', ' ', text)
        text = _html.unescape(text)
        text = _re.sub(r'\s+', ' ', text).strip()

        if len(text) > 500:
            print(f"[HTTP Fallback] 成功！{len(text)} 字符")
            return {
                "type": "text",
                "url": url,
                "text": text,
                "metadata": {"source": "http_fallback"},
            }

        # ── SSO-specific: HTML too short (paged content), try PDF version ──
        pdf_match = _re.search(
            r'href=\"([^\"]+ViewType=Pdf[^\"]*)\"', html, _re.IGNORECASE
        )
        if not pdf_match:
            # Try appending ViewType=Pdf directly
            pdf_candidate = url + ("&" if "?" in url else "?") + "ViewType=Pdf"
        else:
            pdf_candidate = _re.sub(r'&amp;', '&', pdf_match.group(1))
            if pdf_candidate.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(url)
                pdf_candidate = f"{parsed.scheme}://{parsed.netloc}{pdf_candidate}"

        print(f"[HTTP Fallback] HTML 文本过短，尝试 PDF 版本: {pdf_candidate}")
        try:
            pdf_resp = client.get(pdf_candidate)
            pdf_resp.raise_for_status()
            if pdf_resp.headers.get("content-type", "").startswith("application/pdf"):
                import tempfile, os, uuid
                tmp = Path(tempfile.gettempdir()) / f"sso_{uuid.uuid4().hex}.pdf"
                tmp.write_bytes(pdf_resp.content)
                from pdf_reader import read_pdf
                pdf_result = read_pdf(str(tmp))
                pdf_text = "\n".join(pdf_result.pages)
                os.unlink(str(tmp))
                if len(pdf_text) > 500:
                    print(f"[HTTP Fallback PDF] 成功！{len(pdf_text)} 字符")
                    return {
                        "type": "text",
                        "url": url,
                        "text": pdf_text,
                        "metadata": {"source": "http_fallback_pdf", "original_format": "pdf"},
                    }
        except Exception as pdf_e:
            print(f"[HTTP Fallback PDF] 失败: {pdf_e}")

        print(f"[HTTP Fallback] 提取文本过短 ({len(text)} 字符)")
    except Exception as e:
        print(f"[HTTP Fallback] 失败: {e}")
    return None


async def _try_wayback_fallback(url: str, context: str = "dead link") -> dict | None:
    """Try Wayback Machine fallback and log the attempt."""
    print(f"[Dead Link] {url} — {context}，尝试 Internet Archive 归档...")
    wb_result = await fetch_wayback_content(url)
    if wb_result["type"] == "text":
        print(f"[Wayback] 成功！归档于 {wb_result.get('metadata', {}).get('archive_timestamp', '?')}")
        return wb_result
    print(f"[Wayback] 未找到 '{url}' 的快照")
    return None


async def fetch_legal_content(url: str, timeout: int = 60000, max_retries: int = 3, proxy: Optional[dict] = None) -> Dict[str, Any]:
    """
    抓取法律内容（HTML 文本或 PDF）。
    """
    if any(re.match(pattern, url) for pattern in INVALID_URL_PATTERNS):
        return {"type": "error", "message": f"URL 无效: {url}"}

    # ── Pre-check: dead link detection before launching Playwright ──
    dead_reason = await _precheck_url(url)
    if dead_reason:
        wb = await _try_wayback_fallback(url, dead_reason)
        if wb:
            return wb
        return {"type": "error", "message": f"Dead link ({dead_reason}), no Wayback snapshot"}

    # ── Direct HTTP probe (SSR sites like SSO block Playwright but serve
    # full content via plain HTTP — try it first to avoid Playwright overhead).
    http_result = await _try_http_fallback(url, timeout)
    if http_result:
        return http_result

    for attempt in range(1, max_retries + 1):
        async with async_playwright() as p:
            context = None
            try:
                context = await _initialize_browser_context(p, proxy=proxy)
                page = await context.new_page()
                await _apply_stealth(page)
                page.set_default_timeout(timeout)
                
                # Task: Check if direct PDF / Word URL to avoid ERR_ABORTED
                path_lower = url.lower().split('?')[0]
                if path_lower.endswith(".pdf"):
                    print(f"检测到直接 PDF URL: {url}")
                    pdf_path = await _download_file(page, url)
                    if pdf_path:
                        return {"type": "pdf", "url": url, "pdf_path": pdf_path}

                if path_lower.endswith(".docx") or path_lower.endswith(".doc"):
                    print(f"检测到 Word 文档: {url}")
                    doc_path = await _download_file(page, url)
                    if doc_path:
                        if doc_path.endswith(".docx"):
                            doc_text = await _read_docx(doc_path)
                        else:
                            doc_text = None
                        if doc_text:
                            return {"type": "docx", "url": url, "text": doc_text}
                        return {"type": "error", "message": f"Word 文档解析失败: {url}"}

                print(f"正在访问: {url}")
                try:
                    # Increase timeout and use wait_until="domcontentloaded" for potentially slow gov sites
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                    # Inline dead-link detection — catch 404/410 from Playwright response
                    if response and response.status in (404, 410):
                        print(f"[Dead Link] Playwright 返回 HTTP {response.status} — 跳过重试，尝试 Wayback")
                        wb = await _try_wayback_fallback(url, f"HTTP {response.status}")
                        if wb:
                            return wb
                        return {"type": "error", "message": f"Dead link (HTTP {response.status}), no Wayback snapshot"}
                except Exception as e:
                    # If aborted but it's a PDF, we might still be able to download it
                    error_str = str(e).lower()
                    if "err_aborted" in error_str or "navigation was aborted" in error_str or "timeout" in error_str:
                        print(f"尝试中断/超时修复，直接尝试下载: {url}")
                        pdf_path = await _download_file(page, url)
                        if pdf_path:
                            return {"type": "pdf", "url": url, "pdf_path": pdf_path}
                    raise e
                
                # Check current URL or content-type for PDF | 检查当前 URL 或内容类型是否为 PDF
                is_pdf = url.lower().split('?')[0].endswith(".pdf") or page.url.lower().split('?')[0].endswith(".pdf")
                if not is_pdf:
                    # Sometimes the URL doesn't end in .pdf but the content is PDF
                    try:
                        content_type = await page.evaluate("document.contentType")
                        if content_type == "application/pdf":
                            is_pdf = True
                    except: pass

                if is_pdf:
                    pdf_path = await _download_file(page, page.url)
                    if pdf_path:
                        return {"type": "pdf", "url": url, "pdf_path": pdf_path}
                
                await _wait_for_page_load(page, timeout)
                
                # 检测页面内的 PDF 链接
                pdf_links = await page.evaluate('Array.from(document.querySelectorAll(\'a[href$=".pdf"]\')).map(a => a.href)')
                valid_pdf_links = [l for l in pdf_links if not any(re.match(p, l) for p in INVALID_URL_PATTERNS)]
                
                if valid_pdf_links:
                    pdf_url = urljoin(page.url, valid_pdf_links[0])
                    pdf_path = await _download_file(page, pdf_url)
                    if pdf_path:
                        return {"type": "pdf", "url": url, "pdf_path": pdf_path}

                content = await _extract_html_content(page)
                if content:
                    # Detect common anti-bot / block / challenge pages
                    # Use content-length heuristic + known block page signatures
                    block_indicators = [
                        "access denied", "just a moment",
                        "please wait while we verify",
                        "performing security",
                        "รอสักครู่", "กำลังทำการตรวจสอบความปลอดภัย",
                        "cloudflare ray id", "ddos protection",
                        "generated by cloudfront", "request could not be satisfied",
                        "the request could not be satisfied",
                    ]
                    low = content.lower().strip()
                    # Only flag when content is short (< 5KB) AND contains block language
                    if len(content) < 5000 and any(ind in low for ind in block_indicators):
                        print(f"[警告] 检测到反爬拦截 ({content[:60].strip()}...)")
                        # Try HTTP fallback before raising
                        http_result = await _try_http_fallback(url, timeout)
                        if http_result:
                            return http_result
                        raise Exception(f"Blocked by anti-bot protection")
                    return {"type": "text", "url": url, "text": content}
                
                return {"type": "error", "message": "未找到有效内容"}
            except Exception as e:
                print(f"[重试 {attempt}/{max_retries}] 错误: {e}")
                if attempt == max_retries:
                    # ── 所有重试失败 → 尝试 KNOWN_ALTERNATIVES ──────────
                    parsed = urlparse(url)
                    domain = parsed.netloc.replace("www.", "")
                    alternatives = KNOWN_ALTERNATIVES.get(domain, [])
                    if alternatives:
                        print(f"[Fallback] {domain} 有 {len(alternatives)} 个替代来源，尝试中...")
                        for alt in alternatives:
                            if alt["type"] == "search_ocs":
                                # ratchakitcha → OCS 替代：提取 URL 中有意义的搜索词
                                # URL 格式: /search-result?keyword=xxx 或 /documents/xxx.pdf
                                parsed_url = urlparse(url)
                                
                                # 尝试从 ratchakitcha URL 路径中提取法条关键词
                                path_parts = [p for p in parsed_url.path.split("/") if p]
                                if "search" in "".join(path_parts).lower():
                                    search_query = dict(p.split("=") for p in parsed_url.query.split("&") if "=" in p).get("keyword", "")
                                else:
                                    search_query = ""

                                # 如果 URL 中无法提取有意义的关键词，用文件名部分启发式推断
                                if not search_query or len(search_query) < 3:
                                    last_part = path_parts[-1] if path_parts else ""
                                    if "pdpa" in last_part.lower():
                                        search_query = "คุ้มครองข้อมูลส่วนบุคคล"
                                    elif "procurement" in last_part.lower() or "จัดซื้อ" in last_part.lower():
                                        search_query = "การจัดซื้อจัดจ้าง"
                                    elif "digital" in last_part.lower() or "ดิจิทัล" in last_part:
                                        search_query = "ดิจิทัลเพื่อเศรษฐกิจ"
                                    else:
                                        search_query = ""

                                if search_query:
                                    print(f"[Fallback] OCS 搜索关键词: '{search_query}'")
                                    result = await fetch_thai_law_by_keyword(search_query, timeout=timeout)
                                    if result["type"] == "text":
                                        return result
                                else:
                                    print("[Fallback] 无法自动推断 OCS 搜索关键词。")
                                    print("[Fallback] ratchakitcha.soc.go.th 可能被 Cloudflare 阻断或 URL 信息不足。")
                                    print("建议: 直接使用 fetch_thai_law_by_keyword('ชื่อกฎหมายภาษาไทย') 从 OCS 获取。")
                            elif alt["type"] == "web":
                                alt_url = f"https://www.{alt['source']}/"
                                print(f"[Fallback] 尝试替代网站: {alt_url}")
                                try:
                                    return await fetch_legal_content(alt_url, timeout=timeout, max_retries=1)
                                except Exception as alt_e:
                                    print(f"[Fallback] 替代来源失败: {alt_e}")
                                    continue

                    # ── HTTP Fallback (WAF-blocked SSR sites) ───────────
                    http_result = await _try_http_fallback(url, timeout)
                    if http_result:
                        return http_result

                    # ── Wayback Machine 兜底 ──
                    print(f"[Wayback Fallback] 尝试从 Internet Archive 获取 '{url}' 的快照...")
                    wb_result = await fetch_wayback_content(url)
                    if wb_result["type"] == "text":
                        return wb_result

                    # ── 最后尝试 Google Cache ──
                    print(f"[Google Cache Fallback] 尝试 Google Cache...")
                    gc_text = await fetch_google_cache(url)
                    if gc_text:
                        return {
                            "type": "text",
                            "url": url,
                            "text": gc_text,
                            "metadata": {"source": "google_cache"},
                        }

                    return {"type": "error", "message": str(e)}
            finally:
                if context:
                    await context.close()

async def crawl_for_pdpa_pdf(start_url: str, keyword: str = "Personal Data Protection", max_depth: int = 2, timeout: int = 60000) -> Optional[str]:
    """
    递归搜索 PDF。
    """
    visited = set()
    queue = deque([(start_url, 0)])
    
    while queue:
        url, depth = queue.popleft()
        if url in visited or depth > max_depth:
            continue
        visited.add(url)
        
        print(f"[递归] 访问: {url} (深度{depth})")
        try:
            async with async_playwright() as p:
                context = await _initialize_browser_context(p)
                page = await context.new_page()
                await _apply_stealth(page)
                
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                await page.wait_for_timeout(5000) # 等待 Cloudflare 或 JS 挑战
                
                title = await page.title()
                print(f"[页面标题] {title}")
                
                if "Cloudflare" in title or "Just a moment" in title:
                    print("[警告] 遇到 Cloudflare 挑战，尝试等待更多时间...")
                    await page.wait_for_timeout(10000)
                    title = await page.title()
                    print(f"[重新检查标题] {title}")
                if page.url.lower().endswith('.pdf') and keyword.lower() in page.url.lower():
                    pdf_path = await _download_file(page, page.url)
                    if pdf_path: return pdf_path
                
                # 2. 查找页面内所有链接
                links = await page.evaluate('Array.from(document.querySelectorAll("a")).map(a => ({href: a.href, text: a.innerText}))')
                
                for link in links:
                    href = link['href']
                    text = link['text']
                    
                    if not href or href in visited:
                        continue
                        
                    # 如果是 PDF 且包含关键词
                    if href.lower().endswith('.pdf') and (keyword.lower() in href.lower() or keyword.lower() in text.lower()):
                        print(f"[命中] 发现 PDF: {href}")
                        pdf_path = await _download_file(page, href)
                        if pdf_path: return pdf_path
                    
                    # 如果是同站链接，加入队列
                    if urlparse(href).netloc == urlparse(start_url).netloc:
                        queue.append((href, depth + 1))
                
                await context.close()
        except Exception as e:
            print(f"[错误] {url}: {e}")
            
    return None

if __name__ == "__main__":
    async def main():
        print("=" * 60)
        print("RDTII Crawler — Test Suite")
        print("=" * 60)

        # Test 1: 泰国 OCS 法律库搜索 + 全文提取
        print("\n\n>>> 测试 1: 泰国 OCS — 搜索 + 全文提取 <<<")
        SEARCH_TERM = "การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ"
        print(f"搜索: '{SEARCH_TERM}'")
        
        result = await fetch_thai_law_by_keyword(SEARCH_TERM)
        if result["type"] == "text":
            text = result["text"]
            meta = result.get("metadata", {})
            print(f"✅ 成功！标题: {meta.get('title', 'N/A')}")
            print(f"   长度: {len(text)} 字符")
            print(f"   来源: {meta.get('source', 'N/A')}")
            for kw in ["ข้อมูล", "อิเล็กทรอนิก", "ดิจิทัล", "ระบบสารสนเทศ"]:
                count = text.count(kw)
                if count > 0:
                    print(f"   • '{kw}' 出现 {count} 次")
        else:
            print(f"❌ 失败: {result.get('message', '')[:200]}")

        # Test 2: Wayback Machine 回溯取证
        print("\n\n>>> 测试 2: Wayback Machine 回溯取证 <<<")
        try:
            wb_result = await fetch_wayback_content("https://www.meity.gov.in")
            wb_type = wb_result.get("type", "?")
            wb_meta = wb_result.get("metadata", {})
            wb_ts = wb_meta.get("archive_timestamp", "N/A")
            wb_len = len(wb_result.get("text", "")) if wb_result.get("text") else 0
            print(f"   状态: {wb_type}")
            print(f"   快照时间: {wb_ts}")
            if wb_len > 0:
                print(f"   内容长度: {wb_len} 字符 ✅")
            else:
                print(f"   ⚠️  无内容 (或被屏蔽)")
        except Exception as e:
            print(f"   错误: {type(e).__name__}: {str(e)[:100]}")

        # Test 3: 时间戳核实
        print("\n\n>>> 测试 3: 时间戳核实 (三重验证) <<<")
        try:
            tv = await verify_law_timeline(
                "https://www.digitalindia.gov.in",
                llm_claimed_date="2024-01-15",
            )
            print(f"   验证: {'✅ 通过' if tv.get('verified') else '⚠️ 未完全一致'}")
            print(f"   来源数: {tv.get('sources_checked', 0)}")
            print(f"   最佳日期: {tv.get('best_date', 'N/A')}")
            print(f"   日志: {tv.get('verification_log', '')[:200]}")
        except Exception as e:
            print(f"   错误: {type(e).__name__}: {str(e)[:100]}")

        # Test 4: ratchakitcha URL → 阻断检测 → Wayback Fallback
        print("\n\n>>> 测试 4: ratchakitcha URL → 阻断检测 + Wayback Fallback <<<")
        fallback_result = await fetch_legal_content(
            "https://ratchakitcha.soc.go.th/search-result",
            timeout=15000,
        )
        status = fallback_result.get("type", "?")
        meta = fallback_result.get("metadata", {})
        if meta.get("source") == "wayback_machine":
            print(f"✅ Wayback Fallback 成功！(归档于 {meta.get('archive_timestamp', '?')})")
        elif status == "error" and "Blocked" in str(fallback_result.get("message", "")):
            print("⚠️ 阻断检测正确触发，Wayback 可能也无此 URL 的快照")
        else:
            print(f"结果: {status} — {str(fallback_result.get('message', ''))[:100]}")

        # Test 5: 已知可访问站点
        print("\n\n>>> 测试 5: trai.gov.in (印度电信管理局) <<<")
        india_result = await fetch_legal_content(
            "https://www.trai.gov.in",
            timeout=30000,
            max_retries=1,
        )
        if india_result.get("type") == "text":
            print(f"✅ 成功！获取到 {len(india_result['text'])} 字符")
        else:
            print(f"结果: {india_result.get('type')} — {str(india_result.get('message', ''))[:100]}")
        
        print("\n\n测试完成。")

    asyncio.run(main())
