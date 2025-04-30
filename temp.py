import asyncio
import re
import time
import pandas as pd
from utils.deepseek import AIClient
from playwright.async_api import Playwright, async_playwright
import random
from tqdm import tqdm
def build_comment_tasks(csv_path):
    df = pd.read_csv(csv_path, header=None)  # 没有表头，所以 header=None
    tasks = []
    for idx, row in df.iterrows():
        tasks.append(row[0])
    print(tasks)
    return tasks


async def get_comments(page):
    comment_items = await page.locator('[data-e2e="comment-item"]').all()
    results = []
    content = ""
    for item in comment_items:
        try:
            full_text = await item.inner_text()
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            if len(lines) >= 4:
                results.append({
                    "user": lines[0],
                    "comment": lines[1],
                    "timestamp": lines[2],
                    "like": lines[3],
                })
            else:
                results.append({
                    "raw_text": full_text
                })
            content += (f"用户：{lines[0]},内容为:{lines[2]}\n""")
        except Exception as e:
            print("提取失败：", str(e))

    for r in results:
        print(r)
    return content
import json
async def load_cookies_to_context(context, cookie_file, url="https://www.douyin.com"):
    # cookies 必须先 navigate 目标域名一次，才能注入
    page = await context.new_page()
    await page.goto(url)
    with open(cookie_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    await context.add_cookies(cookies)
    return page

async def run(playwright: Playwright) -> None:
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(storage_state="./cookie/cookie_15067815522.json")
    page = await context.new_page()
    urls = build_comment_tasks("./target/video_index.csv")
    AI = AIClient()
    for url in tqdm(urls):
        try:
            await page.goto(url)
            await page.locator("xg-icon").filter(has_text="进入全屏H").get_by_role("img").nth(1).click()
            await page.keyboard.press("x")
            await asyncio.sleep(random.uniform(1, 3))

            await page.locator("div").filter(has_text=re.compile(r"^留下你的精彩评论吧$")).nth(3).click()
            await page.wait_for_selector('div[data-e2e="comment-list"]', timeout=10000)
            title = "当前网页标题为：" + await page.title() + '\n'
            await asyncio.sleep(random.uniform(3, 7))

            comment_list = await get_comments(page)
            random_caption = await AI.send_message(title+comment_list)
            await page.get_by_role("combobox").fill(random_caption)
            # 电极评论区
            await asyncio.sleep(random.uniform(10, 20))
            await page.locator(".commentInput-right-ct .oXIqR6qH").click()
            await asyncio.sleep(random.uniform(50, 70))

        except Exception as e:
            print(e)

    # ---------------------
    await context.close()
    await browser.close()


async def main() -> None:
    async with async_playwright() as playwright:
        await run(playwright)


asyncio.run(main())
