from html import escape
from typing import Any

from .models import DivinationOutput


def build_html(output: DivinationOutput) -> str:
    lines = "".join(f"<div class='yao'>{escape(line.strip())}</div>" for line in output.lines)
    paragraphs = "".join(
        f"<p>{escape(paragraph.strip()).replace(chr(10), '<br>')}</p>"
        for paragraph in output.interpretation.split("\n\n")
        if paragraph.strip()
    )
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: transparent; }}
body {{
  font-family: "Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif;
  color: #20231f;
}}
#card {{
  width: 820px;
  padding: 54px 58px 46px;
  background: #f6f3ea;
  border: 1px solid #cec8b8;
  border-top: 8px solid #9e3429;
}}
.eyebrow {{ color: #357064; font-size: 20px; font-weight: 700; }}
h1 {{ margin: 10px 0 4px; font-size: 48px; line-height: 1.2; font-weight: 800; }}
.trigrams {{ color: #5b6059; font-size: 23px; }}
.question {{
  margin: 30px 0 26px;
  padding: 18px 22px;
  border-left: 5px solid #357064;
  background: #ebe7dc;
  font-size: 23px;
  line-height: 1.65;
}}
.hexagram {{
  display: grid;
  grid-template-columns: 230px 1fr;
  gap: 34px;
  align-items: center;
  padding: 26px 0 30px;
  border-bottom: 1px solid #cec8b8;
}}
.yao-list {{ display: flex; flex-direction: column; gap: 10px; }}
.yao {{ font-family: "Noto Sans Mono CJK SC", "Microsoft YaHei", monospace; font-size: 27px; line-height: 1; white-space: pre; }}
.changing {{ color: #9e3429; font-size: 23px; font-weight: 700; line-height: 1.6; }}
.reading {{ padding-top: 22px; }}
.reading p {{ margin: 0 0 18px; font-size: 23px; line-height: 1.72; }}
.footer {{ margin-top: 28px; padding-top: 18px; border-top: 1px solid #cec8b8; color: #73776f; font-size: 18px; }}
</style>
</head>
<body>
<main id="card">
  <div class="eyebrow">MAIBOT · 群聊起卦</div>
  <h1>{escape(output.title)}</h1>
  <div class="trigrams">{escape(output.trigrams)}</div>
  <div class="question"><strong>所问</strong><br>{escape(output.question)}</div>
  <section class="hexagram">
    <div class="yao-list">{lines}</div>
    <div class="changing">{escape(output.changing_lines)}</div>
  </section>
  <section class="reading">{paragraphs}</section>
  <div class="footer">{escape(output.disclaimer)}</div>
</main>
</body>
</html>
"""


async def send(
    ctx: Any,
    output: DivinationOutput,
    stream_id: str,
    *,
    width: int = 900,
    scale: float = 1.5,
    **_: Any,
) -> Any:
    card = await ctx.render.html2png(
        build_html(output),
        selector="#card",
        viewport={"width": width, "height": 1200},
        device_scale_factor=scale,
        full_page=False,
        omit_background=True,
        allow_network=False,
    )
    image_base64 = str(card.get("image_base64") or "")
    if not image_base64:
        raise RuntimeError("卡片渲染未返回图片数据")
    return await ctx.send.image(image_base64, stream_id)
