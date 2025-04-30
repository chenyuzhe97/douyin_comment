import asyncio
import random
import time

from utils.logger import logger
from utils.config import comment_tasks
from utils.deepseek import AIClient
from playwright.async_api import Playwright, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from browser_manager.browser_manager import BrowserManager
from browser_manager.logger import Logger
from browser_manager.comment_manager import CommentManager
from browser_manager.page_interactions import PageInteractions
from browser_manager.file_utils import FileUtils


class DouyinCommenter:
    def __init__(self, cookie_file: str, comment_task):
        self.cookie_file = cookie_file
        self.ua = {
            "web": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36",
        }
        self.current_active_video = {"url": "", "comment": ""}
        self.no_more = False
        self.comment_task = comment_task
        self.browser = None
        self.context = None
        self.AI = AIClient()
        self.browser_manager = BrowserManager()
        self.logger = Logger()
        self.comment_manager = CommentManager()
        self.page_interactions = PageInteractions()

    async def check_login_status(self, page):
        logger.info("正在判断账号是否登录")
        try:
            element = await page.query_selector("#RkbQLUok")
            if element:
                logger.info("未登录状态，存在 id='RkbQLUok'")
                return False
            else:
                logger.info("已登录状态，不存在 id='RkbQLUok'")
                return True
        except Exception as e:
            logger.error(f"登录检查时出现错误: {e}")
            return False

    async def catch_comment(self, page):
        """
        抓取当前视频 DOM 中已渲染的评论。
        返回 list[dict]；若无评论则返回 []。
        """
        try:
            # 1. 等评论节点出现（最长 10 s）
            await page.wait_for_selector(
                '#merge-all-comment-container div[data-e2e="comment-item"]',

                timeout=10_000
            )
        except PlaywrightTimeoutError:
            logger.info("当前视频暂无评论")
            return []

        # 2. 已有评论 → 在浏览器端批量提取字段
        comments = await page.evaluate("""() => {
            return Array.from(
                document.querySelectorAll('#merge-all-comment-container div[data-e2e="comment-item"]')
            ).map(item => {
                const nickname = item.querySelector('[data-click-from="title"]')?.innerText.trim() || '';
                const content  = item.querySelector('.LvAtyU_f')?.innerText.trim() || '';
                const likeNum  = item.querySelector('.TRWauD80 span')?.innerText.trim() || '0';
                const timeLoc  = item.querySelector('.GOkWHE6S span')?.innerText.trim() || '';
                return {nickname, content, like: likeNum, timeLoc};
            });
        }""")

        for c in comments:
            logger.info(f"[评论] {c['nickname']}: {c['content']} ({c['like']}赞, {c['timeLoc']})")

        return comments
    async def simulate_browsing(self, page):
        logger.info("开始模拟浏览器行为")
        await asyncio.sleep(1)
        await page.keyboard.press('H')
        logger.info("成功按下H")
        await asyncio.sleep(1)
        # logger.info("成功按下F")
        await asyncio.sleep(1)
        await page.keyboard.press('X')
        logger.info("成功按下X")
        await page.keyboard.press('K')
        await page.keyboard.press('K')
        comments_made = []
        # await asyncio.sleep(5)
        try:
            while True:
                if self.no_more:
                    await page.goto(self.comment_task["goto_page"])
                    await self.page_interactions.jump_to_modal(page)

                await self.page_interactions.browse_video(page)

                new_url = await self.page_interactions.get_video_id(page)
                if new_url == self.current_active_video["url"]:
                    logger.info("没有更多了")
                    self.no_more = True
                else:
                    self.no_more = False
                    self.current_active_video["url"] = new_url
                comment = await self.catch_comment(page)

                if random.randint(1, 3) <= 3:
                    # if random.randint(1, 3) <= 2:
                    logger.info("决定发表评论")
                    if not self.no_more:
                        print(comment)
                        if not comment:
                            random_caption = self.comment_manager.get_random_comment(
                                self.comment_task["comments_list"]
                            )
                            print("不走Ai")
                        else:
                            random_caption = await self.AI.send_message(comment)
                            print("走Ai")
                        print(random_caption)
                        self.current_active_video["comment"] = random_caption

                        if comment:
                            await self.comment_manager.post_comment(page, random_caption)
                            comments_made.append(random_caption)
                        logger.info(
                            f"已发布评论: {random_caption}，当前累计评论数: {len(comments_made)}"
                        )
                    else:
                        logger.info("没有更多了")
                else:
                    logger.info("决定继续浏览，不发表评论")
                    self.current_active_video["comment"] = "不发表评论"
                    await asyncio.sleep(random.uniform(5, 10))

                self.logger.log_current_active_video(self.current_active_video)

        except Exception as e:
            logger.error(f"模拟浏览器行为时出现错误: {e}")

    async def start_browsing(self, p: Playwright) -> None:
        self.browser = await self.browser_manager.init_browser(p)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 720},
            storage_state=self.cookie_file,
            user_agent=self.ua["web"],
        )
        page = await self.context.new_page()

        try:
            # await page.add_init_script(path="stealth.min.js")
            await page.goto(self.comment_task["goto_page"])
            is_logged_in = await self.check_login_status(page)

            if is_logged_in:
                await self.page_interactions.jump_to_modal(page)
                await self.simulate_browsing(page)
            else:
                logger.error("请检查登录状态，未登录无法继续")

        except Exception as e:
            logger.error(f"浏览过程中发生错误: {e}")
        finally:
            await self.context.close()
            await self.browser.close()

    async def destroy(self):
        await self.context.close()
        await self.browser.close()

    async def main(self):
        async with async_playwright() as playwright:
            await self.start_browsing(playwright)


async def run():
    cookie_files = FileUtils.find_files("cookie", ".json")
    if not cookie_files:
        logger.error("未找到任何cookie文件")
        return

    for task in comment_tasks:
        commenter = DouyinCommenter(cookie_files[0], task)
        try:
            await asyncio.wait_for(commenter.main(), timeout=180)
        except asyncio.TimeoutError:
            logger.info("评论主函数执行超时，停止执行。")
        finally:
            await commenter.destroy()

        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(run())
