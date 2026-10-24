# thuhole-skill

让 Agent 使用 [thuhole-skill](skills/thuhole-skill/SKILL.md) 搜索新 T 树洞，或读取最新帖子及评论。

## 在 Agent 中使用

1. 让 Agent 能读取本仓库，并让它阅读 `skills/thuhole-skill/SKILL.md`。
2. 向 Agent 提供你自己的新 T 树洞 `User-Token`。建议在 Agent 的运行环境中设置 `HOLE_USER_TOKEN`；如果无法设置环境变量，可以在对话中提供，并要求 Agent 仅用于本次请求，不要回显或写入文件。

然后可以向 Agent 提出两类请求：

- 搜索：`使用这个 Skill 搜索新 T 树洞中关于「关键词」的帖子和评论。`
- 最新：`使用这个 Skill 读取最新的 10 条树洞及评论。`

Skill 会指导 Agent 调用相应工具并附上结果链接。不要把 `User-Token` 提交到仓库。
