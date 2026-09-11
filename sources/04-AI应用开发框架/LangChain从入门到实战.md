# AI开发基础：Langchain框架从入门到实战开发-附代码 

> **素材来源**：`raw/pdf/AI开发基础：Langchain框架从入门到实战开发-附代码 .pdf`
> **页数**：23（其中无文本页 1 页，多为截图/图示）
> **正文规模**：约 15,256 字符，其中汉字 2,279 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

AI开发基础：Langchain框架从入门到实战开
发-附代码​
LangChain实战教程：从入门到实战​
一份接地气的LangChain学习指南，带你从零开始构建AI应用​
写在前面​
 这份教程不会堆砌概念，我会用最直白的话告诉你LangChain是什么、怎么用。代码都是能
跑的，直接抄就行。适合学AI应用开发，或者后端转AI开发的想快速上手的同学。​
适合谁看：​
• 听说过ChatGPT，想自己做点AI应用的开发者​
• 被官方文档绕晕的同学​
• 想快速上手实战项目的人​

---

<!-- p.2 -->

1.LangChain是什么？​
一句话解释​
LangChain=让大模型能"动手干活"的框架​
光靠ChatGPT只能聊天，但通过LangChain，你可以让AI：​
 • 查天气、搜网页​
• 读文件、写代码​
• 调用你公司的内部API​
• 自己决定该做什么​
架构图​

---

<!-- p.3 -->

核心能力​
2.环境搭建​
安装依赖​
代码块​
#
创建虚拟环境（推荐）​
python -m venv langchain_env​
source langchain_env/bin/activate # Mac/Linux​
1
2
3

---

<!-- p.4 -->

# langchain_env\Scripts\activate # Windows​
​
#
安装 LangChain
核心包​
pip install langchain langchain-core langchain-community​
​
#
根据你用的模型安装对应包​
pip install langchain-openai # OpenAI​
pip install langchain-anthropic # Claude​
pip install dashscope #
通义千问​
​
#
其他常用包​
pip install python-dotenv #
环境变量管理​
pip install langgraph # Agent
运行时（新版必装）​
配置APIKey​
创建 .env
文件：​
代码块​
# OpenAI​
OPENAI_API_KEY=sk-xxx​
​
#
或者通义千问​
DASHSCOPE_API_KEY=sk-xxx​
​
# Claude​
ANTHROPIC_API_KEY=sk-xxx​
验证安装​
代码块​
from dotenv import load_dotenv​
import os​
​
load_dotenv()​
​
#
通义千问示例​
from langchain_community.chat_models import ChatTongyi​
​
llm = ChatTongyi(​
model="qwen-turbo",​
dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")​
)​
​
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

---

<!-- p.5 -->

response = llm.invoke("
你好，请用一句话介绍自己")​
print(response.content)​
跑通了就说明环境OK！​
3.核心概念速览​
 LangChain的核心就四个东西，搞懂了就入门了：​
概念地图​
四大核心​
关系是这样的：​
14
15

---

<!-- p.6 -->

代码块
用户提问 → Prompt
格式化 → Agent
思考 →
调用 Tool → Model
生成回答 →
返回用户​
4.Prompt提示词模板​
 提示词模板就是把"问问题"这件事标准化。不用每次都手写完整的提示词。​
工作流程​
4.1最简单的模板​
代码块​
from langchain_core.prompts import PromptTemplate​
​
#
定义模板，用 {}
占位​
template = PromptTemplate.from_template(​
"
请用{language}
语言介绍一下{topic}
，不超过100
字。"​
)​
​
#
填充变量​
prompt = template.format(language="
中文", topic="
人工智能")​
print(prompt)​
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

---

<!-- p.7 -->

#
输出:
请用中文语言介绍一下人工智能，不超过100
字。​
4.2聊天模板（常用）​
做聊天应用一般用这个，可以设置system和user角色：​
代码块​
from langchain_core.prompts import ChatPromptTemplate​
​
#
定义多轮对话模板​
chat_template = ChatPromptTemplate.from_messages([​
("system", "
你是一位{role}
，擅长用简洁易懂的方式解释复杂概念。"),​
("human", "
请解释一下：{concept}"),​
])​
​
#
生成消息列表​
messages = chat_template.format_messages(​
role="
物理学教授",​
concept="
量子纠缠"​
)​
​
#
调用模型​
response = llm.invoke(messages)​
print(response.content)​
4.3Few-shot示例模板
通过给几个例子，教AI按你想要的格式输出：​
代码块​
#
定义示例​
examples = [​
{"input": "
开心", "output": "
我今天非常开心！"},​
{"input": "
难过", "output": "
我感到有些难过..."},​
]​
​
#
创建包含示例的模板​
few_shot_template = ChatPromptTemplate.from_messages([​
("system", "
你是一个情绪表达助手。"),​
("human", "
示例：\n
情绪:
开心\n
表达:
我今天非常开心！\n\n
情绪:
难过\n
表达:
我感到
有些难过..."),​
("human", "
现在请表达这个情绪: {emotion}")​
])​
​
11
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

<!-- p.8 -->

messages = few_shot_template.format_messages(emotion="
兴奋")​
response = llm.invoke(messages)​
4.4动态日期模板​
有些变量想自动填充（比如当前日期）：​
代码块​
from datetime import datetime​
from langchain_core.prompts import PromptTemplate​
​
template = PromptTemplate(​
template="
今天是{date}
，请告诉我关于{topic}
的最新消息。",​
input_variables=["topic"],​
partial_variables={​
"date": datetime.now().strftime("%Y
年%m
月%d
日") #
自动填充​
}​
)​
​
#
只需要传 topic​
prompt = template.format(topic="AI
发展")​
5.Tools工具定义​
工具就是让AI能调用的函数。定义好工具后，AI会自己决定什么时候用、怎么用。​
5.1用装饰器定义（最简单）​
代码块​
from langchain_core.tools import tool​
​
@tool​
def get_weather(city: str) -> str:​
"""​
获取城市的天气信息​
​
Args:​
city:
城市名称，如"
北京"
、"
上海"​
"""​
#
模拟天气数据（实际项目中调用天气 API
）​
weather_data = {​
"
北京": "
晴天，25°C",​
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

---

<!-- p.9 -->

"
上海": "
多云，22°C",​
"
深圳": "
小雨，28°C",​
}​
return weather_data.get(city, f"{city}
的天气暂时无法获取")​
​
​
#
测试工具​
result = get_weather.invoke({"city": "
北京"})​
print(result) #
输出:
晴天，25°C​
​
#
查看工具信息​
print(f"
工具名称: {get_weather.name}")​
print(f"
工具描述: {get_weather.description}")​
print(f"
参数结构: {get_weather.args}")​
重点：docstring写清楚！AI就是靠这个描述来决定什么时候调用这个工具。​
5.2更复杂的工具​
代码块​
from typing import Optional​
​
@tool​
def search_database(query: str, category: Optional[str] = None) -> str:​
"""​
在数据库中搜索信息​
​
Args:​
query:
搜索关键词​
category:
可选的分类过滤器，如"
科技"
、"
健康"
、"
教育"​
"""​
database = {​
"
科技": ["
人工智能正在改变世界", "5G
技术的应用"],​
"
健康": ["
健康饮食的重要性", "
运动与长寿的关系"],​
"
教育": ["
在线学习的趋势", "
终身学习的价值"]​
}​
​
results = []​
​
if category and category in database:​
for item in database[category]:​
if query.lower() in item.lower():​
results.append(f"[{category}] {item}")​
else:​
for cat, items in database.items():​
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

---

<!-- p.10 -->

for item in items:​
if query.lower() in item.lower():​
results.append(f"[{cat}] {item}")​
​
if results:​
return "
找到以下结果:\n" + "\n".join(results)​
else:​
return f"
没有找到关于 '{query}'
的结果"​
5.3用类定义（需要更多控制时）​
代码块​
from langchain_core.tools import BaseTool​
from pydantic import BaseModel, Field​
from typing import Type​
​
#
定义输入参数结构​
class CalculatorInput(BaseModel):​
expression: str = Field(description="
数学表达式，如 '2+2'
或 '10*5'")​
​
class Calculator(BaseTool):​
name: str = "calculator"​
description: str = "
执行数学计算"​
args_schema: Type[BaseModel] = CalculatorInput​
​
def _run(self, expression: str) -> str:​
"""
同步执行"""​
try:​
result = eval(expression)​
return f"
计算结果: {expression} = {result}"​
except Exception as e:​
return f"
计算错误: {str(e)}"​
​
async def _arun(self, expression: str) -> str:​
"""
异步执行（可选实现）"""​
return self._run(expression)​
​
#
使用​
calc = Calculator()​
result = calc.invoke({"expression": "123 * 456"})​
print(result) #
计算结果: 123 * 456 = 56088​
5.4把工具绑定到模型​
26
27
28
29
30
31
32
33
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
28
29

---

<!-- p.11 -->

定义好工具后，需要"告诉"模型这些工具的存在：​
代码块​
#
创建工具列表​
tools = [get_weather, search_database, Calculator()]​
​
#
绑定到模型​
llm_with_tools = llm.bind_tools(tools)​
​
#
现在模型知道有这些工具可用了​
response = llm_with_tools.invoke("
北京今天天气如何？")​
​
#
检查模型是否决定调用工具​
if response.tool_calls:​
for tool_call in response.tool_calls:​
print(f"
模型想调用: {tool_call['name']}")​
print(f"
传入参数: {tool_call['args']}")​
6.Agent智能代理​
 Agent是LangChain最酷的部分。它不是按固定流程执行，而是自己思考、自己决定该干
啥。​
Agent思考循环​
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

---

<!-- p.12 -->

6.1LangChain1.0+新版Agent​
新版用 create_agent
，底层基于LangGraph，更稳定：​
代码块​
from langchain.agents import create_agent​
from langchain_core.tools import tool​
from langchain_community.chat_models import ChatTongyi​
import os​
​
# 1.
初始化模型​
llm = ChatTongyi(​
model="qwen-plus",​
temperature=0.7,​
dashscope_api_key=os.environ.get("DASHSCOPE_API_KEY")​
)​
​
# 2.
定义工具​
@tool​
def get_weather(city: str) -> str:​
"""
获取城市天气信息"""​
weather_db = {​
"
北京": "
晴天，15-25
度",​
"
上海": "
多云，18-28
度",​
"
深圳": "
小雨，20-30
度",​
}​
return weather_db.get(city, f"{city}
的天气信息暂不可用")​
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

---

<!-- p.13 -->

@tool​
def calculator(expression: str) -> str:​
"""
执行数学计算"""​
try:​
result = eval(expression)​
return f"
计算结果: {expression} = {result}"​
except:​
return "
计算错误"​
​
@tool ​
def search_knowledge(query: str) -> str:​
"""
搜索知识库"""​
knowledge = {​
"LangChain": "LangChain
是一个用于开发LLM
应用的框架，支持工具、代理、内存管理等
功能。",​
"
机器学习": "
机器学习是AI
的子集，让系统能从数据中自动学习和改进。",​
}​
for key, value in knowledge.items():​
if key in query:​
return value​
return f"
未找到关于'{query}'
的信息"​
​
# 3.
创建 Agent​
agent = create_agent(​
model=llm,​
tools=[get_weather, calculator, search_knowledge],​
system_prompt="
你是一个专业的中文助手。仔细分析用户问题，选择合适的工具来回答。"​
)​
​
# 4.
使用 Agent​
result = agent.invoke({​
"messages": [{"role": "user", "content": "
北京今天天气怎么样？"}]​
})​
​
#
获取回答​
final_message = result["messages"][-1]​
print(f"
回答: {final_message.content}")​
6.2Agent处理多个问题​
代码块​
test_queries = [​
"
北京今天天气怎么样？",​
"
给我讲讲什么是机器学习",​
"
计算 123 * 456",​
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
1
2
3
4

---

<!-- p.14 -->

]​
​
for query in test_queries:​
print(f"\n
用户: {query}")​
​
result = agent.invoke({​
"messages": [{"role": "user", "content": query}]​
})​
​
final_message = result["messages"][-1]​
print(f"
助手: {final_message.content}")​
6.3带记忆的Agent​
让Agent记住对话历史：​
代码块​
from langgraph.checkpoint.memory import MemorySaver​
​
#
创建记忆存储​
checkpointer = MemorySaver()​
​
#
创建带记忆的 Agent​
agent = create_agent(​
model=llm,​
tools=[get_weather, calculator, search_knowledge],​
system_prompt="
你是一个专业助手，能记住之前的对话。",​
checkpointer=checkpointer #
启用记忆​
)​
​
#
会话配置（同一个 thread_id
共享记忆）​
config = {"configurable": {"thread_id": "session_001"}}​
​
#
第一轮对话​
result1 = agent.invoke(​
{"messages": [{"role": "user", "content": "
我叫小明"}]},​
config​
)​
print(result1["messages"][-1].content)​
​
#
第二轮对话（Agent
会记得用户叫小明）​
result2 = agent.invoke(​
{"messages": [{"role": "user", "content": "
我叫什么名字？"}]},​
config​
)​
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
28

---

<!-- p.15 -->

print(result2["messages"][-1].content) #
会回答"
小明"​
6.4流式输出​
让回答一个字一个字输出，体验更好：​
代码块​
#
流式调用​
for chunk in agent.stream(​
{"messages": [{"role": "user", "content": "
北京天气如何？"}]},​
config,​
stream_mode="values"​
):​
messages = chunk.get("messages")​
if messages:​
last_message = messages[-1]​
if hasattr(last_message, "content") and last_message.content:​
print(last_message.content, end="", flush=True)​
print() #
换行​
7.完整项目：全能智能助手​
现在把前面学的串起来，做一个能干实事的智能助手。​
7.1项目结构​
代码块​
smart_assistant/​
├── .env # API Key​
├── main.py #
主程序​
├── tools/ #
工具定义​
│ ├── __init__.py​
│ ├── weather.py​
│ ├── calculator.py​
│ ├── translator.py​
│ └── knowledge.py​
└── requirements.txt​
7.2工具定义​
tools/weather.py​
29
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

---

<!-- p.16 -->

代码块​
from langchain_core.tools import tool​
from datetime import datetime​
​
@tool​
def get_weather(city: str) -> str:​
"""​
获取指定城市的实时天气信息​
​
Args:​
city:
城市名称，支持北京、上海、广州、深圳、杭州等​
"""​
weather_database = {​
"
北京": {"condition": "
晴天", "temp": "15-25°C", "aqi": "
优"},​
"
上海": {"condition": "
多云", "temp": "18-28°C", "aqi": "
良"},​
"
深圳": {"condition": "
小雨", "temp": "22-30°C", "aqi": "
优"},​
"
杭州": {"condition": "
阴天", "temp": "17-26°C", "aqi": "
良"},​
"
广州": {"condition": "
晴天", "temp": "20-32°C", "aqi": "
良"},​
}​
​
if city not in weather_database:​
return f"
暂无{city}
的天气数据，支持城市：北京、上海、深圳、杭州、广州"​
​
data = weather_database[city]​
return f"""​
{city}
天气预报​
━━━━━━━━━━━━━━━━​
天气：{data['condition']}​
温度：{data['temp']}​
空气质量：{data['aqi']}​
更新时间：{datetime.now().strftime("%H:%M")}​
""".strip()​
tools/calculator.py​
代码块​
from langchain_core.tools import tool​
​
@tool​
def calculator(expression: str) -> str:​
"""​
执行数学计算​
​
Args:​
expression:
数学表达式，如 "2+2"
、"(10*5)+20"
、"2**8"​
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
28
29
30
31
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

<!-- p.17 -->

"""​
try:​
#
安全检查​
allowed_chars = set('0123456789+-*/(). ')​
if not all(c in allowed_chars for c in expression.replace('**', '')):​
return "
表达式包含非法字符"​
​
result = eval(expression, {"__builtins__": {}}, {})​
​
if isinstance(result, float) and result.is_integer():​
result = int(result)​
​
return f"
计算结果：{expression} = {result}"​
except ZeroDivisionError:​
return "
错误：除数不能为零"​
except Exception as e:​
return f"
计算错误：{str(e)}"​
tools/translator.py​
代码块​
from langchain_core.tools import tool​
​
@tool​
def translate(text: str, target_language: str = "
英文") -> str:​
"""​
将中文文本翻译成其他语言（模拟）​
​
Args:​
text:
要翻译的中文文本​
target_language:
目标语言，支持"
英文"
、"
日文"
、"
韩文"​
"""​
translations = {​
"
你好": {"
英文": "Hello", "
日文": "
こんにちは", "
韩文": "
안녕하세요"},​
"
谢谢": {"
英文": "Thank you", "
日文": "
ありがとう", "
韩文": "
감사합니다"},​
"
再见": {"
英文": "Goodbye", "
日文": "
さようなら", "
韩文": "
안녕히 가세요"},​
}​
​
if text in translations and target_language in translations[text]:​
result = translations[text][target_language]​
return f"
翻译结果：'{text}' → [{target_language}] {result}"​
​
return f"
暂不支持'{text}'
的{target_language}
翻译"​
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

---

<!-- p.18 -->

7.3主程序​
main.py​
代码块​
import os​
from dotenv import load_dotenv​
from langchain.agents import create_agent​
from langchain_community.chat_models import ChatTongyi​
from langgraph.checkpoint.memory import MemorySaver​
​
#
导入工具​
from tools.weather import get_weather​
from tools.calculator import calculator​
from tools.translator import translate​
​
#
加载环境变量​
load_dotenv()​
​
#
系统提示词​
SYSTEM_PROMPT = """​
你是小智，一个全能智能助手。​
​
你可以帮用户：​
•
查询天气：查询中国主要城市的天气​
•
数学计算：进行各种数学运算​
•
文本翻译：将中文翻译成其他语言​
​
工作原则：​
1.
先理解用户意图，选择合适的工具​
2.
如果不确定，可以询问用户​
3.
回答简洁明了，有帮助​
"""​
​
def create_assistant():​
"""
创建智能助手"""​
#
初始化模型​
llm = ChatTongyi(​
model="qwen-plus",​
temperature=0.7,​
dashscope_api_key=os.environ.get("DASHSCOPE_API_KEY")​
)​
​
#
创建记忆​
checkpointer = MemorySaver()​
​
#
创建 Agent​
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

---

<!-- p.19 -->

agent = create_agent(​
model=llm,​
tools=[get_weather, calculator, translate],​
system_prompt=SYSTEM_PROMPT,​
checkpointer=checkpointer​
)​
​
return agent​
​
def main():​
"""
主函数"""​
print("=" * 50)​
print("
小智 -
全能智能助手 v1.0")​
print("=" * 50)​
print("
输入 'quit'
退出\n")​
​
agent = create_assistant()​
config = {"configurable": {"thread_id": "main"}}​
​
while True:​
user_input = input("
你: ").strip()​
​
if user_input.lower() in ['quit', '
退出', 'exit']:​
print("
再见！")​
break​
​
if not user_input:​
continue​
​
try:​
result = agent.invoke(​
{"messages": [{"role": "user", "content": user_input}]},​
config​
)​
​
response = result["messages"][-1].content​
print(f"
小智: {response}\n")​
​
except Exception as e:​
print(f"
出错了: {str(e)}\n")​
​
if __name__ == "__main__":​
main()​
7.4运行效果​
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

---

<!-- p.20 -->

代码块​
==================================================​
小智 -
全能智能助手 v1.0​
==================================================​
输入 'quit'
退出​
​
你:
北京天气怎么样​
小智: ​
北京 天气预报​
━━━━━━━━━━━━━━━━​
天气：晴天​
温度：15-25°C​
空气质量：优​
更新时间：14:30​
​
你:
帮我算一下 125 * 88​
小智:
计算结果：125 * 88 = 11000​
​
你:
把"
你好"
翻译成日文​
小智:
翻译结果：'
你好' → [
日文]
こんにちは​
​
你: quit​
再见！​
8.进阶技巧与最佳实践​
8.1工具描述要写好​
AI完全靠工具的description来决定什么时候调用。写得不清楚，它就不会用。​
坏例子：​
代码块​
@tool​
def func(x: str) -> str:​
"""
处理数据""" #
太模糊了！​
pass​
好例子：​
代码块​
@tool​
def get_stock_price(symbol: str) -> str:​
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
1
2
3
4
1
2

---

<!-- p.21 -->

"""​
获取股票实时价格​
​
当用户询问某只股票的价格、涨跌情况时使用此工具。​
​
Args:​
symbol:
股票代码，如 "AAPL"
（苹果）、"GOOGL"
（谷歌）​
​
Returns:​
包含当前价格、涨跌幅的字符串​
"""​
pass​
8.2错误处理要完善​
工具可能会失败（网络错误、参数错误等），一定要有兜底：​
代码块​
@tool​
def fetch_data(url: str) -> str:​
"""
从URL
获取数据"""​
try:​
response = requests.get(url, timeout=10)​
response.raise_for_status()​
return response.text​
except requests.Timeout:​
return "
请求超时，请稍后重试"​
except requests.RequestException as e:​
return f"
请求失败：{str(e)}"​
except Exception as e:​
return f"
未知错误：{str(e)}"​
8.3调整温度参数​
• temperature=0
：输出最确定，适合事实查询​
• temperature=0.7
：有一定创意，适合对话​
• temperature=1.0
：输出多样，适合创作​
8.4使用LangSmith调试​
遇到奇怪问题时，用LangSmith看看Agent到底在想什么：​
代码块​
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

<!-- p.22 -->

import os​
​
#
在代码最前面添加​
os.environ["LANGCHAIN_TRACING_V2"] = "true"​
os.environ["LANGCHAIN_API_KEY"] = "
你的LangSmith API Key"​
然后去smith.langchain.com就能看到每一步的详细trace。​
8.5控制迭代次数​
防止Agent陷入死循环：​
代码块​
agent = create_agent(​
model=llm,​
tools=tools,​
#
其他选项​
)​
​
#
调用时限制最大步数​
result = agent.invoke(​
{"messages": [...]},​
config,​
recursion_limit=10 #
最多10
步​
)​
1
2
3
4
5
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
