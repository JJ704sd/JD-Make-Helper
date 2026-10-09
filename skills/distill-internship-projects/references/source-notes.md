# 来源与验证边界

## 原 Skill

本版从 [JD-clean / write-fullstack-intern-resume](https://github.com/JJ704sd/JD-clean/tree/ef3a40360f0365b95f7cee5f5816faeb3d259235/skills/write-fullstack-intern-resume)提炼。原版已包含事实账本、个人边界、指标核对和独立 HTML 模板；本版调整为实习期间多个项目的整理、合并、演进与多岗位表达，并保留按需制作整份简历的能力。

原版飞书简历样本只用于方法观察；本仓库没有重新读取、复制或公开那些简历，也不将原版样本数或既有程序测试数用作本 Skill 的写作质量证明。

## ASu-skills 参考

2026-10-08 核对上游 main，版本为 cf9eacba193ea08de169e30dcedb698202ad6f6b。实际读取并参考：

- [evidence-recap](https://github.com/Hisn00w/ASu-skills/blob/cf9eacba193ea08de169e30dcedb698202ad6f6b/skills/evidence-recap/SKILL.md)：将项目动作、交付阶段和效果证据分开。
- [project-guide](https://github.com/Hisn00w/ASu-skills/blob/cf9eacba193ea08de169e30dcedb698202ad6f6b/skills/project-guide/SKILL.md)：将源码机制转成外部读者能理解的技术表达，保留可追问的依据。
- [great-resume](https://github.com/Hisn00w/ASu-skills/blob/cf9eacba193ea08de169e30dcedb698202ad6f6b/skills/great-resume/SKILL.md)与 [claim-evidence-ledger](https://github.com/Hisn00w/ASu-skills/blob/cf9eacba193ea08de169e30dcedb698202ad6f6b/skills/great-resume/references/claim-evidence-ledger.md)：原始事实、候选措辞和职责边界跨版本保持一致。
- [make-resume](https://github.com/Hisn00w/ASu-skills/blob/cf9eacba193ea08de169e30dcedb698202ad6f6b/skills/make-resume/SKILL.md)与 [page-balance-qa](https://github.com/Hisn00w/ASu-skills/blob/cf9eacba193ea08de169e30dcedb698202ad6f6b/skills/make-resume/references/page-balance-qa.md)：文本提炼与文件交付按需处理，检查实际分页和可读性。

本版按实习项目沉淀的目标重写工作流程，不要求使用上游的固定章节数量、面试题数量或安装资源。ASu-skills 采用 MIT；[许可原文](asu-license.txt)保留上游版权声明，适用于上游参考材料，不替代本项目其他内容的授权约定。

## 示例

多岗位筛选示例依据授权项目总结、原作者对个人职责的确认，以及公开 JD-clean 的相关实现整理。没有复制候选人文本、内部飞书链接、身份标识或运行数据库；岗位版本的简历要点不是其他使用者的履历。

## 验证边界

Skill 结构与本地链接检查不证明简历事实。场景试用只能验证所给材料中的决策与输出；模板检查使用虚构内容，不能保证任意文本均为一页。原版浏览器检查不自动等于本版检查。真实简历生成后仍需核对事实与实际打印结果。

## 2026-10-08 本版检查

- skill-creator quick_validate 通过；本地 Markdown 引用无缺失，UI 元数据与 Skill 名称一致。
- 两个独立场景完成并由主 Agent 审阅：局部测试开发改写；多个实习子项目取舍与合并。试用保留个人边界、本地/历史验证和计划状态，没有采用材料明确否定的技术、收益或生产结果。
- 隔离 Chrome 使用虚构文本验证正文编辑、下载保存及重开，页面未出现脚本错误或外部资源请求。长英文项目标题和长链接未横向溢出。
- 实际生成 3 份测试 PDF（1 页、1 页、2 页），检查 A4 尺寸、文字可提取、工具栏与打印光标隐藏，并用 Poppler 渲染逐页复核。保存重开后正文相同，单页渲染与保存前哈希一致；多页中的全部结束标记保留，未见裁切或空白页。
- 项目示例定位到实际公开源码；没有将 JD-clean 历史程序测试数作为新 Skill 的质量指标，本轮没有重跑 JD-clean 流水线。

试用与渲染证据保存在本地忽略目录 .local/，不随公开同步发布。以上检查针对给定场景和当前模板，不代替未来真实简历的事实与排版核对。

## 2026-10-08 聊天自动整理改进

- 聊天入口支持直接生成项目与简历信息初稿，无需用户先填写项目卡。长导出可用 Python 标准库工具转为带原消息定位、角色、分支与覆盖说明的阅读分块；该工具不调用模型，也不执行聊天中的命令。
- 导入器 17 项回归通过，覆盖当前会话分支、历史顺序、消息角色、工具失败与截断、附件缺失、长中文文本、多会话、重复输入、未知格式和非空目录保护。另用虚构导出实际运行 CLI，生成 11 条事件的阅读材料。
- 两个独立的聊天入口试用完成并由主 Agent 回读审阅。真实聊天试用仅凭用户授权的两条聊天，归并同一筛选项目、采用明确确认的职责，另列未确认归属的工具制作经历，保留后续缺陷修复与历史验证范围。导出聊天试用处理后续否认，排除助手虚构的上线与收益、他人经历，以及尚未实施的方案。
- 两次试用均先交付候选经历、技术与贡献、来源账本和关键待确认项，没有要求补填完整表单。缺失公司、日期与个人职责未自动补齐；未读附件、截断输出和只有调用状态的工具结果在私有覆盖说明中列出。

真实聊天信息稿保存在已忽略的 outputs/，虚构输入与试用证据保存在 .local/，均不随公开同步发布。这些检查验证给定聊天范围的整理行为，不证明源项目当前的生产状态、个人能力或所有导出格式均受支持。

## 2026-10-09 ASu-skills 参考改造

本次只读核对上游 main，参考版本为 4306ec6aa1722b16ee8ff9a75a414eb5e04541ff。读取 README、入口清单、以下流程与 MIT 许可后，按本项目用途改写：

- [job-match](https://github.com/Hisn00w/ASu-skills/blob/4306ec6aa1722b16ee8ff9a75a414eb5e04541ff/skills/job-match/SKILL.md)：要求—证据矩阵、五种匹配状态、硬性门槛和可解释的投递建议。
- [evidence-recap](https://github.com/Hisn00w/ASu-skills/blob/4306ec6aa1722b16ee8ff9a75a414eb5e04541ff/skills/evidence-recap/SKILL.md)：问题、个人动作、阶段、结果与责任边界的证据组织。
- [great-resume](https://github.com/Hisn00w/ASu-skills/blob/4306ec6aa1722b16ee8ff9a75a414eb5e04541ff/skills/great-resume/SKILL.md)与 [claim-evidence-ledger](https://github.com/Hisn00w/ASu-skills/blob/4306ec6aa1722b16ee8ff9a75a414eb5e04541ff/skills/great-resume/references/claim-evidence-ledger.md)：同一原始事实跨任务交接，候选措辞不反向成为确认来源。

保留 distill-internship-projects 单入口与可独立复制的资源目录，按复盘、JD 匹配、经历改写与文件制作按需读取参考。没有复制上游九入口插件结构，也没有引入其浏览器投递、进度管理或外部调用。聊天导入器与 HTML 模板保持原实现，旧账本字段无需迁移；新增匹配稿引用已有稳定事实 ID。

新增岗位匹配稿与完全虚构的对照示例。上游版权声明继续保留于 [许可原文](asu-license.txt)。

本轮实际验证：

- skill-creator quick_validate 通过；17 份 Markdown 的 43 个本地引用无缺失，UI 名称与默认提示一致，主入口为 55 行。
- 项目既有聊天导入器的 17 项 unittest 回归通过。没有新增运行依赖；这些回归检查导入行为，不证明简历或匹配结论真实。
- 独立试用完成两个虚构场景，主 Agent 已回读：只做 JD 分析时保持条件式投递建议与本地测试范围；只复盘聊天时处理后续否认、局部修复、团队职责、计划功能与未读附件，没有生成简历或展开其他模式。
- 根据试用与回读，补充“未使用”不自动否定“了解”的判断，并将虚构示例中的真实缺口改为明确否认基本认知的材料。

本轮来源快照、结构结果、虚构输入与实际试用输出保存在已忽略的 .local/asu-refactor-20261009/。未用真实用户履历或在线招聘页面试用，本轮未重做 HTML/PDF 渲染；历史模板检查仍只属于其原记录范围。
