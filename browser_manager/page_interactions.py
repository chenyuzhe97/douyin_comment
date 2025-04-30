import asyncio
import random
from browser_manager.logger import logger
from playwright.async_api import Page, expect


class PageInteractions:
    @staticmethod
    async def browse_video(page):
        wait_time_before_action = random.uniform(2, 12)
        logger.info(f"等待 {wait_time_before_action:.2f} 秒，准备浏览下一个视频")
        await asyncio.sleep(wait_time_before_action)

        logger.info("按下 ↓ 键切换到下一个视频")
        await page.keyboard.press("ArrowDown")

        logger.info("获取视频标题和ID")
        await asyncio.sleep(1)

    @staticmethod
    async def get_video_id(page):
        try:
            video_element = page.locator(
                '[data-e2e="feed-item"]>[data-e2e="feed-active-video"]'
            )
            video_id = await video_element.get_attribute("data-e2e-vid")
            logger.info(f"当前视频ID: {video_id}")
            return f"https://www.douyin.com/video/{video_id}"
        except Exception as e:
            logger.error(f"获取视频ID时出现错误: {e}")
            return None
    @staticmethod
    async def jump_to_modal(page: Page) -> None:
        """
        1. 点击左侧“多列”按钮（用 .JLxgOO5G…）
        2. 等弹窗列表 .NA7vT_tM 出来后，点第三个 .AMqhOzPC（索引 2）
        3. 等真正 <video> 元素出现，表示视频已打开
        """
        #
        # # ① 点击“多列”按钮（class 名 + :has-text 双保险）
        # btn_multi = page.locator('.JLxgOO5G div:has-text("多列")')
        # await expect(btn_multi).to_be_visible(timeout=35_000)
        # await btn_multi.click()
        #
        # # ② 等弹窗渲染完，拿到所有缩略图容器
        # await page.wait_for_selector(".NA7vT_tM .AMqhOzPC", timeout=35_000)
        # all_cards = page.locator(".NA7vT_tM .AMqhOzPC")
        #
        # # ▶ 点第三张缩略图
        # card = all_cards.nth(2)
        # await card.scroll_into_view_if_needed()
        # await card.click()
        #
        # # ③ 确认真正的视频播放器出现
        # await page.wait_for_selector("video[src]", timeout=35_000)

    @staticmethod
    async def click_second_video_comment_icon(page):
        try:
            await page.wait_for_selector(
                '[data-e2e="feed-active-video"]', timeout=35000
            )
            logger.info('[data-e2e="feed-active-video"] 元素已找到')

            active_videos = await page.locator('[data-e2e="feed-active-video"]').all()

            if len(active_videos) >= 2:
                comment_icon = active_videos[1].locator(
                    '[data-e2e="feed-comment-icon"]'
                )
                await comment_icon.click()
                logger.info("成功点击第二个视频的评论图标")
            else:
                logger.warning(
                    "[data-e2e='feed-active-video'] 元素少于两个，无法点击第二个视频的评论图标，点第一个"
                )
                comment_icon = active_videos[0].locator(
                    '[data-e2e="feed-comment-icon"]'
                )
                await comment_icon.click()

        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
