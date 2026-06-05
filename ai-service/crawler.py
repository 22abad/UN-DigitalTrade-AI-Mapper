import asyncio
import os
import re
from playwright.async_api import async_playwright, Page, BrowserContext
from typing import Dict, Optional, Any
from urllib.parse import urljoin, urlparse
from playwright_stealth import Stealth

_stealth = Stealth()
from collections import deque

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
            element = await page.locator(selector).first.all()
            if element:
                text_content = await element[0].text_content()
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
                await _stealth.apply_stealth_async(page)
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
                    return {"type": "text", "url": url, "text": content}
                
                return {"type": "error", "message": "未找到有效内容"}
            except Exception as e:
                print(f"[重试 {attempt}/{max_retries}] 错误: {e}")
                if attempt == max_retries:
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
                await _stealth.apply_stealth_async(page)


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
        print("开始抓取泰国 Personal Data Protection Act 相关 PDF...")
        
        # 为了演示功能，我们直接测试一个已知的 MDES 官方 PDF 链接（由于首页 Cloudflare 拦截）
        target_urls = [
            "https://www.mdes.go.th/view/1/Digital%20Laws", # 数字法律列表页
            "https://www.mdes.go.th/download/pdpa_en.pdf"    # PDPA 英文版直接链接
        ]
        
        for url in target_urls:
            print(f"\n--- 正在处理: {url} ---")
            result = await fetch_legal_content(url, timeout=60000)
            if result.get("type") == "pdf":
                print(f"成功下载 PDF: {result['pdf_path']}")
            elif result.get("type") == "text":
                print(f"提取到文本内容，预览: {result['text'][:200]}...")
            else:
                print(f"处理失败: {result.get('message')}")

    asyncio.run(main())
