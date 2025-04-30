from bs4 import BeautifulSoup, SoupStrainer
from pathlib import Path
import re

FILE = Path("./origin.txt")          # 你的上传文件
html_text = FILE.read_text(encoding="utf-8", errors="ignore")

# 只解析 <a> 标签，速度更快
only_a = SoupStrainer("a")
soup = BeautifulSoup(html_text, "lxml", parse_only=only_a)

links = set()
for tag in soup:
    href = tag.get("href", "")
    if "/video/" in href:          # 也可以用正则更精确地限定
        # 绝对/相对路径都补成完整 URL，便于点击
        if href.startswith("/video/"):
            href = f"https://www.douyin.com{href}"
        links.add(href)

links = sorted(links)

# 输出 Markdown
for url in links:
    print(f"- [{url}]({url})")
