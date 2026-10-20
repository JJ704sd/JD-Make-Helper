# 本地项目进展素材库

用于用户要求从多个本地项目持续收集进展、压缩关键节点并统一保存，以供后续简历润色的任务。沿用本 Skill 的事实、归属和验证边界；素材库是私有依据层，不是自动生成的对外履历。

## 最小可用流程

1. 根据本次授权选定项目目录与材料范围，复制 [配置示例](../assets/project-hub-config.example.json) 到用户私有目录并填写来源。根目录只读取配置中指定的文字文件、Git 历史和聊天导出，不自动扫描全盘、账号数据库或隐藏凭据。用户已选定的范围不重复询问。
2. 用 [本地采集器](../scripts/project_hub.py) 的 collect 命令保存快照，先读 reading/index.json 的覆盖说明，再读取相关带行号材料。Git 记录支持提交与时间线；文档支持其中记载的设计或结果，不能直接证明个人作者、运行成功或生产验收。聊天保留说话人、后续修正、截断及未读附件信息。
3. 由当前 Agent 基于实际读到的内容压缩节点。按项目归并同一问题的连续小修改；保留需求/决策、实现、验证、问题与修正、交付和计划等关键转折。每个节点写清问题、动作、结果与限制，关联快照 ID 和行范围。内容未知时保留未知，不从文件时间推断事件日期。
4. 用 import 命令将节点写入统一 SQLite 素材库，再 export 生成搜索页面、resume-context.md 与现有格式的 claim-ledger.md。只改写简历时优先查询已有节点，需要时展开原快照，不把压缩摘要当作独立确认来源。

采集、结构验证和索引由本地标准库脚本完成；语义压缩由当前 Agent 完成。脚本不另调模型，不在后台定时运行。重新采集不会重复已有快照；原文变化会保留旧快照并让引用旧版本的节点提示待复核。再次导出后页面才更新。

## 命令

从仓库根目录执行；安装到其他位置时改用脚本的绝对路径。私有配置、数据库和交付目录不要提交到公开仓库。

    python -X utf8 -B skills/distill-internship-projects/scripts/project_hub.py collect --config private/project-hub.sources.json --db private/project-hub.sqlite3 --bundle outputs/project-hub/reading
    python -X utf8 -B skills/distill-internship-projects/scripts/project_hub.py import --db private/project-hub.sqlite3 --input private/project-milestones.json
    python -X utf8 -B skills/distill-internship-projects/scripts/project_hub.py export --db private/project-hub.sqlite3 --output outputs/project-hub
    python -X utf8 -B skills/distill-internship-projects/scripts/project_hub.py search --db private/project-hub.sqlite3 --project example-project --query 幂等

配置相对目录以配置文件所在目录为基准。documents 支持项目根目录内的 Markdown/TXT glob，chats 支持已有导入器兼容的文本及 JSON/JSONL 聊天导出。每份文字默认最多 96 KiB，每项目默认 30 份文件，Git 默认最近 30 条；可配置 git_since 与限额。截断、缺失、无法读取和不支持的格式会记录覆盖提示。大聊天先按 [聊天读取](chat-to-resume.md)拆分；PDF、Word、截图需先提取为文字再明确加入来源，不声称当前采集器支持其原格式。

Git 只运行 log，使用所选目录的命令级 safe.directory，不修改全局配置、分支、索引或源文件。采集器只对常见密钥和邮箱作尽力脱敏；私有材料仍不能当作已清理的公开数据。

## 节点格式

import 消费如下 JSON。示例 ID 和行范围必须用实际快照替换；同项目更新沿用稳定节点 ID。

```json
{
  "schema_version": "project-milestones-v1",
  "milestones": [{
    "id": "example-parser-local-validation",
    "project_id": "example-project",
    "date": null,
    "title": "解析原型完成一轮局部验证",
    "summary": "材料记载已检查指定样例的字段输出；尚无完整语义回归和生产使用依据。",
    "kind": "验证",
    "stage": "本地原型",
    "ownership": "本人动作与团队边界待确认",
    "verification": "历史材料记载，本轮没有重跑源项目",
    "status": "待确认",
    "evidence": [{"snapshot_id": "S-replace-with-captured-id", "start_line": 1, "end_line": 3}],
    "supersedes": []
  }]
}
```

- kind：决策 / 实现 / 验证 / 交付 / 问题 / 计划 / 修正。
- status：沿用已确认 / 待确认 / 计划 / 不采用；项目历史不能自动确认本人职责，来源变化后的已确认节点导出时降为待确认。计划的真实性可以被确认，完成情况仍按 kind、stage 与验证范围判断。
- date：原材料支持的 YYYY-MM-DD，未知填 null。提交日期可用于该提交发生时间，不能作为实习日期或上线日期。
- evidence：非空，必须引用同项目的已存快照与有效行范围。脚本检查结构与引用，不判断语义真实性。
- supersedes：需要明确取代旧结论时引用同项目已存在的旧节点 ID。旧节点保留、页面默认隐藏，简历上下文排除。相同节点的内容更新另存修订历史；冲突未解决时保留限制，不能随意选较好结果。

结构错误整批回滚；重复导入相同节点不新增版本。SQLite 使用 project-hub schema v1，不会把已有的其他业务数据库当作素材库。

## 后续简历润色

先查询目标岗位相关节点，再结合 [证据与归属](evidence-and-ownership.md)及 [岗位匹配](jd-matching.md)选择经历。导出的账本与原有 Markdown 账本格式兼容，不要求迁移已有私有材料。对外措辞继续采用用户明确确认或材料足以支持的事实，保留个人边界；摘要不能替代本人职责确认。

默认不把本地素材库同步到飞书、Notion 或其他云服务；用户指定平台后再按授权连接。当前交付不依赖它们的账号，也不安装 Magpie。参考的是 [Magpie 官网](https://usemagpie.ai/zh/)在 2026-10-20 展示的统一入口思路；官网描述的是模型/Agent 管理，本项目自行实现多来源进展采集与证据节点。
