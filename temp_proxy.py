import asyncio
import re
import time
import pandas as pd
from utils.deepseek import AIClient
from playwright.async_api import Playwright, async_playwright
import random
from tqdm import tqdm
import json

PROXIES = [
    "http://botuser1:pwd123@45.72.98.11:3128",
    "http://botuser2:pwd123@62.109.24.73:20001",
    "http://botuser3:pwd123@84.233.159.66:20002",
    "http://botuser4:pwd123@103.157.191.120:8000",
    "http://botuser5:pwd123@156.225.12.97:8080",
    "socks5://botuser6:pwd123@185.146.168.44:1080",
    "socks5://botuser7:pwd123@95.164.37.210:1081",
    "http://botuser8:pwd123@gw.proxyprovider.net:22003?session=bot08",
    "http://botuser9:pwd123@gw.proxyprovider.net:22004?session=bot09",
    "http://botuser10:pwd123@gw.proxyprovider.net:22005?session=bot10",
]


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
            content += f"用户：{lines[0]},内容为:{lines[2]}\n"""
        except Exception as e:
            print("提取失败：", str(e))

    for r in results:
        print(r)
    return content

async def run(playwright: Playwright) -> None:

    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(storage_state="./cookie/cookie_18067156249.json")
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
            random_caption = await AI.send_message(title + comment_list)
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
