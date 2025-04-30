import asyncio
import os
from playwright.async_api import Playwright, async_playwright


class creator_douyin:
    def __init__(self, phone, timeout: int = 120):
        """
        初始化
        :param phone: 手机号
        :param timeout: 你要等待多久，单位秒
        """
        self.timeout = timeout * 1000
        self.phone = phone
        self.path = os.path.abspath("")
        self.desc = "cookie_%s.json" % phone

        if not os.path.exists(os.path.join(self.path, "cookie")):
            os.makedirs(os.path.join(self.path, "cookie"))

    async def __cookie(self, playwright: Playwright) -> None:
        browser = await playwright.chromium.launch(channel="chrome", headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # 反检测自动化脚本，避免页面检测 WebDriver
        await page.add_init_script(path="stealth.min.js")

        # 打开抖音主页
        await page.goto("https://www.douyin.com/?recommend=1")

        print("主页已打开")
        # 等待一些时间以确保页面加载
        # await page.wait_for_timeout(10000)  # 等待2秒
        print("页面已经加载")
        # 等待Modal弹窗加载
        # await page.wait_for_selector(".login-mask-enter-done", timeout=self.timeout)
        # print("model弹窗已加载")
        # 等待并点击验证码登录的 Tab
        # try:
        #     # 显式等待验证码登录 tab 的 img 元素加载完成，最大等待时间为 `timeout`
        #     # 2. 切换验证码登录
        #     await page.wait_for_selector('text=验证码登录', timeout=self.timeout)
        #     await page.click('text=验证码登录')
        #
        #     print("成功点击验证码登录 tab")
        # except Exception as e:
        #     print(f"点击验证码登录 tab 失败: {e}")
        #
        # # 3. 填写手机号并获取验证码
        # await page.fill('input[name="normal-input"]', self.phone)
        # await page.click('span:has-text("获取验证码")')

        await asyncio.get_event_loop().run_in_executor(
            None,
            input,
            "请在浏览器中完成验证码登录后，按回车键继续…"
        )

        # 然后再等待登录弹窗消失（根据实际面板 ID／class 改一下）
        try:
            await page.wait_for_selector(
                '#douyin_login_comp_flat_panel',  # 或者你看到的登录面板根节点选择器
                state='hidden',
                timeout=self.timeout
            )
            print("登录弹窗已关闭，准备收尾")
        except Exception as e:
            print(f"等待弹窗关闭时发生错误: {e}")

        # 最后保存 cookie／storage state，关闭 context/browser
        cookies = await context.cookies()
        # …你的保存逻辑…
        await context.storage_state(path=os.path.join(self.path, "cookie", self.desc))
        await page.close()
        await context.close()
        await browser.close()

    async def main(self):
        async with async_playwright() as playwright:
            await self.__cookie(playwright)


def main():
    while True:
        phone = input('请输入手机号码\n输入"exit"将退出服务\n')
        if phone == "exit":
            break
        elif phone.isnumeric() and len(phone) == 11:
            app = creator_douyin(phone, 60)
            asyncio.run(app.main())
        else:
            print('请输入正确的手机号码\n')


main()
