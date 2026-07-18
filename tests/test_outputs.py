import asyncio
import base64
import unittest

from outputs import DivinationOutput, send_output
from outputs.card import build_html
from outputs.forward import build_messages


SAMPLE = DivinationOutput(
    question="今日运势",
    title="第 44 卦 · 姤",
    trigrams="天乾在上 · 风巽在下",
    changing_lines="动爻：无",
    lines=("━━━━━━", "━━━━━━", "━━━━━━", "━━━━━━", "━━━━━━", "━━  ━━"),
    interpretation="【此刻之势】保持观察。\n\n【宜】先完成可控事项。\n\n【慎】避免冲动决定。",
)


class FakeSend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, str]] = []

    async def text(self, content: str, stream_id: str) -> bool:
        self.calls.append(("text", content, stream_id))
        return True

    async def forward(self, content: list[dict], stream_id: str) -> bool:
        self.calls.append(("forward", content, stream_id))
        return True

    async def image(self, content: str, stream_id: str) -> bool:
        self.calls.append(("image", content, stream_id))
        return True


class FakeRender:
    async def html2png(self, html: str, **kwargs: object) -> dict[str, str]:
        assert "第 44 卦" in html
        assert kwargs["selector"] == "#card"
        return {"image_base64": base64.b64encode(b"png").decode()}


class FailingRender:
    async def html2png(self, html: str, **kwargs: object) -> dict[str, str]:
        raise RuntimeError("render failed")


class FakeLogger:
    def warning(self, *_: object) -> None:
        pass


class FakeContext:
    def __init__(self) -> None:
        self.send = FakeSend()
        self.render = FakeRender()
        self.logger = FakeLogger()


class OutputTests(unittest.TestCase):
    def test_model_text_methods_return_content(self) -> None:
        hexagram = SAMPLE.hexagram_text()
        complete = SAMPLE.as_text()

        self.assertIsInstance(hexagram, str)
        self.assertIn("第 44 卦 · 姤", hexagram)
        self.assertIsInstance(complete, str)
        self.assertIn("【此刻之势】保持观察。", complete)
        self.assertTrue(complete.endswith(SAMPLE.disclaimer))

    def test_forward_nodes(self) -> None:
        nodes = build_messages(SAMPLE, "随机算卦")
        self.assertGreaterEqual(len(nodes), 5)
        self.assertEqual(nodes[0]["nickname"], "随机算卦")
        self.assertIn("今日运势", nodes[0]["segments"][0]["content"])

    def test_card_html_escapes_question(self) -> None:
        unsafe = DivinationOutput(
            question="<script>alert(1)</script>",
            title=SAMPLE.title,
            trigrams=SAMPLE.trigrams,
            changing_lines=SAMPLE.changing_lines,
            lines=SAMPLE.lines,
            interpretation=SAMPLE.interpretation,
        )
        html = build_html(unsafe)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_all_modes(self) -> None:
        async def run() -> None:
            for mode, expected in (("text", "text"), ("forward", "forward"), ("card", "image")):
                ctx = FakeContext()
                result = await send_output(
                    ctx,
                    SAMPLE,
                    "stream-1",
                    mode=mode,
                    fallback_mode="forward",
                    forward_nickname="随机算卦",
                    card_width=900,
                    card_scale=1.5,
                )
                self.assertTrue(result)
                self.assertEqual(ctx.send.calls[0][0], expected)

        asyncio.run(run())

    def test_card_failure_falls_back_to_forward(self) -> None:
        async def run() -> None:
            ctx = FakeContext()
            ctx.render = FailingRender()
            result = await send_output(
                ctx,
                SAMPLE,
                "stream-1",
                mode="card",
                fallback_mode="forward",
                forward_nickname="随机算卦",
                card_width=900,
                card_scale=1.5,
            )
            self.assertTrue(result)
            self.assertEqual(ctx.send.calls[0][0], "forward")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
