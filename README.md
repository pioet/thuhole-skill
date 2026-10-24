# 新 T 树洞搜索 Skill

让 Agent 使用 [thuhole-search Skill](skills/thuhole-search/SKILL.md) 搜索新 T 树洞的帖子和评论。

## 在 Agent 中使用

1. 让 Agent 能读取本仓库，并在对话中告诉它：`请阅读 skills/thuhole-search/SKILL.md，使用这个 Skill 搜索新 T 树洞中关于「关键词」的内容。`
2. 向 Agent 提供你自己的新 T 树洞 `User-Token`。建议在 Agent 的运行环境中设置 `HOLE_USER_TOKEN`；如果无法设置环境变量，可以在对话中提供，并要求 Agent 仅用于本次搜索，不要回显或写入文件。

Skill 会指导 Agent 调用仓库内的搜索工具并附上结果链接。不要把 `User-Token` 提交到仓库。
