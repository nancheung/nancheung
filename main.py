import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

README = Path(__file__).parent / "README.md"
TZ = ZoneInfo("Asia/Shanghai")
# 开始用 AI 写代码的日子
VIBE_START = date(2022, 1, 1)
CC_LATEST_URL = "https://registry.npmjs.org/@anthropic-ai/claude-code/latest"
BLOG_FEED_URL = "https://blog.nancheung.com/feed.xml"
BLOG_LIMIT = 3


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "nancheung-readme-bot"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


def render_date(today):
    return f"😄{today:%Y-%m-%d}😄"


def render_vibe(today):
    years = today.year - VIBE_START.year
    months = today.month - VIBE_START.month
    days = today.day - VIBE_START.day
    if days < 0:
        # 向上个月借位
        months -= 1
        days += (today.replace(day=1) - timedelta(days=1)).day
    if months < 0:
        years -= 1
        months += 12
    return f"Vibe 时长两年半（实际 {years} 年 {months} 个月 {days} 天，已超额练习）"


def render_cc(today):
    version = json.loads(fetch(CC_LATEST_URL))["version"]
    return f"**v{version}**"


def render_blog(today):
    items = ET.fromstring(fetch(BLOG_FEED_URL)).findall("./channel/item")[:BLOG_LIMIT]
    if not items:
        raise ValueError("RSS 中没有文章")
    lines = []
    for item in items:
        # 长标题只取破折号前的主标题
        title = item.findtext("title").split("——")[0].strip()
        published = parsedate_to_datetime(item.findtext("pubDate")).astimezone(TZ)
        lines.append(f"- `{published:%Y-%m-%d}` [{title}]({item.findtext('link')})")
    return "\n" + "\n".join(lines) + "\n"


# 区块名 -> 渲染函数，对应 README 中的 <!-- 名:start -->...<!-- 名:end -->
BLOCKS = {
    "date": render_date,
    "vibe": render_vibe,
    "cc": render_cc,
    "blog": render_blog,
}


def main():
    today = datetime.now(TZ).date()
    content = README.read_text(encoding="utf-8")

    for name, render in BLOCKS.items():
        pattern = re.compile(rf"(<!-- {name}:start -->).*?(<!-- {name}:end -->)", re.S)
        if not pattern.search(content):
            print(f"[{name}] README 中没有找到标记，跳过")
            continue
        try:
            block = render(today)
        except Exception as e:
            # 外部数据拉取失败时保留旧内容，不影响其他区块
            print(f"[{name}] 渲染失败，保留旧内容：{e}")
            continue
        content = pattern.sub(lambda m: m.group(1) + block + m.group(2), content)
        print(f"[{name}] {block.strip()}")

    README.write_text(content, encoding="utf-8")


main()
