from typing import Any

from .models import DivinationOutput


async def send(ctx: Any, output: DivinationOutput, stream_id: str, **_: Any) -> Any:
    return await ctx.send.text(output.as_text(), stream_id)
