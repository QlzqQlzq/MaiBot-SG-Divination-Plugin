from typing import Any

from . import card, forward, text
from .models import DivinationOutput


async def send_output(
    ctx: Any,
    output: DivinationOutput,
    stream_id: str,
    *,
    mode: str,
    fallback_mode: str,
    forward_nickname: str,
    card_width: int,
    card_scale: float,
) -> Any:
    selected = mode.strip().lower()
    try:
        if selected == "text":
            return await text.send(ctx, output, stream_id)
        if selected == "forward":
            return await forward.send(ctx, output, stream_id, nickname=forward_nickname)
        if selected == "card":
            return await card.send(ctx, output, stream_id, width=card_width, scale=card_scale)
        raise ValueError(f"不支持的输出模式：{mode}")
    except Exception as exc:
        fallback = fallback_mode.strip().lower()
        if fallback == selected:
            raise
        if fallback == "forward":
            ctx.logger.warning("%s 输出失败，降级为合并转发：%s", selected, exc)
            return await forward.send(ctx, output, stream_id, nickname=forward_nickname)
        if fallback == "text":
            ctx.logger.warning("%s 输出失败，降级为普通文本：%s", selected, exc)
            return await text.send(ctx, output, stream_id)
        raise ValueError(f"不支持的回退输出模式：{fallback_mode}") from exc
