# -*- coding: utf-8 -*-
"""
Multi‑account TikTok commenter — *方案 A*（每个账号=一个 Browser 进程）
------------------------------------------------------------------
- **完全独立的 Cookie/缓存/指纹**：同一脚本里并发启动多套 Chrome。
- **依赖**：Playwright ≥ 1.44、系统 Chrome（或改用自带 Chromium 去掉 `channel`）。
- **目录结构**：
    cookie/              ← 账号登录后保存的 storage_state JSON（一文件一账号）
    target/video_index.csv  ← 待访问的视频 URL 列表（单列、无表头）
- **用法**：`python multi_browser_playwright.py`

如需设置代理，在 `PROXIES` 中填入对应条目即可（长度不足时循环使用）。
"""

import asyncio
import random
import re
from pathlib import Path
from typing import List

import pandas as pd
from playwright.async_api import async_playwright, Playwright
from tqdm import tqdm

from utils.deepseek import AIClient

# --------------------------- 配置区 ---------------------------
COOKIE_DIR = Path("./cookie/")          # 存放 storage_state 的目录
CSV_PATH = Path("./target/video_index.csv")
MAX_CONCURRENCY = 2                    # 同时跑多少个浏览器进程

# 如不需要代理，保持为空列表即可
PROXIES: List[str] = []  # e.g. ["http://user:pass@host:port", "socks5://..."]
# -------------------------------------------------------------

def build_comment_tasks(csv_path: Path) -> List[str]:
    df = pd.read_csv(csv_path, header=None)
    return df[0].tolist()


async def extract_comments(page) -> str:
    """抓取评论并格式化成发送给 AI 的提示词。"""
    comment_items = await page.locator('[data-e2e="comment-item"]').all()
    prompt_lines: List[str] = []
    for item in comment_items:
        try:
            text = await item.inner_text()
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if len(lines) >= 2:
                user, comment = lines[0], lines[2]
                prompt_lines.append(f"用户：{user}, 内容为:{comment}")
        except Exception as e:
            print("评论提取失败:", e)
    return "\n".join(prompt_lines)


async def account_worker(playwright: Playwright, cookie_file: Path, proxy: str | None, urls: List[str]):
    """单账号流程：起一个 Browser → 逐个视频评论。"""
    browser = await playwright.chromium.launch(
        channel="chrome",
        headless=False,
        proxy={"server": proxy} if proxy else None,
    )
    context = await browser.new_context(storage_state=str(cookie_file))
    page = await context.new_page()
    ai = AIClient()

    for url in tqdm(urls, desc=cookie_file.stem, position=0, leave=False):
        try:
            await page.goto(url, timeout=60_000)
            # --- 你的业务逻辑 ---
            await page.locator("xg-icon").filter(has_text="进入全屏H").get_by_role("img").nth(1).click()
            await page.keyboard.press("x")
            await asyncio.sleep(random.uniform(1, 3))

            await page.locator("div").filter(has_text=re.compile(r"^留下你的精彩评论吧$")).nth(3).click()
            await page.wait_for_selector('div[data-e2e="comment-list"]', timeout=10_000)
            title = "当前网页标题为：" + await page.title() + "\n"
            await asyncio.sleep(random.uniform(3, 7))

            comment_prompt = await extract_comments(page)
            reply = await ai.send_message(title + comment_prompt)

            await page.get_by_role("combobox").fill(reply)
            await asyncio.sleep(random.uniform(10, 20))
            await page.locator(".commentInput-right-ct .oXIqR6qH").click()
            await asyncio.sleep(random.uniform(50, 70))
        except Exception as e:
            print(f"[{cookie_file.stem}] 处理 {url} 时出错:", e)

    await context.close()
    await browser.close()


async def main():
    urls = build_comment_tasks(CSV_PATH)
    cookie_files = sorted(COOKIE_DIR.glob("*.json"))

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async with async_playwright() as playwright:
        async def sem_task(idx: int, cf: Path):
            proxy = PROXIES[idx % len(PROXIES)] if PROXIES else None
            async with semaphore:
                await account_worker(playwright, cf, proxy, urls)

        await asyncio.gather(*(sem_task(i, cf) for i, cf in enumerate(cookie_files)))


if __name__ == "__main__":
    asyncio.run(main())
