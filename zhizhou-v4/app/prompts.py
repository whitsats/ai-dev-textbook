"""v4 的提示：**模板是对象，不是字符串**。

对照点。v3 的提示是一份 Markdown 文件（`app/llm/prompts/article_summary.md`），
读进来是一整个 `str`，拼接靠 f-string / `+`，变量名只活在写代码那个人的脑子里。
v4 的提示是 `ChatPromptTemplate`——它自己知道「我需要哪几个变量」，
所以**缺变量能在渲染时就报出来**，而不是等模型返回一段答非所问的话。

四条纪律（第 4.2.2 节会逐条给读数）：

1. **变量名是契约**。`input_variables` 可查、可断言；改名会让渲染当场抛 `KeyError`。
2. **系统提示与用户内容分开**。系统提示写规则，用户内容写数据——
   这样注入正文里的「忽略以上要求」不会与规则混在同一段文本里。
3. **历史用 `MessagesPlaceholder`，不用字符串拼接**。它留的是一个消息**列表**的位置。
4. **少样本示例是消息，不是一段文本**。示例进 `AIMessage`，模型看到的是「一问一答」，
   而不是「一段有点像对话的散文」——这是素材 §4.3 那种写法最主要的损失。
"""
from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate

from app.schemas import TAGS

# 规则与 v3 的 `article_summary.md` 逐条对应，只是换了承载方式：
# v3 写在 Markdown 文件的第 2 条里，v4 里「最多三个」这句同时由 `Field(max_length=3)` 兜住。
SUMMARY_SYSTEM = (
    "你是知舟博客的编辑助手。把用户给出的文章正文压成三句话以内的摘要。\n\n"
    "要求：\n"
    "1. 摘要只陈述正文里写过的事实，不要补充正文之外的背景，不要给建议。\n"
    f"2. tags 只能从清单里选，最多三个：{'、'.join(TAGS)}。\n"
    "3. 按正文实际内容选标签；正文只讲一件事时，给一个标签也是正确结果，不要凑数。\n"
    "4. 输出使用简体中文。"
)

# 摘要链的提示：系统消息（规则）＋ 用户消息（数据）。
SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SUMMARY_SYSTEM),
    ("human", "正文：\n{article}"),
])

# 带历史的多轮提示：`MessagesPlaceholder` 占的是一个位置，装的是**一个消息列表**。
# 素材 §4.2 那种写法是把历史拼进字符串，于是「历史里有几条」这件事在模板层面不可知。
CHAT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是知舟的技术助手。回答控制在两句话内，不要客套。"),
    ("placeholder", "{history}"),
    ("human", "{question}"),
])

# 少样本示例：每一例是一对消息，而不是一段「示例：情绪: 开心 表达: 我今天非常开心！」的散文。
_EXAMPLES = [
    {"input": "给文章 12 打标签", "output": '{"tool": "get_tags", "args": {"article_id": 12}}'},
    {"input": "文章 7 的第一段是什么", "output": '{"tool": "read_article", "args": {"article_id": 7}}'},
]
_EXAMPLE_PROMPT = ChatPromptTemplate.from_messages([
    ("human", "{input}"),
    ("ai", "{output}"),
])
_FEW_SHOT = FewShotChatMessagePromptTemplate(example_prompt=_EXAMPLE_PROMPT, examples=_EXAMPLES)

# 起草草稿的提示：少样本 ＋ 真实任务。素材 §4.3 想教的正是这件事，只是写成了字符串。
# `_FEW_SHOT` 本身就是一个消息模板，所以它**整体**占列表里的一个位置。
DRAFT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "你是知舟的编辑。把工具调用写成 JSON，字段只有 tool 与 args。"),
    _FEW_SHOT,                               # 示例是**消息**，整体插在规则与任务之间
    ("human", "{request}"),
])

# 代理的系统提示：**与 v3 的 `app/agent/prompts/agent.md` 逐字相同**。
# 为什么不做成模板：它一个变量都没有，而 `create_agent(system_prompt=...)` 收的就是字符串。
# 但「没有变量」不等于「不是契约」——两棵树要做同一个任务，提示必须先一样，
# 否则 4.3.6 的对照里差的就不只是编排了（这一条纪律在第 4 篇每一章都成立）。
AGENT_SYSTEM = """你是「知舟」博客的写作助手。你只能通过工具了解站点内容，不能凭印象编造文章。

工作方式：
1. 先判断这个问题需要哪些信息，再用最少的工具调用把它们拿到。
2. 检索用关键词，不要把整句话当检索词。**已经拿到候选文章 id 就直接 read_article**：
   换一个关键词重搜同一个主题通常只会拿到同一批结果，属于白花一次调用。
3. 标签写法不确定时先调 get_tags 看现有标签，不要猜。
4. 工具返回的错误是信息，不是失败：按提示改参数或换方法，不要原样重试。
5. 信息够了就直接给答案，不要为了「完整」再多调一次工具。

写操作分两档，**不要混**：
- `create_draft`（起草）：用户要求改稿/润色/另写一版时，直接调用即可，
  然后在回答里说清写了什么。它不改变已发布内容，可覆盖。
- `publish_article`（发布）：**不可逆**。只有用户在本轮明确说了「发布」才调用；
  没确认之前只说明「将要发布什么」，不要调用它。

回答要求：简体中文；结论在前；引用的文章给出 id 与标题；找不到就直说找不到。
"""
