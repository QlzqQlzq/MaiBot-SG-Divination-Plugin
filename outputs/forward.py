from typing import Any

from .models import DivinationOutput


def build_messages(output: DivinationOutput, nickname: str) -> list[dict[str, Any]]:
    contents = [
        f"【所问】\n{output.question}",
        f"【卦象】\n{output.hexagram_text()}",
    ]
    contents.extend(paragraph for paragraph in output.interpretation.split("\n\n") if paragraph.strip())
    contents.append(output.disclaimer)
    return [
        {
            "user_id": "0",
            "nickname": nickname,
            "segments": [{"type": "text", "content": content.strip()}],
        }
        for content in contents
        if content.strip()
    ]


async def send(
    ctx: Any,
    output: DivinationOutput,
    stream_id: str,
    *,
    nickname: str = "随机算卦",
    **_: Any,
) -> Any:
    return await ctx.send.forward(build_messages(output, nickname), stream_id)
