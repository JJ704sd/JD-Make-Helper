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
