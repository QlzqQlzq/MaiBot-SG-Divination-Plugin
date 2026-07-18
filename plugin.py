from typing import Any, Literal

import json
import secrets

from maibot_sdk import Command, Field, MaiBotPlugin, PluginConfigBase, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType

from .outputs import DivinationOutput, send_output


TRIGRAMS = {
    "111": ("乾", "天", "主动与开创"),
    "110": ("兑", "泽", "交流与取舍"),
    "101": ("离", "火", "看见与表达"),
    "100": ("震", "雷", "启动与应变"),
    "011": ("巽", "风", "渗透与调整"),
    "010": ("坎", "水", "风险与穿越"),
    "001": ("艮", "山", "边界与停止"),
    "000": ("坤", "地", "承接与积累"),
}
TRIGRAM_ORDER = ("111", "110", "101", "100", "011", "010", "001", "000")
HEXAGRAM_NAMES = (
    ("乾", "夬", "大有", "大壮", "小畜", "需", "大畜", "泰"),
    ("履", "兑", "睽", "归妹", "中孚", "节", "损", "临"),
    ("同人", "革", "离", "丰", "家人", "既济", "贲", "明夷"),
    ("无妄", "随", "噬嗑", "震", "益", "屯", "颐", "复"),
    ("姤", "大过", "鼎", "恒", "巽", "井", "蛊", "升"),
    ("讼", "困", "未济", "解", "涣", "坎", "蒙", "师"),
    ("遁", "咸", "旅", "小过", "渐", "蹇", "艮", "谦"),
    ("否", "萃", "晋", "豫", "观", "比", "剥", "坤"),
)
HEXAGRAM_NUMBERS = (
    (1, 43, 14, 34, 9, 5, 26, 11),
    (10, 58, 38, 54, 61, 60, 41, 19),
    (13, 49, 30, 55, 37, 63, 22, 36),
    (25, 17, 21, 51, 42, 3, 27, 24),
    (44, 28, 50, 32, 57, 48, 18, 46),
    (6, 47, 64, 40, 59, 29, 4, 7),
    (33, 31, 56, 62, 53, 39, 52, 15),
    (12, 45, 35, 16, 20, 8, 23, 2),
)


class PluginSectionConfig(PluginConfigBase):
    __ui_label__ = "插件"
    __ui_icon__ = "package"
    __ui_order__ = 0

    enabled: bool = Field(default=True, description="是否启用随机算卦插件")
    config_version: str = Field(default="1.0.0", description="配置版本")


class DivinationSettings(PluginConfigBase):
    __ui_label__ = "解卦设置"
    __ui_icon__ = "sparkles"
    __ui_order__ = 1

    model: str = Field(default="planner", description="MaiBot 模型任务名称；默认由工具规划模型 planner 处理")
    fallback_model: str = Field(default="replyer", description="主模型失败时使用的备用模型任务")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="解读文本的随机度")
    max_tokens: int = Field(default=900, ge=200, le=2000, description="AI 解读最大 token 数")
    max_question_length: int = Field(default=500, ge=20, le=2000, description="问题允许的最大字符数")


class OutputSettings(PluginConfigBase):
    __ui_label__ = "输出设置"
    __ui_icon__ = "image"
    __ui_order__ = 2

    mode: Literal["text", "forward", "card"] = Field(
        default="forward",
        description="输出方式：普通文本、合并转发聊天记录或图片卡片",
    )
    fallback_mode: Literal["text", "forward"] = Field(
        default="forward",
        description="所选输出方式失败时使用的回退输出方式",
    )
    forward_nickname: str = Field(default="随机算卦", description="合并转发节点显示的昵称")
    card_width: int = Field(default=900, ge=720, le=1400, description="卡片渲染视口宽度")
    card_scale: float = Field(default=1.5, ge=1.0, le=2.0, description="卡片图片渲染倍率")


class DivinationConfig(PluginConfigBase):
    plugin: PluginSectionConfig = Field(default_factory=PluginSectionConfig)
    divination: DivinationSettings = Field(default_factory=DivinationSettings)
    output: OutputSettings = Field(default_factory=OutputSettings)


class DivinationPlugin(MaiBotPlugin):
    config_model = DivinationConfig

    async def on_load(self) -> None:
        self.ctx.logger.info("随机算卦插件已加载，命令：/sg 问题")

    async def on_unload(self) -> None:
        self.ctx.logger.info("随机算卦插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict[str, object], version: str) -> None:
        self.ctx.logger.info("随机算卦配置已更新：scope=%s version=%s", scope, version)

    @Command(
        "sg",
        description="在群聊中根据当前问题随机起卦并生成情境解读",
        pattern=r"^/sg(?:\s+(?P<question>[\s\S]+))?$",
        timeout_ms=180000,
    )
    async def handle_sg(self, stream_id: str = "", **kwargs: Any):
        if not self.config.plugin.enabled:
            message = "随机算卦插件当前未启用。"
            await self.ctx.send.text(message, stream_id)
            return False, message, True

        matched = kwargs.get("matched_groups")
        question = str(matched.get("question") or "").strip() if isinstance(matched, dict) else ""
        if not question:
            message = "用法：/sg 你此刻想问的问题\n例如：/sg 这个游戏为什么打不开，我下一步该怎么排查？"
            await self.ctx.send.text(message, stream_id)
            return False, "缺少要问的问题", True

        question = question[: self.config.divination.max_question_length]
        acknowledged = await self.ctx.send.text("正在起卦，请稍候……", stream_id)
        if not acknowledged:
            return False, "无法发送起卦提示", True
        reading = await self._create_reading(question)
        sent = await send_output(
            self.ctx,
            reading,
            stream_id,
            mode=self.config.output.mode,
            fallback_mode=self.config.output.fallback_mode,
            forward_nickname=self.config.output.forward_nickname,
            card_width=self.config.output.card_width,
            card_scale=self.config.output.card_scale,
        )
        if not sent:
            return False, "起卦完成，但回复发送失败", True
        return True, "已强制完成起卦、解读与发送", True

    @Tool(
        "cast_divination",
        description="当用户明确希望算一卦时，根据其具体问题随机生成卦象和务实的行动建议。卦象用于反思，不用于断言未来。",
        parameters=[
            ToolParameterInfo(
                name="question",
                param_type=ToolParamType.STRING,
                description="用户此刻想询问的具体问题",
                required=True,
            )
        ],
    )
    async def cast_divination(self, question: str = "", **kwargs: Any):
        del kwargs
        if not self.config.plugin.enabled:
            return {"success": False, "content": "随机算卦插件当前未启用。"}
        normalized = question.strip()[: self.config.divination.max_question_length]
        if not normalized:
            return {"success": False, "content": "请先提供一个具体问题。"}
        reading = await self._create_reading(normalized)
        return {"success": True, "content": reading.as_text()}

    async def _create_reading(self, question: str) -> DivinationOutput:
        hexagram = self._cast_hexagram()
        prompt = self._build_prompt(question, hexagram)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "send_divination_reply",
                    "description": "提交本次算卦最终要发送给用户的中文回复正文",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "包含此刻之势、宜、慎和建议的做法的最终回复",
                            }
                        },
                        "required": ["message"],
                    },
                },
            }
        ]
        result = await self.ctx.call_capability(
            "llm.generate_with_tools",
            timeout_ms=120000,
            prompt=prompt,
            tools=tools,
            model=self.config.divination.model.strip() or "planner",
            temperature=self.config.divination.temperature,
            max_tokens=self.config.divination.max_tokens,
        )
        interpretation = self._extract_reply_message(result)
        fallback_model = self.config.divination.fallback_model.strip()
        if (not result.get("success") or not interpretation) and fallback_model:
            self.ctx.logger.warning(
                "主解卦模型失败，切换备用模型 %s：%s",
                fallback_model,
                result.get("error") or result.get("message") or "未返回有效工具调用",
            )
            result = await self.ctx.call_capability(
                "llm.generate_with_tools",
                timeout_ms=120000,
                prompt=prompt,
                tools=tools,
                model=fallback_model,
                temperature=self.config.divination.temperature,
                max_tokens=self.config.divination.max_tokens,
            )
            interpretation = self._extract_reply_message(result)
        if not result.get("success") or not interpretation:
            reason = str(result.get("error") or result.get("message") or "模型没有返回有效内容")
            self.ctx.logger.error("解卦模型调用失败：%s", reason)
            interpretation = "AI 解读暂时不可用，请稍后再试。"

        return self._build_output(question, hexagram, interpretation)

    @staticmethod
    def _extract_reply_message(result: dict[str, Any]) -> str:
        for tool_call in result.get("tool_calls") or []:
            function = tool_call.get("function") if isinstance(tool_call, dict) else None
            if not isinstance(function, dict) or function.get("name") != "send_divination_reply":
                continue
            arguments = function.get("arguments")
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            if isinstance(arguments, dict):
                message = str(arguments.get("message") or "").strip()
                if message:
                    return message
        return str(result.get("response") or "").strip()

    @staticmethod
    def _cast_hexagram() -> dict[str, Any]:
        # 三枚钱币法：每枚取 2 或 3，得到老阴 6、少阳 7、少阴 8、老阳 9。
        lines = [sum(2 + secrets.randbelow(2) for _ in range(3)) for _ in range(6)]
        binary = ["1" if value in (7, 9) else "0" for value in lines]
        lower_key = "".join(binary[:3])
        upper_key = "".join(binary[3:])
        row = TRIGRAM_ORDER.index(lower_key)
        column = TRIGRAM_ORDER.index(upper_key)
        upper = TRIGRAMS[upper_key]
        lower = TRIGRAMS[lower_key]
        changing_lines = [index + 1 for index, value in enumerate(lines) if value in (6, 9)]
        return {
            "lines": lines,
            "name": HEXAGRAM_NAMES[row][column],
            "number": HEXAGRAM_NUMBERS[row][column],
            "upper": upper,
            "lower": lower,
            "changing_lines": changing_lines,
        }

    @staticmethod
    def _format_hexagram(hexagram: dict[str, Any]) -> str:
        rendered_lines = []
        for value in reversed(hexagram["lines"]):
            line = "━━━━━━" if value in (7, 9) else "━━  ━━"
            marker = "  ○" if value == 9 else "  ×" if value == 6 else ""
            rendered_lines.append(f"　{line}{marker}")
        changing = "、".join(str(line) for line in hexagram["changing_lines"]) or "无"
        upper = hexagram["upper"]
        lower = hexagram["lower"]
        return (
            f"第 {hexagram['number']} 卦 · {hexagram['name']}\n"
            f"{upper[1]}{upper[0]}在上 · {lower[1]}{lower[0]}在下\n"
            f"动爻：{changing}\n" + "\n".join(rendered_lines)
        )

    @staticmethod
    def _build_output(question: str, hexagram: dict[str, Any], interpretation: str) -> DivinationOutput:
        changing = "、".join(str(line) for line in hexagram["changing_lines"]) or "无"
        upper = hexagram["upper"]
        lower = hexagram["lower"]
        rendered_lines = []
        for value in reversed(hexagram["lines"]):
            line = "━━━━━━" if value in (7, 9) else "━━  ━━"
            marker = "  ○" if value == 9 else "  ×" if value == 6 else ""
            rendered_lines.append(f"　{line}{marker}")
        return DivinationOutput(
            question=question,
            title=f"第 {hexagram['number']} 卦 · {hexagram['name']}",
            trigrams=f"{upper[1]}{upper[0]}在上 · {lower[1]}{lower[0]}在下",
            changing_lines=f"动爻：{changing}",
            lines=tuple(rendered_lines),
            interpretation=interpretation,
        )

    @staticmethod
    def _build_prompt(question: str, hexagram: dict[str, Any]) -> list[dict[str, str]]:
        upper = hexagram["upper"]
        lower = hexagram["lower"]
        changing = "、".join(str(line) for line in hexagram["changing_lines"]) or "无"
        system = (
            "你是负责处理算卦工具结果的规划模型。你必须调用 send_divination_reply 提交最终回复，"
            "不要在工具调用之外输出正文。卦象只提供联想框架，不能声称预测事实或保证结果。"
            "先理解用户的实际问题；技术、医疗、法律、财务等问题必须优先给出现实中可验证的下一步，"
            "必要时建议寻求专业帮助。不要制造恐惧，不要断言吉凶，不要用玄学话术替代现实判断。"
            "请按四段输出：\n【此刻之势】结合问题解释局面；\n【宜】给总体方向；\n"
            "【慎】指出应避免的做法；\n【建议的做法】给出 2 到 4 个有先后顺序、可实际执行的步骤。"
            "总长度控制在 250 到 500 个汉字，不使用 Markdown 表格，不反问用户。"
        )
        user = (
            f"用户问题：{question}\n"
            f"本卦：第 {hexagram['number']} 卦 {hexagram['name']}\n"
            f"上卦：{upper[1]}{upper[0]}（{upper[2]}）\n"
            f"下卦：{lower[1]}{lower[0]}（{lower[2]}）\n"
            f"动爻：{changing}"
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def create_plugin() -> DivinationPlugin:
    return DivinationPlugin()
