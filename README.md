# JD-Make-Helper

把实习期间做过的项目，提炼成有个人贡献、有技术细节、能回答面试追问的简历经历。

本项目的核心是 [distill-internship-projects](skills/distill-internship-projects/SKILL.md) Skill。它接受项目仓库、工作记录、设计文档、问题修复记录或已有简历，先还原事实，再组织经历。适合整理实习复盘、改写项目段落，以及面向全栈开发、后端开发、测试开发或运维开发制作不同投递版本。

## 使用

把整个 skills/distill-internship-projects 文件夹复制到你使用的 Agent 的 Skill 目录。在 Codex 中，可放到 ~/.codex/skills/；只克隆仓库不会自动完成全局安装。也可以在仓库内直接让 Agent 读取上述 SKILL.md。

可以直接这样提需求：

> 请使用 $distill-internship-projects，整理我实习期间这几个项目的代码和工作记录，提炼成开发实习的简历经历。先写有证据的部分，缺少的事实另列。

> 请把这段项目经历改成测试开发实习版本，保留我的实际职责和验证范围。

> 结合目标 JD，从这几个项目中选择最值得写的经历，说明哪些应合并，哪些应单独保留。

默认只交付请求的项目段落；需要整份简历或文件时，再使用附带的内容骨架和可编辑 HTML 模板。

## 会得到什么

- 项目全貌：业务需求、实习时间线、个人负责内容和关键实现。
- 可用经历：项目标题、背景和简历要点；按岗位调整重点。
- 事实依据：主张对应的材料、职责归属、验证环境和待确认项。
- 面试准备：能解释的技术取舍、异常处理、验证方式和限制。
- 后续补强：缺口对应的实践任务及需要留下的证据。

多个岗位配置、多个脚本或同一项目的连续版本通常先整理为一套系统经历。是否拆分取决于业务目标、个人贡献和技术问题，不以脚本数量凑项目数量。没有测量记录时，用具体完成结果表达价值，不自动添加效率或准确率数字。

## 示例与模板

[多岗位简历筛选工具示例](skills/distill-internship-projects/references/multi-role-screening-example.md)展示同一项目如何分别突出开发和测试能力。示例用于学习提炼方式，不能作为其他使用者的经历。

[项目素材卡](skills/distill-internship-projects/assets/project-card.md)用于持续记录实习工作；[事实账本](skills/distill-internship-projects/assets/claim-ledger.md)用于保留跨版本的依据；[简历 HTML 模板](skills/distill-internship-projects/assets/resume-template.html)支持本地编辑、保存和浏览器打印。

真实材料与交付物默认放到已忽略的 private/ 或 outputs/。不要提交个人简历、客户数据、内部链接或凭据。Skill 不自动访问飞书、发送材料到外部模型、投递简历或发布交付物。

本版从 JD-clean 的 write-fullstack-intern-resume 提炼而来，扩大到实习项目沉淀与多岗位表达；[来源说明](skills/distill-internship-projects/references/source-notes.md)保留原版及 ASu-skills 的出处与许可。

## 直接给聊天记录

支持 Codex 聊天引用、粘贴的对话，以及文本/Markdown/JSON/JSONL 导出。你不需要先填写项目卡或把经历重新讲一遍。

> 请使用 $distill-internship-projects，从这些聊天记录自动整理我的项目、个人贡献、技术能力和候选简历经历。先给有依据的初稿，只列影响成稿的关键待确认项。

Agent 会读取相关历史、归并同一项目、处理后续修正，区分本人陈述、助手建议与工具结果。多聊天或长记录默认保存信息稿和事实账本，便于下次补充记录继续更新。具体流程见 [聊天到简历信息](skills/distill-internship-projects/references/chat-to-resume.md)，写法见 [虚构聊天示例](skills/distill-internship-projects/references/chat-example.md)。

长导出可由 Agent 使用零依赖的本地导入器，生成带消息定位的分块；它保留文字与来源，不直接判断经历真实性：

    python skills/distill-internship-projects/scripts/import_chat.py private/chat.json --output-dir outputs/chat-import-run

支持常见 role/content 消息列表、ChatGPT 当前会话分支和 Codex read_thread 导出；任意客户端的专用日志不保证兼容。附件未读取、历史不完整、输出截断或权限不足会明确列出。聊天日期不直接作为实习日期，助手生成的代码也不直接证明本人独立开发。

## 维护检查

本地导入器使用 Python 3.10+ 标准库，无新增运行依赖。执行相关回归：

    python -B -m unittest discover -s tests -v

结构与解析检查不替代聊天到简历的实际试用；公开同步只包含 Skill、通用模板、指南和虚构测试。
