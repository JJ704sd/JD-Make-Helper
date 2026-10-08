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
