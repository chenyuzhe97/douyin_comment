import asyncio
import random
import time
import re

from utils.logger import logger
from utils.config import build_comment_tasks
from utils.deepseek import AIClient
from playwright.async_api import Playwright, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from browser_manager.browser_manager import BrowserManager
from browser_manager.logger import Logger
from browser_manager.comment_manager import CommentManager
from browser_manager.page_interactions import PageInteractions
from browser_manager.file_utils import FileUtils


class DouyinCommenter:
    """
    负责：登录检测、抓评论、发表评论
    不创建 / 关闭浏览器，只接收外部注入的 page 对象。
    """

    def __init__(self, page):
        self.page = page
        self.AI = AIClient()
        self.comment_manager = CommentManager()
        self.page_interactions = PageInteractions()
        self.current_active_video = {"url": "", "comment": ""}
        self.no_more = False

    # ---------- 工具方法 ---------- #
    async def check_login_status(self) -> bool:
        """判断是否已登录：页面上存在 id='RkbQLUok' 时视为未登录。"""
        try:
            return (await self.page.query_selector("#RkbQLUok")) is None
        except Exception as e:
            logger.error(f"登录检查错误: {e}")
            return False

    async def catch_comment(self, page):
        """
        抓取当前视频 DOM 中已渲染的评论。
        返回 list[dict]；若无评论则返回 []。
        """
        try:
            # 1. 等评论节点出现（最长 10 s）
            # await page.wait_for_selector(
            #     '#merge-all-comment-container div[data-e2e="comment-item"]',
            #
            #     timeout=10_000
            # )
            # await page.wait_for_selector(".comment-item")  # 替换成实际的评论 class
            print("等待渲染完毕")
            await asyncio.sleep(3)
            text = await page.locator(".HV3aiR5J").all()
            print(text)

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

    # ---------- 主工作流 ---------- #
    async def simulate_browsing(self, task: dict, timeout_s: int = 180):
        """
        在同一个 page 上浏览 task 指定的视频，随机发表评论。
        timeout_s 控制单条视频浏览时长。
        """
        await self.page.goto(task["goto_page"])
        await asyncio.sleep(3)  # 再小等几秒，确保动态内容
        # await self.page_interactions.jump_to_modal(self.page)
        await self.page.locator("xg-icon").filter(has_text="进入全屏H").get_by_role("img").nth(1).click()
        logger.info("按下H")
        await asyncio.sleep(3)
        # # await self.page.locator("div").filter(has_text=re.compile(r"^抢首评评论X$")).get_by_role("img").click()
        #
        # await self.page.locator("div").filter(has_text=re.compile(r"^\d+评论X$")).get_by_role("img").click()
        # # await self.page.keyboard.press('X')

        # 先找"抢首评评论X"
        try:
            await self.page.locator("div").filter(has_text=re.compile(r"^抢首评评论X$")).get_by_role("img").click()
        except Exception as e:
            await self.page.locator("div").filter(has_text=re.compile(r"^\d+评论X$")).get_by_role("img").click()



        logger.info("按下X")

        start_time = time.time()
        comments_made = []
        count = 0

        while time.time() - start_time < timeout_s:
            await asyncio.sleep(3)  # 给页面一点渲染/播放时间

            comment_list = await self.catch_comment(self.page)
            print(comment_list)
            # ⅓ 概率发表评论，可自行调整
            if random.randint(1, 3) <= 3:
                logger.info("决定发表评论")

                if not comment_list:  # 无现成评论 → 随机评论
                    random_caption = self.comment_manager.get_random_comment(
                        task["comments_list"]
                    )
                    logger.info("不走 AI")
                else:  # 有评论 → 让大模型生成回复
                    random_caption = await self.AI.send_message(comment_list)
                    logger.info("走 AI")

                self.current_active_video.update(
                    {"url": task["goto_page"], "comment": random_caption}
                )

                if comment_list:
                    await self.comment_manager.post_comment(self.page, random_caption)
                    comments_made.append(random_caption)

                    logger.info(
                        f"已发布评论: {random_caption}，当前累计评论数: {len(comments_made)}"
                    )
                    break
                logger.info(
                    f"已发布评论: {random_caption}，当前累计评论数: {len(comments_made)}"
                )
                break

            else:
                logger.info("决定继续浏览，不发表评论")
                break

        logger.info(
            f"任务结束，共发表评论 {len(comments_made)} 条，页面停留 {time.time() - start_time:.1f}s"
        )
        await asyncio.sleep(random.uniform(3, 6))


# ========== 脚本入口 ========== #
async def run():
    cookie_files = FileUtils.find_files("cookie", ".json")
    if not cookie_files:
        logger.error("未找到任何 cookie 文件，脚本退出")
        return
    cookie_file = cookie_files[0]

    comment_tasks = build_comment_tasks("./target/video_index.csv")
    if not comment_tasks:
        logger.error("未读取到任何任务")
        return

    async with async_playwright() as p:
        # --- 启动浏览器一次 ---
        browser_manager = BrowserManager()
        browser = await browser_manager.init_browser(p)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            storage_state=cookie_file,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        commenter = DouyinCommenter(page)
        if not await commenter.check_login_status():
            logger.error("账号未登录，脚本终止")
            await context.close()
            await browser.close()
            return

        # --- 依次执行任务 ---
        for idx, task in enumerate(comment_tasks, 1):
            logger.info(f"开始第 {idx}/{len(comment_tasks)} 个任务: {task['goto_page']}")
            try:
                await commenter.simulate_browsing(task, timeout_s=180)
            except Exception as e:
                logger.error(f"任务 {task['goto_page']} 出错: {e}")

        # --- 结束 ---
        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
