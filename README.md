# MaiBot 随机算卦插件

面向 MaiBot 群聊场景的随机算卦插件。群友发送 `/sg 问题` 后，插件使用三枚钱币法在本地生成六爻，再调用 MaiBot 已配置的模型给出克制、务实的情境解读。

当前版本：`1.1.0`

## 功能

- 使用 `/sg 问题` 在群聊中起卦并强制回复结果。
- 本地随机生成本卦与动爻，不向外部服务提交随机过程。
- 通过 MaiBot 的 `planner` 模型任务生成解读，失败时可回退到 `replyer`。
- 注册 `cast_divination` Tool，供 MaiBot 在明确需要算卦时调用。
- 支持普通文本、合并转发聊天记录和图片卡片三种输出方式。
- 解读强调现实可执行的建议，不断言吉凶或保证未来结果。

## 安装

将仓库克隆或下载到 MaiBot 的 `plugins` 目录：

```text
plugins/
└── sg_divination_plugin/
    ├── _manifest.json
    ├── plugin.py
    └── config.toml
```

重启 MaiBot，或等待插件运行器完成热重载。

## 使用

在群聊发送：

```text
/sg 你此刻想问的问题
```

示例：

```text
/sg 今日运势
/sg 这个项目下一步应该优先处理什么？
```

插件会先发送“正在起卦，请稍候……”，随后回复卦象、动爻与 AI 解读。

## 配置

`config.toml`：

```toml
[plugin]
enabled = true
config_version = "1.0.0"

[divination]
model = "planner"
fallback_model = "replyer"
temperature = 0.7
max_tokens = 900
max_question_length = 500

[output]
mode = "forward"
fallback_mode = "forward"
forward_nickname = "随机算卦"
card_width = 900
card_scale = 1.5
```

- `model`：主要解卦模型任务名。
- `fallback_model`：主要模型失败或未返回有效工具调用时使用的备用任务名；留空可禁用回退。
- `temperature`：解读文本的随机度。
- `max_tokens`：单次解读的最大 token 数。
- `max_question_length`：问题的最大字符数，超出部分会被截断。
- `mode`：输出模式，可选 `text`、`forward` 或 `card`。
- `fallback_mode`：所选输出方式失败时使用的回退方式，可设为 `forward` 或 `text`。
- `forward_nickname`：合并转发聊天记录中各节点显示的昵称。
- `card_width`：图片卡片的渲染视口宽度。
- `card_scale`：图片卡片的清晰度倍率。

### 输出模式

- `text`：直接发送完整文本，兼容性最好。
- `forward`：把所问、卦象和解读分成多个节点，打包为一条合并转发聊天记录。
- `card`：使用 MaiBot 的 `render.html2png` 能力渲染图片卡片，再发送图片。

三个输出实现分别位于 `outputs/text.py`、`outputs/forward.py` 和 `outputs/card.py`，主插件只通过统一调度器调用。

## 注意事项

卦象仅用于娱乐和整理思路，不替代医疗、法律、财务或其他专业判断。插件会要求模型优先给出现实中可以验证的行动建议，避免制造恐慌或断言结果。

## 开发说明

作者：[QlzqQlzq](https://github.com/QlzqQlzq)

本插件在开发、调试和文档整理过程中使用了 AI 辅助。

## 许可证

[MIT](LICENSE)
