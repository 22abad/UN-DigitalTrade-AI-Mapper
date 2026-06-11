import asyncio
import json
import os
import re
from playwright.async_api import async_playwright, Page, BrowserContext
from typing import Dict, Optional, Any
from urllib.parse import urljoin, urlparse, quote
from playwright_stealth import Stealth
from collections import deque

# ── playwright-stealth 跨版本兼容 ──────────────────────────────────
# 1.x API:  from playwright_stealth import stealth_async; await stealth_async(page)
# 2.x API:  from playwright_stealth import Stealth; await Stealth().apply_stealth_async(page)
_stealth = Stealth()

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
    ts = lambda: datetime.now().strftime("%H:%M:%S")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
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

async def _download_pdf(page: Page, pdf_url: str, filename: Optional[str] = None) -> Optional[str]:
    """
    下载 PDF 文件。
    """
    try:
        parsed_url = urlparse(pdf_url)
        if not filename:
            filename = os.path.basename(parsed_url.path) or f"downloaded_pdf_{asyncio.current_task().get_name()}.pdf"
        local_path = os.path.join(DOWNLOADS_DIR, filename)
        
        # Add headers to mimic browser request | 添加请求头以模拟浏览器
        # Use the domain as referer for better compatibility | 使用域名作为 referer 以提高兼容性
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": domain,
            "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        response = await page.request.get(pdf_url, headers=headers, timeout=30000)
        if response.ok:
            with open(local_path, "wb") as f:
                f.write(await response.body())
            print(f"PDF 已下载到: {local_path}")
            return local_path
        return None
    except Exception as e:
        print(f"下载 PDF 时发生错误 {pdf_url}: {e}")
        return None

async def _extract_html_content(page: Page) -> str:
    """
    提取 HTML 页面正文。
    """
    selectors = [
        "main", "article", "section[role=main]", "[role=main]",
        ".main-content", ".mainContent", ".content-main",
        "#content", ".content", ".entry-content", ".post-content", ".body-content",
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

async def fetch_legal_content(url: str, timeout: int = 60000, max_retries: int = 3, proxy: Optional[dict] = None) -> Dict[str, Any]:
    """
    抓取法律内容（HTML 文本或 PDF）。
    """
    if any(re.match(pattern, url) for pattern in INVALID_URL_PATTERNS):
        return {"type": "error", "message": f"URL 无效: {url}"}

    for attempt in range(1, max_retries + 1):
        async with async_playwright() as p:
            context = None
            try:
                context = await _initialize_browser_context(p, proxy=proxy)
                page = await context.new_page()
                await _apply_stealth(page)
                page.set_default_timeout(timeout)
                
                # Task: Check if direct PDF URL to avoid ERR_ABORTED | 任务：检查是否为直接 PDF URL，避免导航中断
                if url.lower().split('?')[0].endswith(".pdf"):
                    print(f"检测到直接 PDF URL: {url}")
                    pdf_path = await _download_pdf(page, url)
                    if pdf_path:
                        return {"type": "pdf", "url": url, "pdf_path": pdf_path}

                print(f"正在访问: {url}")
                try:
                    # Increase timeout and use wait_until="domcontentloaded" for potentially slow gov sites
                    await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                except Exception as e:
                    # If aborted but it's a PDF, we might still be able to download it
                    error_str = str(e).lower()
                    if "err_aborted" in error_str or "navigation was aborted" in error_str or "timeout" in error_str:
                        print(f"尝试中断/超时修复，直接尝试下载: {url}")
                        pdf_path = await _download_pdf(page, url)
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
                    pdf_path = await _download_pdf(page, page.url)
                    if pdf_path:
                        return {"type": "pdf", "url": url, "pdf_path": pdf_path}
                
                await _wait_for_page_load(page, timeout)
                
                # 检测页面内的 PDF 链接
                pdf_links = await page.evaluate('Array.from(document.querySelectorAll(\'a[href$=".pdf"]\')).map(a => a.href)')
                valid_pdf_links = [l for l in pdf_links if not any(re.match(p, l) for p in INVALID_URL_PATTERNS)]
                
                if valid_pdf_links:
                    pdf_url = urljoin(page.url, valid_pdf_links[0])
                    pdf_path = await _download_pdf(page, pdf_url)
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
                    ]
                    low = content.lower().strip()
                    # Only flag when content is short (< 5KB) AND contains block language
                    if len(content) < 5000 and any(ind in low for ind in block_indicators):
                        print(f"[警告] 检测到反爬拦截 ({content[:60].strip()}...)")
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
                                    print("[Fallback] ratchakitcha.soc.go.th 被 Cloudflare 阻断，无法自动推断搜索关键词。")
                                    print("建议: 直接使用 fetch_thai_law_by_keyword('ชื่อกฎหมายภาษาไทย') 从 OCS 获取。")
                            elif alt["type"] == "web":
                                alt_url = f"https://www.{alt['source']}/"
                                print(f"[Fallback] 尝试替代网站: {alt_url}")
                                try:
                                    return await fetch_legal_content(alt_url, timeout=timeout, max_retries=1)
                                except Exception as alt_e:
                                    print(f"[Fallback] 替代来源失败: {alt_e}")
                                    continue
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
                    pdf_path = await _download_pdf(page, page.url)
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
                        pdf_path = await _download_pdf(page, href)
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
            # 搜索数据相关关键词
            for kw in ["ข้อมูล", "อิเล็กทรอนิก", "ดิจิทัล", "ระบบสารสนเทศ"]:
                count = text.count(kw)
                if count > 0:
                    print(f"   • '{kw}' 出现 {count} 次")
        else:
            print(f"❌ 失败: {result.get('message', '')[:200]}")

        # Test 2: Fallback 测试 — ratchakitcha URL 应触发阻断检测但不一定能自动补齐
        print("\n\n>>> 测试 2: ratchakitcha URL → 阻断检测 + Fallback <<<")
        fallback_result = await fetch_legal_content(
            "https://ratchakitcha.soc.go.th/search-result",
            timeout=15000,
        )
        status = fallback_result.get("type", "?")
        msg = fallback_result.get("message", "")
        if status == "error" and "Blocked" in msg:
            print("✅ 正确检测到 Cloudflare 阻断 (预期行为)")
            print(f"   提示: {msg[:150]}")
        elif status == "text":
            print(f"⚠️  Fallback 返回了文本 ({len(fallback_result.get('text',''))} chars)")
        else:
            print(f"结果: {status} — {msg[:150]}")

        # Test 3: 已知可访问的站点
        print("\n\n>>> 测试 3: 已知可访问站点 trai.gov.in (印度电信管理局) <<<")
        india_result = await fetch_legal_content(
            "https://www.trai.gov.in",
            timeout=30000,
            max_retries=1,
        )
        if india_result.get("type") == "text":
            text = india_result["text"]
            print(f"✅ 成功！获取到 {len(text)} 字符")
        else:
            print(f"结果: {india_result.get('type')} — {india_result.get('message', '')[:100]}")
        
        print("\n\n测试完成。")

    asyncio.run(main())
