# AI Harness 入门与实践

> **素材来源**：`raw/pdf/AI Harness 入门与实践.pdf`
> **页数**：52（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 30,630 字符，其中汉字 8,829 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

万字详解！AIHarness入门与实践！一篇博文
给你讲透！​
HarnessAgent的基本概念​
1. 先说结论：AI应用开发正在从“会问AI”变成“会给AI搭工作台”​
 过去一年，很多人做AI应用开发的姿势是这样的：​
“帮我写一个登录页。”​
“帮我修一下这个bug。”​
“帮我生成一个Python爬虫。”​
“帮我把这个函数改成异步。”​
这类做法通常被叫作VibeCoding。大白话说，就是你把想法说出来，让AI顺着你的感觉往前写代
码。你不一定逐行看代码，也不一定一开始就把需求写得特别严谨。你更像是在和一个很快的程序员
聊天：你说一个大概方向，它先做一个版本；你试一下，不满意，再让它改。​

---

<!-- p.2 -->

VibeCoding的价值很明显：快。以前一个小工具可能要半天，现在十几分钟就能跑起来。以前你
不懂前端、不懂后端、不懂脚本，也许做不出来，现在你可以靠自然语言先做一个可用版本。​
但问题也很明显：快，不等于稳。能跑，不等于能上线。看起来能用，不等于边界条件正确。AI写
出来的代码，有时候像临时搭的棚子：遮雨可以，但不一定经得起长期使用。​
所以现在真正值得关注的变化，不是“AI会不会写代码”，而是：​
我们怎么让AI在一个可验证、可约束、可回滚、可观察的环境里写代码？​
这就是本文要讲的核心：HarnessEngineering。​
你可以先把它理解成一句话：​
HarnessEngineering不是教你写更玄的提示词，而是教你给AIAgent搭一个能干活、能自查、能
留痕、能被人类接管的工程环境。​
如果VibeCoding是“让AI凭感觉开车”，那HarnessEngineering就是“给AI修路、画线、装红
绿灯、加仪表盘、设限速、放安全员”。​
1. Harness到底是什么意思？​

---

<!-- p.3 -->

“Harness”这个词本来不是AI专有词。它在英文里有“马具、装备、把力量约束并利用起
来”的意思。放到软件工程里，我们经常听过一个词：testharness，测试夹具、测试套
件、测试环境。​
​
它的意思是：你不是只写一个函数，然后靠肉眼看结果；你要给这个函数配一套输入、输
出、断言、运行环境，用这套环境来判断它到底有没有做好。​
到了AIAgent时代，Harness的意思被扩展了。​
一个AICodingAgent不是单纯的模型。模型只是大脑。真正让它能干活的，是它周围的一整套东西：​
• 它能看到哪些文件；​
• 它能调用哪些工具；​
• 它能不能跑测试；​
• 它能不能改文件；​
• 它能不能访问网络；​
• 它改完以后怎么判断自己完成了；​
• 它失败以后怎么定位原因；​
• 它每一步操作有没有日志；​
• 它什么时候必须停下来问人；​
• 它的上下文怎么组织；​

---

<!-- p.4 -->

• 它的长期项目记忆放在哪里；​
• 它产生的变更怎么被审查和合并。​
这些东西加起来，就是一个Agent的Harness。​
所以，Harness不是单个提示词，也不是单个工具，而是模型和真实工程环境之间的“工作底座”。​
更准确一点说：​
Harness是包在AI模型外面的一层运行系统。它负责把用户目标变成可执行任务，把项目上下文喂
给模型，把模型输出转成工具调用，把工具结果反馈给模型，并用测试、权限、日志、审查机制判断
任务是否真的完成。​
这也是为什么同一个模型，在普通聊天窗口里表现一般，但放到Codex、ClaudeCode、Cursor、
Windsurf这类工程环境里，会显得强很多。不是模型突然换了脑子，而是它有了更好的工作台。​
2. HarnessAgent是什么？​
“HarnessAgent”这个词有两层意思，需要分开讲。​
第一层，是泛化意义上的harnessedagent，也就是“被Harness包起来的Agent”。比如一个
codingagent，它有如下能力：​
 • 读项目文件；​
• 搜索代码；​
• 修改代码；​

---

<!-- p.5 -->

• 运行shell命令；​
• 跑测试；​
• 读取失败日志；​
• 继续修复；​
• 生成变更说明；​
• 请求人类批准高风险操作。​
这类Agent的重点不是“它能聊天”，而是“它能在工具环境里循环执行任务”。这就已经不是传统
chatbot了，而是一个带工作流的执行体。​
第二层，是特定产品里的HarnessAgent。比如Harness.io这家公司提供的Harness平台里，有
WorkerAgents、AgentMarketplace、HarnessMCPServer等概念。它们面向DevOps、CI/CD、测
试、安全、成本优化等场景，可以让用户创建、配置和运行工作型Agent。你可以把它理解成“把智
能体放进软件交付流水线里”，例如PRreview、pipelinefailuresummarizer、IaCplansafety、
zero-dayremediation等。​
两者关系可以这样理解：​
• 泛化意义上的harnessagent：任何被工作底座包起来、能调用工具做事的AIAgent。​
• Harness.io里的WorkerAgent：一个具体平台产品里的Agent能力，主要服务软件交付、
DevOps、安全、测试等流程。​
本文主要讲第一种，也就是更通用的AI应用开发方法论；同时会穿插Harness.io这种具体平台如何落
地。​
3. 什么是HarnessEngineering？​
如果Harness是工作底座，那么HarnessEngineering就是“设计、实现、维护这个底座”的工程方
法。​
过去我们讲PromptEngineering，核心问题是：​
我应该怎么问AI，AI才能回答得更好？​
后来我们讲ContextEngineering，核心问题变成：​
我应该给AI什么上下文，AI才能在正确的信息里工作？​
而HarnessEngineering又往前走了一步：​
我应该给AI什么样的任务环境、工具边界、验证机制、状态管理和反馈循环，AI才能持续、可靠、
可审查地完成复杂任务？​
这三者的层次不同。​

---

<!-- p.6 -->

3.1PromptEngineering：把话说清楚​
比如：​
代码块​
你是一个资深 Python
工程师。请帮我实现一个订单折扣函数，要求：​
1.
满 100
减 10
；​
2. VIP
用户额外 95
折；​
3.
返回值保留两位小数。​
这已经比“帮我写个折扣函数”好多了。​
但它仍然主要依赖模型一次性生成正确答案。​
3.2ContextEngineering：把资料给够​
比如你告诉AI：​
代码块​
这是我们项目的目录结构：​
src/​
pricing/​
discount.py​
tests/​
test_discount.py​
​
这是现有代码：​
...​
​
这是我们的编码规范：​
-
金额统一使用 Decimal
；​
-
不允许用 float
处理价格；​
-
测试必须覆盖普通用户、VIP
用户、边界值。​
这样AI不再是凭空写代码，而是基于项目真实上下文来写。​
3.3HarnessEngineering：把工作环境搭好​
再进一步，你不仅给它资料，还给它一套可以执行的流程：​
代码块​
你可以：​
1.
读取 src/
和 tests/
下的文件；​
2.
修改业务代码和测试代码；​
1
2
3
4
1
2
3
4
5
6
7
8
9
10
11
12
13
14
1
2
3

---

<!-- p.7 -->

3.
运行 pytest
；​
4.
如果测试失败，读取失败日志并继续修；​
5.
最终必须输出：​
-
修改了哪些文件；​
-
为什么这么改；​
- pytest
是否通过；​
-
是否存在未覆盖风险。​
你不可以：​
1.
删除数据库；​
2.
访问外部网络；​
3.
修改 pyproject.toml
以外的构建配置；​
4.
在测试没通过时声称完成。​
这就是HarnessEngineering的味道。​
它不是只靠“说得更好”，而是靠：​
• 工具；​
• 权限；​
• 反馈；​
• 测试；​
• 日志；​
• 状态；​
• 结构化输出；​
• 人类审批。​
让AI进入一个工程闭环。​
4. 为什么VibeCoding不够？​
VibeCoding很适合从0到1。比如你要做：​
• 一个内部小工具；​
• 一个演示Demo；​
• 一个一次性脚本；​
• 一个低风险页面；​
• 一个探索性原型；​
• 一个产品想法验证。​
你用自然语言和AI对话，很快就能看到东西。这种体验过去没有，所以它很迷人。​
4
5
6
7
8
9
10
11
12
13
14
15

---

<!-- p.8 -->

但当项目开始变复杂，VibeCoding会遇到几个硬问题。​
4.1需求会漂​
你一开始说“做个记账工具”，AI可能会给你做一个很漂亮的页面。你继续说“加个分类统计”，它
又加了图表。你再说“支持多人协作”，它可能开始乱改数据结构。到最后，你自己都不清楚这个项
目原来的核心目标是什么。​
这不是AI特有的问题。人类团队也会这样。区别是AI写得太快，漂得也太快。​
4.2上下文会爆​
AIAgent做复杂任务时，会读很多文件、跑很多命令、产生很多日志、经历多轮对话。上下文窗口再
大，也不是无限的。上下文越乱，模型越容易忘记早期约束，或者把过期信息当成最新事实。​
所以工程里不能把所有东西都塞进一个大提示词。要有文档地图，要有短入口，要有可检索的项目知
识库，要有“系统事实来源”。​
4.3代码能跑，但不一定对​
一个函数在某个样例下能跑，不代表它满足所有业务边界。​
比如金额计算，最怕这些问题：​
• float精度误差；​
• 四舍五入规则错误；​
• 折扣顺序错误；​
• 边界值99.99和100.00处理错误；​
• 负数金额没有拒绝；​
• 空订单没有处理；​
• VIP和普通用户逻辑混在一起。​
如果没有测试，AI很容易写出“看起来对”的代码。​
4.4AI很会“自信地完成”​
很多Agent会在没有真正验证时说“已完成”。这对工程来说非常危险。人类工程师至少知道自己有
没有跑测试，但Agent如果没有被要求跑测试，或者没有权限跑测试，它可能只靠代码表面判断。​
HarnessEngineering的关键，就是不要让“模型觉得完成了”成为完成标准。​
真正的完成标准应该是：​
• 测试通过；​
• lint通过；​
• typecheck通过；​

---

<!-- p.9 -->

• 构建通过；​
• 关键路径验证通过；​
• 人类审查通过；​
• 变更说明清楚；​
• 可回滚。​
4.5安全边界不清楚​
如果你给Agent一个shell，它就可能运行命令。如果它能运行命令，就可能读文件、删文件、发请
求、安装包、修改配置。不是说Agent一定会作恶，而是复杂任务里总会有误操作。​
所以Harness必须有权限边界：​
• 哪些文件可读；​
• 哪些文件可写；​
• 哪些命令可执行；​
• 是否允许联网；​
• 是否允许访问密钥；​
• 是否允许执行部署；​
• 哪些操作必须人类批准。​
没有边界的Agent，不适合进入真实工程。​
5. 从VibeCoding到HarnessEngineering的五个阶段​

---

<!-- p.10 -->

我们可以把AI应用开发的成熟度分成五个阶段。​
阶段0：纯聊天写代码​
你打开一个聊天窗口，说：​
代码块​
帮我写一个 Flask
应用。​
AI给你一段代码。你复制到本地跑。​
优点：简单。​
缺点：没有项目上下文，没有工具调用，没有自动验证，没有工程闭环。​
适合：学习、试错、小片段代码。​
阶段1：带上下文的辅助编码​
你把文件、错误日志、目录结构贴给AI，让它帮你改。​
优点：比纯聊天准确很多。​
缺点：上下文仍然靠手动维护，AI不一定能自己验证。​
适合：小bug、小函数、小模块改造。​
阶段2：Agent能读写文件和运行命令​
1

---

<!-- p.11 -->

你使用Codex、ClaudeCode、CursorAgent、WindsurfAgent等工具，让Agent直接在项目里工
作。​
它可以：​
• 读文件；​
• 搜索代码；​
• 改多个文件；​
• 跑测试；​
• 根据日志继续修。​
优点：效率大幅提升。​
缺点：如果项目没有清晰文档、测试和权限边界，Agent会很容易迷路。​
适合：中小型功能开发、重构、测试补齐、脚本自动化。​
阶段3：工程化Harness​
你开始给Agent明确的工作台：​
• AGENTS.md
或 CLAUDE.md
；​
• 项目架构文档；​
• 测试命令；​
• lint命令；​
• typecheck命令；​
• donecriteria；​
• PR模板；​
• 代码规范；​
• 权限策略；​
• sandbox；​
• trace日志；​
• reviewchecklist。​
优点：Agent不再靠感觉做事，而是在项目规则里工作。​
缺点：需要团队维护这些规则。​
适合：真实产品开发、团队协作、CI/CD自动化。​
阶段4：可观测、可评估、自我改进的Harness​
你进一步把Agent的每次运行都记录下来：​

---

<!-- p.12 -->

• 任务输入；​
• 读取了哪些文件；​
• 调用了哪些工具；​
• 哪一步失败；​
• 怎样修复；​
• 测试结果；​
• 人类反馈；​
• 最终是否合并；​
• 是否引入回归。​
然后把这些trace转成evals，反过来改进Harness。​
这时你不只是“用Agent写代码”，你是在运营一个“Agent工程系统”。​
优点：可持续改进。​
缺点：建设成本更高。​
适合：平台团队、AI原生研发团队、大型工程组织。​
6. HarnessEngineering的核心组件​
一个成熟的Harness，至少应该包含下面这些模块。​

---

<!-- p.13 -->

6.1任务规格：让目标别漂​
任务规格不是一句“做个功能”。它应该包括：​
代码块​
# Task Spec​
​
## Goal​
实现订单折扣计算。​
​
## Non-goals​
不做优惠券系统。​
不接入支付。​
不修改数据库结构。​
​
## Inputs​
- items:
商品列表​
- user_type: normal
或 vip​
​
## Rules​
-
满 100
减 10
；​
- VIP
在满减后额外 95
折；​
-
金额使用 Decimal
；​
-
返回保留两位小数；​
-
负数价格必须报错。​
​
## Done When​
- pytest
全部通过；​
-
新增边界测试；​
-
不引入 float
；​
-
输出变更说明。​
这类规格很朴素，但非常有用。它把“感觉”变成“合同”。​
6.2上下文选择：不要把所有东西都塞给AI​
很多人以为上下文越多越好。实际不是。上下文是稀缺资源。你给太多，模型会抓不住重点。​
更好的做法是：​
• 根目录放一个短的 AGENTS.md
；​
• AGENTS.md
只做地图；​
• 详细内容放到 docs/
；​
• 让Agent按需读取；​
• 每个文档有明确用途；​
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26

---

<!-- p.14 -->

• 文档保持短、准、可验证。​
比如：​
代码块​
# AGENTS.md​
​
##
项目简介​
这是一个订单和价格计算服务。​
​
##
先读这些​
- docs/architecture.md
：模块边界​
- docs/pricing-rules.md
：价格规则​
- docs/testing.md
：测试命令和测试策略​
​
##
常用命令​
- pytest​
- ruff check .​
- mypy src​
​
##
完成标准​
任何改动都必须通过 pytest
。​
涉及金额计算时必须新增边界测试。​
这比一个几千行的大说明靠谱得多。​
6.3工具访问：工具少而精，比工具多更重要​
Agent最怕什么？不是没有工具，而是工具太多、接口太碎、语义太复杂。​
一个好的Harness应该给Agent提供少量、稳定、可组合的工具。例如：​
• read_file(path)
​
• write_file(path, content)
​
• search_code(query)
​
• run_tests(command)
​
• run_lint(command)
​
• git_diff()
​
• create_pr(title, body)
​
工具越像Unix命令，越容易组合。工具越像“200个业务API摆在面前”，Agent越容易选错。
6.4项目记忆：把重要事实写到仓库，而不是留在聊天里​
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18

---

<!-- p.15 -->

Agent的对话会结束，上下文会压缩，记忆会丢。但仓库里的文件会留下来。​
所以重要事实应该沉淀成文件：​
代码块​
docs/​
architecture.md​
decisions/​
0001-use-decimal-for-money.md​
0002-discount-order.md​
testing.md​
known-issues.md​
tech-debt.md​
这就像给Agent留路标。下一次它进来，不用从头问。​
6.5状态管理：复杂任务必须有进度文件​
长任务不能只靠对话记录。最好让Agent写一个计划文件：​
代码块​
# exec-plans/2026-05-pricing-refactor.md​
​
## Goal​
重构 pricing
模块，统一 Decimal
金额计算。​
​
## Milestones​
- [x]
梳理现有价格入口​
- [x]
增加边界测试​
- [ ]
替换 float
计算​
- [ ]
跑全量测试​
- [ ]
更新文档​
​
## Current Status​
已发现 cart.py
和 discount.py
中存在 float
计算。​
​
## Risks​
-
订单导出 CSV
可能依赖旧格式。​
这样就算上下文被压缩，Agent也能回到这个文件继续工作。​
6.6验证机制：不要相信“我觉得对”​
验证机制是Harness的灵魂。​
1
2
3
4
5
6
7
8
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17

---

<!-- p.16 -->

至少要有：​
• 单元测试；​
• 集成测试；​
• lint；​
• typecheck；​
• build；​
• snapshot；​
• goldenfile；​
• APIcontracttest；​
• 数据迁移dryrun；​
• 回归测试。​
对Agent来说，最有价值的反馈不是“你写得不错”，而是：​
代码块​
FAILED tests/test_discount.py::test_vip_discount​
Expected Decimal("85.50"), got Decimal("90.25")​
这种反馈非常清楚。Agent能基于它继续修。​
6.7权限和沙箱：让Agent在围栏里跑​
Agent需要自由，但不能无限自由。​
一个实际项目里可以分几层权限：​
代码块​
Level 0
：只读​
-
允许读文件、搜索代码​
-
不允许改文件、不允许执行命令​
​
Level 1
：本地修改​
-
允许改工作区文件​
-
允许跑测试和 lint​
-
不允许联网​
-
不允许访问密钥​
​
Level 2
：受控外部访问​
-
允许访问指定 MCP
工具​
-
高风险操作需要确认​
1
2
1
2
3
4
5
6
7
8
9
10
11
12
13

---

<!-- p.17 -->

​
Level 3
：CI/CD
自动化​
-
允许创建 PR​
-
允许触发 CI​
-
不允许直接部署生产​
​
Level 4
：有限自治​
-
在明确策略下自动修复、开 PR
、请求 review​
-
生产变更仍需人类批准​
不要一上来就给Agent生产权限。先让它在低风险环境里证明自己。​
6.8可观测性：每一步都要能复盘​
Agent失败不可怕。可怕的是失败以后你不知道它为什么失败。​
所以Harness应该记录：​
代码块​
{​
"task_id": "pricing-discount-001",​
"started_at": "2026-05-28T10:00:00Z",​
"steps": [​
{​
"type": "read_file",​
"path": "src/cart.py"​
},​
{​
"type": "write_file",​
"path": "src/cart.py"​
},​
{​
"type": "run_tests",​
"command": "pytest",​
"exit_code": 1,​
"summary": "test_vip_discount failed"​
},​
{​
"type": "write_file",​
"path": "src/cart.py"​
},​
{​
"type": "run_tests",​
"command": "pytest",​
"exit_code": 0​
}​
14
15
16
17
18
19
20
21
22
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27

---

<!-- p.18 -->

],​
"final_status": "passed"​
}​
这类trace对调试、评估和团队信任都很重要。​
6.9人类接管：不是全自动才高级​
很多人把AIAgent想成“完全自动”。但真实工程里，高级不是完全自动，而是该自动的自动，该停
的停。​
比如：​
• 改测试：自动；​
• 跑lint：自动；​
• 修改核心支付逻辑：需要review；​
• 删除数据：必须拒绝；​
• 改CI/CD权限：必须审批；​
• 访问生产密钥：不允许。​
HarnessEngineering的目标不是让人消失，而是让人从“手写每一行代码”变成“设计规则、审查结
果、处理关键决策”。​
7. 一个可以验证的最小Harness案例​
下面这个案例不依赖真实LLM。它用一个“假Agent提案”来模拟AI写补丁，然后用Harness来决定
是否接受补丁。​
为什么不用真实模型？因为我们要让案例可验证。真实模型输出每次可能不同，不适合做入门示范。
这个例子重点是Harness思路：不是谁写了代码重要，而是代码必须经过验证才算完成。​
7.1项目结构​
代码块​
mini-harness-demo/​
src/​
cart.py​
tests/​
test_cart.py​
agent_harness.py​
pyproject.toml​
28
29
30
1
2
3
4
5
6
7

---

<!-- p.19 -->

7.2初始业务代码： src/cart.py
​
代码块​
from decimal import Decimal​
​
​
def calculate_total(items, user_type="normal"):​
"""​
items: [{"price": "60.00", "qty": 2}]​
rules:​
- subtotal >= 100: minus 10​
- vip user: 5% off after threshold discount​
- return Decimal with 2 decimal places​
"""​
total = 0.0​
​
for item in items:​
total += float(item["price"]) * item["qty"]​
​
if total >= 100:​
total -= 10​
​
if user_type == "vip":​
total = total * 0.95​
​
return Decimal(str(round(total, 2)))​
这段代码能跑，但有问题：金额用了 float
。在真实业务里，金额不要用float，因为会有精度问
题。​
7.3测试代码： tests/test_cart.py
​
代码块​
from decimal import Decimal​
import pytest​
​
from src.cart import calculate_total​
​
​
def test_normal_user_threshold_discount():​
items = [{"price": "60.00", "qty": 2}]​
assert calculate_total(items) == Decimal("110.00")​
​
​
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
1
2
3
4
5
6
7
8
9
10
11

---

<!-- p.20 -->

def test_vip_discount_after_threshold_discount():​
items = [{"price": "60.00", "qty": 2}]​
assert calculate_total(items, user_type="vip") == Decimal("104.50")​
​
​
def test_no_float_precision_issue():​
items = [​
{"price": "0.10", "qty": 3},​
{"price": "0.20", "qty": 1},​
]​
assert calculate_total(items) == Decimal("0.50")​
​
​
def test_negative_price_rejected():​
items = [{"price": "-1.00", "qty": 1}]​
with pytest.raises(ValueError):​
calculate_total(items)​
7.4Harness脚本： agent_harness.py
​
代码块​
import json​
import shutil​
import subprocess​
from datetime import datetime​
from pathlib import Path​
​
​
ROOT = Path(__file__).parent​
TARGET_FILE = ROOT / "src" / "cart.py"​
TRACE_FILE = ROOT / "trace.json"​
​
​
PATCH_PROPOSAL = '''from decimal import Decimal, ROUND_HALF_UP​
​
​
def money(value):​
return Decimal(str(value)).quantize(Decimal("0.01"),
rounding=ROUND_HALF_UP)​
​
​
def calculate_total(items, user_type="normal"):​
"""​
items: [{"price": "60.00", "qty": 2}]​
rules:​
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23

---

<!-- p.21 -->

- subtotal >= 100: minus 10​
- vip user: 5% off after threshold discount​
- return Decimal with 2 decimal places​
"""​
total = Decimal("0.00")​
​
for item in items:​
price = Decimal(str(item["price"]))​
qty = int(item["qty"])​
​
if price < 0:​
raise ValueError("price must not be negative")​
​
if qty < 0:​
raise ValueError("qty must not be negative")​
​
total += price * qty​
​
if total >= Decimal("100.00"):​
total -= Decimal("10.00")​
​
if user_type == "vip":​
total = total * Decimal("0.95")​
​
return money(total)​
'''​
​
​
class Harness:​
def __init__(self):​
self.trace = {​
"task": "fix money calculation without float",​
"started_at": datetime.utcnow().isoformat() + "Z",​
"steps": [],​
}​
​
def log(self, step_type, **kwargs):​
record = {"type": step_type, **kwargs}​
self.trace["steps"].append(record)​
print(json.dumps(record, ensure_ascii=False))​
​
def run(self, command):​
self.log("run_command", command=command)​
result = subprocess.run(​
command,​
cwd=ROOT,​
shell=True,​
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
49
50
51
52
53
54
55
56
57
58
59
60
61
62
63
64
65
66
67
68
69
70

---

<!-- p.22 -->

text=True,​
stdout=subprocess.PIPE,​
stderr=subprocess.STDOUT,​
)​
self.log(​
"command_result",​
exit_code=result.returncode,​
output_tail=result.stdout[-1200:],​
)​
return result.returncode == 0​
​
def read_file(self, path):​
self.log("read_file", path=str(path.relative_to(ROOT)))​
return path.read_text(encoding="utf-8")​
​
def write_file(self, path, content):​
allowed = path.resolve() == TARGET_FILE.resolve()​
if not allowed:​
raise PermissionError(f"Not allowed to write {path}")​
​
self.log("write_file", path=str(path.relative_to(ROOT)))​
path.write_text(content, encoding="utf-8")​
​
def save_trace(self, status):​
self.trace["finished_at"] = datetime.utcnow().isoformat() + "Z"​
self.trace["final_status"] = status​
TRACE_FILE.write_text(​
json.dumps(self.trace, ensure_ascii=False, indent=2),​
encoding="utf-8",​
)​
​
def execute(self):​
backup = TARGET_FILE.with_suffix(".py.bak")​
shutil.copyfile(TARGET_FILE, backup)​
​
try:​
self.read_file(TARGET_FILE)​
​
baseline_ok = self.run("python -m pytest -q")​
if baseline_ok:​
self.log("baseline", message="tests already pass")​
self.save_trace("already_passed")​
return​
​
self.write_file(TARGET_FILE, PATCH_PROPOSAL)​
​
fixed_ok = self.run("python -m pytest -q")​
71
72
73
74
75
76
77
78
79
80
81
82
83
84
85
86
87
88
89
90
91
92
93
94
95
96
97
98
99
100
101
102
103
104
105
106
107
108
109
110
111
112
113
114
115
116
117

---

<!-- p.23 -->

if not fixed_ok:​
shutil.copyfile(backup, TARGET_FILE)​
self.log("rollback", reason="tests failed after patch")​
self.save_trace("failed_and_rolled_back")​
return​
​
self.run("python -m py_compile src/cart.py")​
self.log("done", message="patch accepted because tests passed")​
self.save_trace("passed")​
​
finally:​
if backup.exists():​
backup.unlink()​
​
​
if __name__ == "__main__":​
Harness().execute()​
7.5 pyproject.toml
​
代码块​
[tool.pytest.ini_options]​
pythonpath = ["."]​
testpaths = ["tests"]​
7.6运行方式​
代码块​
pip install pytest​
python agent_harness.py​
预期输出类似：​
代码块​
{"type": "read_file", "path": "src/cart.py"}​
{"type": "run_command", "command": "python -m pytest -q"}​
{"type": "command_result", "exit_code": 1, "output_tail": "..."}​
{"type": "write_file", "path": "src/cart.py"}​
{"type": "run_command", "command": "python -m pytest -q"}​
{"type": "command_result", "exit_code": 0, "output_tail": "4 passed ..."}​
{"type": "run_command", "command": "python -m py_compile src/cart.py"}​
118
119
120
121
122
123
124
125
126
127
128
129
130
131
132
133
134
1
2
3
1
2
1
2
3
4
5
6
7

---

<!-- p.24 -->

{"type": "done", "message": "patch accepted because tests passed"}​
同时生成 trace.json
，记录这次Agent修复过程。​
7.7这个例子体现了什么？​
这个小例子很简单，但它已经有HarnessEngineering的核心味道：​
第一，Agent不能随便改任何文件。脚本里限制它只能写 src/cart.py
。​
第二，修改不能靠嘴说完成，必须跑测试。​
第三，失败要回滚。补丁如果跑不通，就恢复原文件。​
第四，全过程有trace。以后你可以复盘它读了什么、改了什么、跑了什么命令、为什么接受或拒绝补
丁。​
第五，完成标准是外部验证，不是模型自信。​
这就是HarnessEngineering最重要的思想：​
让AI写代码不是难点，让AI写出来的代码被可靠验证，才是难点。​
8. 把这个最小Harness扩展成真实工程系统​
上面的脚本只是玩具版本。真实项目可以逐步加东西。​
8.1加入 AGENTS.md
​
代码块​
# AGENTS.md​
​
## Project​
This project handles cart pricing and discount calculation.​
​
## Rules​
- Money must use Decimal.​
- Do not use float for price calculation.​
- Any pricing change must include tests.​
- Do not change public function names unless requested.​
​
## Commands​
- Run tests: python -m pytest -q​
- Compile check: python -m py_compile src/cart.py​
​
## Done When​
- All tests pass.​
8
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17

---

<!-- p.25 -->

- No float is used for money.​
- Edge cases are covered.​
Agent每次进入仓库先读这个文件。​
8.2加入静态扫描​
你可以增加一个简单检查：如果业务代码里出现 float(
，直接失败。​
代码块​
def check_no_float_for_money():​
content = TARGET_FILE.read_text(encoding="utf-8")​
forbidden = ["float("]​
for token in forbidden:​
if token in content:​
raise AssertionError(f"Forbidden token found: {token}")​
然后在Harness里跑：​
代码块​
check_no_float_for_money()​
这就是deterministiccheck。它不靠模型判断，规则明确。​
8.3加入PR输出​
Agent完成后，不只是说“好了”，而是生成：​
代码块​
## Summary​
- Replaced float-based money calculation with Decimal.​
- Added validation for negative price and quantity.​
- Preserved discount order: threshold discount first, VIP discount second.​
​
## Verification​
- python -m pytest -q: passed​
- python -m py_compile src/cart.py: passed​
​
## Risks​
- Currency-specific rounding rules are not yet configurable.​
18
19
1
2
3
4
5
6
1
1
2
3
4
5
6
7
8
9
10
11

---

<!-- p.26 -->

这个输出可以进入PR描述。​
8.4加入CIGate​
本地Harness只是第一关。进入团队后，还要接CI：​
代码块​
name: pricing-check​
​
on:​
pull_request:​
paths:​
- "src/**"​
- "tests/**"​
​
jobs:​
test:​
runs-on: ubuntu-latest​
steps:​
- uses: actions/checkout@v4​
- uses: actions/setup-python@v5​
with:​
python-version: "3.11"​
- run: pip install pytest​
- run: python -m pytest -q​
Agent可以开PR，但CI不通过就不能合并。​
8.5加入人工审批点​
比如：​
代码块​
如果改动涉及 src/payment/
或 migrations/
：​
- Agent
可以提出 patch
；​
- Agent
可以跑测试；​
- Agent
不允许自动合并；​
-
必须由 human reviewer
审查。​
这类规则比“相信AI”靠谱得多。​
9. HarnessAgent在AI应用开发里的典型用法
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
1
2
3
4
5

---

<!-- p.27 -->

很多人以为HarnessEngineering只适合代码生成。其实不是。只要你的AI应用需要“多步执行、调
用工具、依赖外部状态、需要验证结果”，就需要Harness。​
9.1代码修复Agent​
输入：​
代码块​
线上出现错误：Decimal conversion syntax
。​
请定位原因、修复、补测试。​
Harness提供：​
• 读取日志工具；​
• 搜索代码工具；​
• 修改文件工具；​
• 测试工具；​
• diff输出；​
• PR创建工具。​
完成标准：​
• 新增复现测试；​
• 修复后测试通过；​
• 输出根因分析。​
9.2PRReviewAgent​
输入：​
代码块​
审查这个 PR
是否有安全、性能、架构问题。​
Harness提供：​
• gitdiff；​
• changedfiles；​
• 代码规范；​
• 安全checklist；​
1
2
1

---

<!-- p.28 -->

• 历史架构决策；​
• 评论API。​
完成标准：​
• 只评论具体文件和行；​
• 不输出泛泛建议；​
• 高风险问题必须说明影响和修复建议；​
• 不阻塞低风险风格问题。​
9.3数据分析Agent​
输入：​
代码块​
分析 2026
年 Q1
用户留存下降原因。​
Harness提供：​
• 查询只读数据仓库；​
• 数据字典；​
• 指标口径；​
• Pythonnotebook；​
• 图表生成；​
• 结果校验；​
• 敏感字段脱敏。​
完成标准：​
• SQL可复现；​
• 指标口径引用明确；​
• 图表有数据来源；​
• 结论和证据对应；​
• 不泄漏个人隐私数据。​
9.4运维排障Agent​
输入：​
代码块​
1

---

<!-- p.29 -->

API
错误率从 1%
上升到 8%
，帮我定位。​
Harness提供：​
• logs；​
• metrics；​
• tracing；​
• deployhistory；​
• incidentrunbook；​
• rollback工具；​
• 权限审批。​
完成标准：​
• 找出时间线；​
• 关联最近变更；​
• 给出可能根因；​
• 提供低风险缓解建议；​
• 回滚必须人工确认。​
9.5文档维护Agent​
输入：​
代码块​
根据最新代码更新 API
文档。​
Harness提供：​
• OpenAPIspec；​
• 代码扫描；​
• 文档目录；​
• markdownlint；​
• previewbuild。​
完成标准：​
• 文档和接口一致；​
1
1

---

<!-- p.30 -->

• 示例能运行；​
• 链接不失效；​
• PR描述说明变更范围。​
10. Harness.ioWorkerAgents怎么理解？​
如果你用的是Harness.io这个平台，它的WorkerAgents可以看成一种面向软件交付流程的Agent运
行机制。​
它的典型特点包括：​
• 在项目范围里创建和管理Agent；​
• 可以从Marketplace使用预置Agent；
• 可以fork后定制；​
• 可以写Agentinstructions；​
• 可以配置inputs、environmentvariables、MCPconnectors；​
• 可以让Agent进入pipeline；​
• 可以做PRreview、pipelinefailuresummarizer、IaCsafety、codecoverage、manifest
remediation等任务；​
• 可以通过HarnessAIChat、IDE或HarnessMCPServer创建和管理Agent。​
换句话说，它把Agent放在CI/CD和DevOps的上下文里，而不是让Agent只停留在聊天窗口里。​
一个示意性的Agent配置可能长这样：​
代码块​
agent:​
name: PR Reviewer Agent​
description: Review pull requests for security, schema, and architecture
risks.​
instructions: |​
You are a strict but practical PR reviewer.​
Focus on:​
- security risks​
- breaking API changes​
- database migration safety​
- missing tests​
Do not comment on minor style issues unless they affect readability.​
inputs:​
- name: pull_request_url​
type: string​
required: true​
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15

---

<!-- p.31 -->

tools:​
- type: mcp​
name: github​
- type: mcp​
name: harness​
output:​
format: markdown​
requirements:​
- include risk level​
- include file references​
- include suggested fixes​
注意，这只是帮助理解的示意，不是让你照抄到生产。真正使用时要以平台当前文档和你的组织权限
模型为准。​
它背后的思想和本文讲的一样：​
Agent不是孤零零的聊天机器人，而是嵌进工程流程里的工作单元。​
11. MCP和HarnessEngineering的关系​
MCP，全称ModelContextProtocol，可以理解成“AI应用连接外部工具和数据源的一种标准接
口”。​
如果把Agent比作一个会思考的操作员，那么MCP就像一组标准插口。通过这些插口，Agent可以连
接：​
• 文件系统；​
• 数据库；​
• GitHub；​
• Jira；​
• Slack；​
• GoogleDrive；​
• Figma；​
• 内部API；​
• 搜索服务；​
• 部署平台；​
• 监控平台。​
MCP和HarnessEngineering的关系是：​
16
17
18
19
20
21
22
23
24
25
26

---

<!-- p.32 -->

• MCP解决“工具怎么标准化接入”的问题；​
• HarnessEngineering解决“工具接入后怎么安全、可靠、可验证地使用”的问题。​
也就是说，有MCP不等于有好Harness。你可以给Agent接100个MCP工具，但如果没有权限、验
证和任务边界，它仍然可能迷路。​
好的Harness会对MCP工具做几件事：​
第一，减少工具数量。不是所有工具都给Agent，而是按任务给最少必要工具。​
第二，给工具加说明。Agent要知道这个工具适合什么场景，输入输出是什么。​
第三，给工具加权限。读和写分开，高风险操作需要审批。​
第四，记录工具调用。以后可以复盘Agent做了什么。​
第五，给工具结果做结构化。不要让Agent在一大坨日志里猜重点。​
12. 从“提示词文件”到“仓库知识系统”​
很多团队一开始用Agent，会写一个巨大的 AGENTS.md
或 CLAUDE.md
。里面什么都有：​
• 项目背景；​
• 架构说明；​
• 编码规范；​
• API说明；​
• 数据库说明；​
• 测试命令；​
• 部署步骤；​
• 常见坑；​
• 产品规划；​
• 历史债务；​
• 甚至团队偏好。​
这样做前期有用，但很快会变成垃圾堆。​
更好的做法是：入口短，知识分层。​
代码块​
AGENTS.md​
docs/​
architecture.md​
testing.md​
1
2
3
4

---

<!-- p.33 -->

coding-style.md​
product/​
pricing.md​
checkout.md​
decisions/​
0001-money-decimal.md​
0002-api-versioning.md​
runbooks/​
incident-api-error-rate.md​
AGENTS.md
只告诉Agent去哪里找。​
例如：​
代码块​
# AGENTS.md​
​
## Start Here​
Read this file first. It is a map, not the full manual.​
​
## Architecture​
See docs/architecture.md.​
​
## Pricing Rules​
See docs/product/pricing.md.​
​
## Testing​
See docs/testing.md.​
​
## Decisions​
Before changing money calculation, read:​
- docs/decisions/0001-money-decimal.md​
​
## Done Criteria​
- tests pass​
- lint passes​
- docs updated if behavior changed​
- PR summary includes verification result​
这种结构有几个好处：​
• 上下文更省；​
• 文档更容易维护；​
• Agent更容易按需读取；​
5
6
7
8
9
10
11
12
13
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23

---

<!-- p.34 -->

• 规则可以被测试；​
• 过期内容更容易发现；​
• 团队成员也能看懂。​
13. HarnessEngineering和传统软件工程不是对立的​
有些人会把AIcoding说得像“传统软件工程要被淘汰”。这很危险。​
现实更可能是：传统软件工程里的很多好习惯，会在AIAgent时代变得更重要。​
比如：​
• 清晰的模块边界；​
• 自动化测试；​
• 类型系统；​
• CI/CD；​
• codereview；​
• 文档；​
• ADR；​
• 可观测性；​
• 权限控制；​
• 灰度发布；​
• 回滚机制。​
以前这些东西是为了帮助人类团队协作。现在它们还多了一个作用：帮助Agent正确工作。​
一个没有测试、没有文档、没有边界、没有CI的项目，人类维护起来已经困难；让Agent维护，只会
更乱。​
所以HarnessEngineering不是“反工程”，而是“把工程纪律变成Agent的工作环境”。​
14. Agent-first开发里，工程师的角色怎么变？​
在VibeCoding阶段，工程师像一个“AI指挥员”：​
代码块​
写这个。​
改那里。​
报错了，修一下。​
1
2
3

---

<!-- p.35 -->

再美化一下。​
在HarnessEngineering阶段，工程师更像一个“系统设计者”和“质量负责人”。​
你要关心：​
• 需求如何表达成规格；​
• 项目知识如何组织；​
• Agent能用哪些工具；​
• 哪些操作需要审批；​
• 怎样验证完成；​
• 怎样记录过程；​
• 怎样评估质量；​
• 怎样让失败经验沉淀到系统里。​
也就是说，工程师不一定逐行写代码，但要对系统结果负责。​
未来很可能出现一种新型工程能力：​
不只是会写代码，而是会设计一个让Agent稳定产出好代码的环境。​
这就是HarnessEngineering的真正价值。​
15. 一个真实团队可以怎么落地？​
如果你现在带一个小团队，想从VibeCoding走向HarnessEngineering，不建议一上来搞很重的平
台。可以分四步走。​
第一步：补最小项目上下文​
先加三个文件：​
代码块​
AGENTS.md​
docs/architecture.md​
docs/testing.md​
AGENTS.md
写：​
代码块​
# AGENTS.md​
4
1
2
3
1

---

<!-- p.36 -->

​
## Project​
一句话说明项目。​
​
## Read Before Coding​
- docs/architecture.md​
- docs/testing.md​
​
## Commands​
- install:​
- test:​
- lint:​
- typecheck:​
​
## Rules​
-
不要改哪些目录​
-
关键业务规则​
-
代码风格​
​
## Done When​
-
测试通过​
- lint
通过​
-
输出变更说明​
别写太长。先让Agent不迷路。​
第二步：把“完成标准”机器化​
不要只写：​
代码块​
代码质量要好。​
要写成可执行命令：​
代码块​
python -m pytest -q​
npm run lint​
npm run typecheck​
npm run build​
能机器判断，就不要靠感觉判断。​
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
1
1
2
3
4

---

<!-- p.37 -->

第三步：把Agent变更统一走PR​
不要让Agent直接改主分支。推荐：​
• 每个任务一个branch；​
• Agent提交diff；​
• CI跑；​
• 人类review；​
• 合并。​
PR模板可以这样写：​
代码块​
## What changed?​
​
## Why?​
​
## Verification​
- [ ] Tests passed​
- [ ] Lint passed​
- [ ] Typecheck passed​
- [ ] Manual check completed​
​
## Risk​
Low / Medium / High​
​
## Rollback​
How to rollback this change?​
第四步：记录失败并改进Harness​
每次Agent出错，不要只骂模型。要问：​
• 是任务没写清楚？​
• 是上下文缺了？​
• 是工具太多？​
• 是没有测试？​
• 是权限太大？​
• 是日志太乱？​
• 是完成标准不明确？​
• 是旧文档误导了它？​
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15

---

<!-- p.38 -->

然后把经验沉淀进：​
• AGENTS.md
；​
• docs/testing.md
；​
• 新测试；​
• 新lintrule；​
• 新审批规则；​
• 新runbook；​
• 新evalcase。​
这就是闭环。​
16. 如何评价一个Harness好不好？​
可以用下面这张表。​
如果你的团队现在还在“复制AI代码到项目里”，那不一定错，但它还在早期阶段。​
如果你的团队已经开始让Agent读文档、跑测试、开PR、留trace、按规则工作，那你已经在走向
HarnessEngineering。​

---

<!-- p.39 -->

17. 常见误区​
17.1误区一：提示词越长越好​
不对。提示词太长会稀释重点。​
更好的方式是：​
• 入口短；​
• 文档分层；​
• 规则明确；​
• 让Agent按需读取。​
17.2误区二：工具越多越强​
不对。工具多会增加选择成本。Agent可能不知道该用哪个，还可能把低风险任务搞成高风险操作。​
工具要少、稳、可组合。​
17.3误区三：AI通过一次测试就能放心​
不一定。测试只能证明你测过的地方没问题。关键业务还需要：​
• 边界测试；​
• 回归测试；​
• 人类review；​
• 灰度；​
• 监控；​
• 回滚。​
17.4误区四：Agent会自动理解团队品味​
不会。团队的架构偏好、命名习惯、抽象边界、错误处理方式，都要写下来，最好还能用lint、测试
或reviewchecklist固化。​
17.5误区五：HarnessEngineering只适合大公司​
不对。小团队更需要它，因为小团队没有那么多人肉review。哪怕只加一个 AGENTS.md
和测试命
令，也比纯VibeCoding稳定很多。​
18. 一个适合小团队的Harness模板​

---

<!-- p.40 -->

你可以直接从下面这个结构开始：​
代码块​
my-project/​
AGENTS.md​
docs/​
architecture.md​
testing.md​
coding-style.md​
decisions/​
0001-key-decision.md​
scripts/​
verify.sh​
.github/​
pull_request_template.md​
scripts/verify.sh
​
代码块​
#!/usr/bin/env bash​
set -euo pipefail​
​
echo "Running tests..."​
python -m pytest -q​
​
echo "Running compile check..."​
python -m compileall src​
​
echo "Verification passed."​
AGENTS.md
​
代码块​
# AGENTS.md​
​
## Project​
This is a small Python service.​
​
## Before You Start​
Read:​
- docs/architecture.md​
- docs/testing.md​
1
2
3
4
5
6
7
8
9
10
11
12
1
2
3
4
5
6
7
8
9
10
1
2
3
4
5
6
7
8
9

---

<!-- p.41 -->

​
## Commands​
Use this command before claiming completion:​
​
```bash​
bash scripts/verify.sh​
Rules​
• Keepchangesminimal.​
• Addtestsforbehaviorchanges.​
• Donotintroducenetworkcallsunlessrequested.​
• Donoteditsecrets,credentials,ordeploymentconfigs.​
• Donotclaimcompletionifverificationfails.​
ResponseFormat
Whendone,report:​
1. Summary​
2. Fileschanged​
3. Verificationresult​
4. Risks​
5. Follow-upsuggestions​
代码块​
​
### `docs/testing.md`​
​
```markdown​
# Testing​
​
## Unit Tests​
Run:​
​
```bash​
python -m pytest -q​
RequiredCoverage​
10
11
12
13
14
15
1
2
3
4
5
6
7
8
9
10
11

---

<!-- p.42 -->

Forbusinesslogicchanges,include:​
• normalcase​
• boundarycase​
• invalidinput
• regressioncaseiffixingabug​
CompletionRule​
Ataskisnotdoneuntiltestspass.​
代码块​
​
### PR
模板​
​
```markdown​
## Summary​
​
## Files Changed​
​
## Verification​
- [ ] bash scripts/verify.sh​
​
## Risk Level​
Low / Medium / High​
​
## Notes for Reviewer​
这个模板很简单，但已经能让Agent的表现稳定不少。​
19. HarnessEngineering的更高级方向：Evals、Trace和自动改进​
当团队开始大量使用Agent后，你会遇到一个新问题：​
我们怎么知道Agent越来越好了，还是只是感觉越来越好了？​
这时候要引入evals。​
一个evalcase可以长这样：​
代码块​
id: pricing-negative-price​
task: Fix cart pricing to reject negative prices.​
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
1
2

---

<!-- p.43 -->

repo_state: fixture/pricing_bug​
expected:​
tests:​
- tests/test_cart.py::test_negative_price_rejected​
forbidden_patterns:​
- "float("​
required_files_changed:​
- "src/cart.py"​
每次改Harness、改提示词、改工具、改模型，都跑一批evals，看成功率、耗时、token、失败类型
有没有变化。​
Trace的作用是告诉你失败为什么发生。​
例如：​
代码块​
{​
"case_id": "pricing-negative-price",​
"result": "failed",​
"failure_type": "missing_test",​
"notes": "Agent fixed implementation but did not add regression test."​
}​
你看到这种失败，就不应该只说“模型不行”。你可以改Harness：​
• 在 AGENTS.md
里加“修bug必须先写失败测试”；​
• 在verify脚本里检查测试文件是否变更；​
• 在PR模板里强制填写regressiontest；​
• 在Agent输出里要求列出新增测试。​
这就是Harness自我改进。​
20. 从工程角度重新理解“AI应用开发”​
过去很多AI应用开发教程会重点讲：​
• 怎么调API；​
• 怎么写prompt；​
• 怎么做RAG；​
• 怎么接向量数据库；​
3
4
5
6
7
8
9
10
1
2
3
4
5
6

---

<!-- p.44 -->

• 怎么做functioncalling；​
• 怎么做多Agent。​
这些当然重要。但如果你真的要做一个能上线、能维护、能团队协作的AI应用，还要问更工程化的问
题：​
20.1这个Agent的输入契约是什么？​
用户能说任何话，但系统不能接受任何含糊目标直接执行。你要把用户输入转成任务规格。​
20.2这个Agent能用哪些工具？​
工具不是越多越好。每个工具都要有：​
• 名称；​
• 描述；​
• 输入schema；​
• 输出schema；​
• 权限；​
• 风险级别；​
• 是否需要审批。​
20.3这个Agent的状态放在哪里？​
短期状态可以放对话里，长期状态最好放数据库、文件、任务系统或tracestore。​
20.4这个Agent怎么判断完成？​
不能只靠模型说完成。要有可验证标准。​
20.5这个Agent怎么失败？​
失败也要设计。比如：​
• 工具失败；​
• 权限不足；​
• 上下文不足；​
• 测试失败；​
• 外部API超时；​
• 用户目标冲突；​
• 安全策略拒绝。​
每种失败都应该有清晰输出，而不是“抱歉我失败了”。​

---

<!-- p.45 -->

20.6这个Agent怎么被审计？​
如果Agent能改代码、查数据、发消息、开PR、触发部署，那就必须能审计。​
审计不是大公司才需要，小团队也需要。否则出了问题没人知道它做过什么。​
21. 一个AI应用里的Harness架构图​
可以把系统想成这样：​
代码块​
User Request​
|​
v​
Task Spec Builder​
|​
v​
Context Selector ---- Project Docs / DB / Memory​
|​
v​
Agent Runtime​
|​
+---- Tool Router ---- Tools / MCP / APIs​
|​
+---- Permission Gate​
|​
+---- State Store​
|​
+---- Trace Logger​
|​
v​
Verification Layer ---- Tests / Evals / Rules / Human Review​
|​
v​
Final Output / PR / Report / Action​
每一层都有作用。​
• TaskSpecBuilder：把自然语言变成明确任务。​
• ContextSelector：挑相关上下文，不乱塞。​
• AgentRuntime：让模型规划和执行。
• ToolRouter：管理工具调用。​
• PermissionGate：控制风险。​
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24

---

<!-- p.46 -->

• StateStore：保存进度。​
• TraceLogger：记录过程。​
• VerificationLayer：判断是否完成。​
• FinalOutput：输出给用户或进入工程流程。​
如果你只调用一次LLMAPI，那不是Harness。那只是模型调用。​
如果你有工具、有状态、有验证、有权限、有trace，那才开始像一个Harness。​
22. HarnessEngineering对产品经理、小白和非技术人的意义​
这件事不只是程序员关心。​
非技术人使用AI做产品原型时，也会遇到同样问题。​
你用VibeCoding做一个产品Demo，很容易说：​
代码块​
帮我做一个 CRM
系统。​
AI可能很快给你页面。但你真正需要的不是“看起来像CRM”，而是：​
• 客户字段有哪些；​
• 谁可以看客户；​
• 销售阶段怎么流转；​
• 数据怎么导入导出；​
• 权限怎么做；​
• 删除客户是否可恢复；​
• 操作日志怎么留；​
• 移动端要不要适配；​
• 报表口径是什么；​
• 哪些功能第一版不做。​
这就是任务规格。​
哪怕你不会写代码，也可以做HarnessEngineering的一部分：把目标、规则、验收标准说清楚。​
例如你可以这样要求AI：​
代码块​
1

---

<!-- p.47 -->

你先不要写代码。请先帮我整理一份产品规格，包含：​
​
1.
用户角色​
2.
核心流程​
3.
数据字段​
4.
页面列表​
5.
第一版做什么​
6.
第一版不做什么​
7.
验收标准​
8.
风险和疑问​
​
等我确认后，再开始生成代码。​
这比直接“帮我写系统”靠谱得多。​
23. 实践清单：以后怎么和CodingAgent合作​
23.1开始任务前​
你应该准备：​
代码块​
## Goal​
我要做什么？​
​
## Why​
为什么做？​
​
## Scope​
这次包括什么？​
​
## Non-goals​
这次不包括什么？​
​
## Constraints​
有什么技术限制、业务限制、安全限制？​
​
## Done When​
怎样才算完成？​
​
## Verification​
用什么命令或方法验证？​
1
2
3
4
5
6
7
8
9
10
11
12
1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20

---

<!-- p.48 -->

23.2让Agent工作时​
不要只说：​
代码块​
继续。​
要说：​
代码块​
先读取 AGENTS.md
和 docs/testing.md
。​
然后制定计划。​
计划确认后再改代码。​
每完成一个 milestone
跑一次测试。​
如果测试失败，先解释失败原因，再修复。​
23.3Agent完成后​
不要只看它的总结。你要看：​
• diff；​
• tests；​
• lint；​
• build；​
• edgecases；​
• 是否改了不该改的文件；​
• 是否新增了不必要的依赖；​
• 是否把问题复杂化；​
• 是否修改了测试来迎合错误实现；​
• 是否留下了说明文档。​
23.4任务结束后​
把经验沉淀下来：​
• 这次哪里说得不清楚？​
• 哪个测试缺失？​
• 哪条规则应该写进AGENTS.md？​
1
1
2
3
4
5

---

<!-- p.49 -->

• 哪个工具权限太大？​
• 哪个文档过期？​
• 哪类任务适合Agent？​
• 哪类任务必须人类主导？​
24. 未来会发生什么？​
我认为未来AI应用开发会出现几个变化。​
24.1“写代码”会继续变便宜​
普通功能、样板代码、测试补齐、文档更新、迁移脚本，会越来越多地由Agent完成。​
但这不代表工程师不重要。因为真正难的是判断什么该做、怎么做才稳、风险在哪里、系统长期怎么
维护。​
24.2仓库会变得更“Agent-readable”​
未来的好仓库，不只是人能看懂，也要Agent能看懂。​
它会有：​
• 清晰文档；​
• 机器可执行验证；​
• 结构化任务；​
• 明确模块边界；​
• 标准化工具入口；​
• 可追踪决策记录。​
24.3CI/CD会变成Agent的工作场所​
Agent不会只在IDE里。它会进入：​
• issuetriage；​
• PRreview；​
• CIfailurerepair；​
• releasenote；​
• incidentresponse；​
• dependencyupgrade；​
• securityremediation；​

---

<!-- p.50 -->

• testgeneration；​
• migrationplanning。​
软件交付流水线会越来越像“人类+Agent”的协作系统。​
24.4Harness会成为AI原生应用的核心资产​
模型会更新，工具会变化，框架会流行又过时。但你团队沉淀下来的Harness会变成资产：​
• 任务模板；​
• 测试体系；​
• 文档体系；​
• 工具边界；​
• trace数据；​
• eval集合；​
• review规则；​
• 权限模型；​
• 失败案例库。​
这些东西越积越多，Agent的工作质量才会越来越稳。​
25. 总结：从“让AI写”到“让AI在系统里正确地写”​
VibeCoding让我们第一次感受到：用自然语言驱动软件开发是可能的。它降低了门槛，提高了速度，
也让很多想法能快速变成原型。​
但如果我们停在VibeCoding，就会遇到代码质量、上下文漂移、验证不足、安全边界、长期维护等问
题。​
HarnessEngineering解决的是下一阶段的问题：​
• 不只是prompt，而是任务规格；​
• 不只是上下文，而是项目知识系统；​
• 不只是工具调用，而是受控工具环境；​
• 不只是生成代码，而是验证代码；​
• 不只是一次运行，而是可追踪、可回滚、可复盘；​
• 不只是人盯着AI，而是人设计AI的工作系统。​
VibeCoding让AI动起来，HarnessEngineering让AI靠谱起来。​
对个人开发者来说，你可以从一个 AGENTS.md
、一个 scripts/verify.sh
、一套测试开始。​

---

<!-- p.51 -->

对团队来说，你可以从PR流程、CIgate、Agenttrace、任务模板开始。​
对AI应用开发者来说，你要从一开始就设计：这个Agent能做什么、不能做什么、怎么知道做对了、
失败后怎么处理、过程怎么审计。​
未来真正拉开差距的，不只是“谁会用AI写代码”，而是：​
谁能搭出一个让AI稳定交付的工程系统。​
