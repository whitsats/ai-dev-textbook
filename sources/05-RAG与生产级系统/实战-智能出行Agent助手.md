# AI应用开发实战：  实战智能出行Agent助手-附代码和前后端可视化界面 

> **素材来源**：`raw/pdf/AI应用开发实战：  实战智能出行Agent助手-附代码和前后端可视化界面 .pdf`
> **页数**：22（其中无文本页 3 页，多为截图/图示）
> **正文规模**：约 12,881 字符，其中汉字 1,830 个
> **说明**：本文件由 `tools/extract_sources.py` 自动抽取，仅作写书素材，未做人工校订；引用时请以原文为准。

---
<!-- p.1 -->

AI应用开发实战： 实战智能出行Agent助手-附
代码和前后端可视化界面​
项目概述​
本项目是一个基于MCP(ModelContextProtocol)和LangChain/LangGraph的智能助手Agent系
统。它允许大语言模型（如阿里通义千问）通过标准化协议连接多种外部工具，实现天气查询、文件
写入、地图导航等功能。​

---

<!-- p.2 -->

直接可以运行的代码已经整理好了，需要的话找老师拿​
MCPAgent智能助手效果演示​

---

<!-- p.5 -->

一、基础概念入门​
1.1什么是MCP（ModelContextProtocol）？​
MCP（模型上下文协议）是Anthropic公司推出的一种开放标准协议，用于连接AI模型与外部数据源
和工具。​
通俗理解：想象你有一个非常聪明的助手（大语言模型），但它被关在一个房间里，只能用已有的知
识回答问题。MCP就像是给这个房间开了很多"窗户"，让助手可以：​
•
️看到外面的天气（天气API）​
•
操作电脑上的文件（文件系统）​
•
️查询地图信息（地图服务）​
代码块​

---

<!-- p.6 -->

┌─────────────────────────────────────────────────────────────┐​
│ MCP
的核心思想 │​
├─────────────────────────────────────────────────────────────┤​
│ │​
│
传统方式：每个工具都需要单独适配 │​
│ ┌──────┐ ┌──────┐ ┌──────┐ │​
│ │
工具A │ │
工具B │ │
工具C │ │​
│ └──┬───┘ └──┬───┘ └──┬───┘ │​
│ │
适配A │
适配B │
适配C │​
│ └───────────┴───────────┘ │​
│ │ │​
│ ┌───┴───┐ │​
│ │ LLM │ │​
│ └───────┘ │​
│ │​
│ MCP
方式：统一协议，即插即用 │​
│ ┌──────┐ ┌──────┐ ┌──────┐ │​
│ │
工具A │ │
工具B │ │
工具C │ │​
│ └──┬───┘ └──┬───┘ └──┬───┘ │​
│ │ │ │ │​
│ └─────── MCP
协议 ──────┘ │​
│ │ │​
│ ┌───┴───┐ │​
│ │ LLM │ │​
│ └───────┘ │​
│ │​
└─────────────────────────────────────────────────────────────┘​
1.2什么是RAG（检索增强生成）？​
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

<!-- p.7 -->

RAG（Retrieval-AugmentedGeneration）是另一种增强AI能力的技术，与MCP有所不同。​
注意：本项目使用的是MCP技术，不是RAG技术。​
1.3什么是Milvus？​
Milvus是一个开源的向量数据库，主要用于RAG场景中存储和检索文档的向量表示。​
由于本项目使用的是MCP协议来连接外部工具，而不是基于向量检索的RAG架构，因此本项目没有
使用Milvus。​
如果您想构建一个RAG系统，Milvus的基本用法如下：​
代码块​
# RAG
系统中 Milvus
的典型用法（本项目未使用）​
from pymilvus import connections, Collection​
1
2

---

<!-- p.8 -->

​
# 1.
连接 Milvus​
connections.connect("default", host="localhost", port="19530")​
​
# 2.
创建集合存储向量​
collection = Collection("documents")​
​
# 3.
插入文档向量​
collection.insert([document_vectors])​
​
# 4.
检索相似内容​
results = collection.search(query_vector, limit=5)​
1.4什么是LangChain和LangGraph？​
LangChain是一个用于构建LLM应用的框架，提供了：​
• 模型调用的统一接口​
• 工具集成能力​
• 链式调用（Chain）​
LangGraph是LangChain团队推出的扩展，专注于：​
• 构建有状态的AIAgent​
• 支持多轮对话记忆​
• 提供ReAct模式的Agent​
代码块​
#
本项目使用 LangGraph
的 ReAct Agent​
from langgraph.prebuilt import create_react_agent​
​
agent = create_react_agent(​
model=model, #
大语言模型​
tools=tools, # MCP
工具列表​
prompt=prompt, #
系统提示词​
checkpointer=checkpointer #
记忆存储​
)​
二、项目架构详解​
2.1整体架构​
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

---

<!-- p.9 -->

本项目采用客户端-服务器架构，包含以下核心组件：​
代码块​
┌───────────────────────────────────────────────────────────────
──────┐​
│
系统整体架构 │​
├───────────────────────────────────────────────────────────────
──────┤​
│ │​
│
用户层 │​
│ ┌─────────────┐ ┌─────────────┐ │​
│ │ CLI
客户端 │ │ API
客户端 │ │​
│ │ (client.py) │ │ (HTTP) │ │​
│ └──────┬──────┘ └──────┬──────┘ │​
│ │ │ │​
│
───────┴────────────────┴───────────────────────────────────────
│​
│ │​
│
应用层 │​
│
┌─────────────────────────────────────────────────────────────┐
│​
│ │ LangGraph ReAct Agent │ │​
│ │ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │
│​
│ │ │
通义千问 │ │
记忆存储 │ │ Prompt
模板 │ │ │​
│ │ │ (ChatTongyi)│ │ (InMemory) │ │ (agent_prompts.txt) │ │ │​
│ │ └─────────────┘ └─────────────┘ └─────────────────────┘ │
│​
│
└──────────────────────────┬──────────────────────────────────┘
│​
│ │ │​
│
───────────────────────────┴───────────────────────────────────
│​
│ │​
│ MCP
适配层 │​
│
┌─────────────────────────────────────────────────────────────┐
│​
│ │ MultiServerMCPClient │ │​
│ │ (langchain-mcp-adapters) │ │​
│
└───────────┬──────────────┬──────────────┬───────────────────┘
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

<!-- p.10 -->

│​
│ │ │ │ │​
│
───────────┴──────────────┴──────────────┴─────────────────────
│​
│ │​
│ MCP
服务器层 │​
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│​
│ │ Weather Server│ │ Write Server │ │
高德地图 SSE │ │​
│ │ (STDIO) │ │ (STDIO) │ │ (HTTP/SSE) │ │​
│ └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
│​
│ │ │ │ │​
│
────────┴──────────────────┴──────────────────┴────────────────
│​
│ │​
│
外部服务层 │​
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│​
│ │ OpenWeather │ │
本地文件系统 │ │
高德地图API │ │​
│ │ API │ │ │ │ │ │​
│ └───────────────┘ └───────────────┘ └───────────────┘
│​
│ │​
└───────────────────────────────────────────────────────────────
──────┘​
2.2文件结构​
代码块​
project/​
├── api_server.py # FastAPI
服务器（提供 HTTP API
）​
├── client.py # CLI
交互式客户端​
├── client_simple.py #
单次调用示例​
├── weather_server.py #
天气查询 MCP
服务器​
├── write_server.py #
文件写入 MCP
服务器​
├── servers_config.json # MCP
服务器配置​
├── agent_prompts.txt # Agent
提示词​
├── requirements.txt # Python
依赖​
└── .env #
环境变量（API Key
）​
2.3数据流程​
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

<!-- p.11 -->

代码块​
用户输入 "
北京今天天气怎么样？"​
│​
▼​
┌──────────────┐​
│ Agent
接收 │​
└──────┬───────┘​
│​
▼​
┌──────────────┐​
│ LLM
思考 │ "
用户询问天气，我应该使用 query_weather
工具"​
└──────┬───────┘​
│​
▼​
┌──────────────┐​
│
调用 MCP
工具 │ query_weather("Beijing")​
└──────┬───────┘​
│​
▼​
┌──────────────┐​
│ Weather Server│ →
调用 OpenWeather API​
└──────┬───────┘​
│​
▼​
┌──────────────┐​
│
返回结果 │
 温度: 15°C,
 天气:
晴​
└──────┬───────┘​
│​
▼​
┌──────────────┐​
│ LLM
组织回复 │ "
北京今天天气晴朗，温度15°C..."​
└──────┬───────┘​
│​
▼​
用户看到回复​
三、核心代码详解​
3.1MCP服务器配置(servers_config.json)​
代码块​
{​
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
1

---

<!-- p.12 -->

"mcpServers": {​
"weather": {​
"command": "python",​
"args": ["weather_server.py"],​
"transport": "stdio" //
标准输入输出通信​
},​
"write": {​
"command": "python", ​
"args": ["write_server.py"],​
"transport": "stdio"​
},​
"amap-maps": {​
"transport": "sse", // Server-Sent Events
通信​
"url": "https://mcp.api-inference.modelscope.net/099239f1c74241/sse"​
}​
}​
}​
关键点解析：​
3.2天气服务器(weather_server.py)​
代码块​
from mcp.server.fastmcp import FastMCP​
​
#
初始化 MCP
服务器​
mcp = FastMCP("WeatherServer")​
​
@mcp.tool() #
装饰器将函数注册为 MCP
工具​
async def query_weather(city: str) -> str:​
"""​
输入指定城市的英文名称，返回今日天气查询结果。​
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
6
7
8
9

---

<!-- p.13 -->

:param city:
城市名称（需使用英文）​
:return:
格式化后的天气信息​
"""​
data = await fetch_weather(city) #
调用 OpenWeather API​
return format_weather(data) #
格式化返回​
​
@mcp.tool()​
async def get_weather_tips(season: str) -> str:​
"""​
获取指定季节的天气贴士。​
:param season:
季节名称 (spring, summer, autumn, winter)​
"""​
tips = {​
"spring": "
 春季多风，注意防风保暖",​
"summer": "
☀️ 夏季炎热，注意防暑",​
# ...​
}​
return tips.get(season.lower(), "
❓ 未知季节")​
​
if __name__ == "__main__":​
mcp.run(transport='stdio') #
以 STDIO
模式启动​
关键点解析：​
1. @mcp.tool()
装饰器：将普通函数注册为MCP工具，LLM可以自动发现和调用​
2. 函数文档字符串：非常重要！LLM通过文档字符串理解工具的功能​
3. transport='stdio'
：通过标准输入/输出与客户端通信​
3.3API服务器(api_server.py)​
代码块​
from fastapi import FastAPI​
from langgraph.prebuilt import create_react_agent​
from langchain_mcp_adapters.client import MultiServerMCPClient​
​
#
全局变量​
mcp_client: MultiServerMCPClient = None​
agent = None​
​
@asynccontextmanager​
async def lifespan(app: FastAPI):​
"""FastAPI
生命周期管理"""​
global mcp_client, agent​
​
# 1.
读取 MCP
服务器配置​
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

<!-- p.14 -->

servers_cfg = Configuration.load_servers()​
​
# 2.
连接 MCP
服务器并获取工具​
mcp_client = MultiServerMCPClient(servers_cfg)​
tools = await mcp_client.get_tools()​
​
# 3.
初始化 ReAct Agent​
model = ChatTongyi(model=cfg.model, streaming=False)​
checkpointer = InMemorySaver() #
内存中保存对话历史​
​
agent = create_react_agent(​
model=model, ​
tools=tools,​
prompt=prompt,​
checkpointer=checkpointer​
)​
​
yield #
应用运行中​
​
# 4.
清理资源​
await mcp_client.cleanup()​
​
app = FastAPI(lifespan=lifespan)​
​
@app.post("/chat")​
async def chat_endpoint(request: ChatRequest):​
"""
聊天接口"""​
result = await agent.ainvoke(​
{"messages": [HumanMessage(content=request.message)]},​
{"configurable": {"thread_id": request.thread_id}}​
)​
return ChatResponse(content=result["messages"][-1].content)​
关键点解析：​
1. lifespan
上下文管理器：​
◦ 应用启动时初始化MCP连接和Agent​
◦ 应用关闭时清理资源​
2. MultiServerMCPClient
：​
◦ 同时连接多个MCP服务器​
◦ 自动获取所有可用工具​
3. create_react_agent
：​
◦ 创建ReAct模式的Agent​
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
43
44
45
46

---

<!-- p.15 -->

◦ ReAct=Reasoning+Acting（推理+行动）​
4. checkpointer
：​
◦ 保存对话历史​
◦ 支持多轮对话​
3.4CLI客户端(client.py)​
代码块​
async def run_chat_loop() -> None:​
"""
启动 MCP-Agent
聊天循环"""​
​
# 1.
连接多台 MCP
服务器​
mcp_client = MultiServerMCPClient(servers_cfg)​
tools = await mcp_client.get_tools()​
​
# 2.
初始化大模型​
model = ChatTongyi(model=cfg.model)​
​
# 3.
构造 Agent
（带记忆）​
checkpointer = InMemorySaver()​
agent = create_react_agent(​
model=model, ​
tools=tools,​
prompt=prompt,​
checkpointer=checkpointer​
)​
​
# 4. CLI
聊天循环​
while True:​
user_input = input("\n
你: ").strip()​
if user_input.lower() == "quit":​
break​
​
result = await agent.ainvoke(​
{"messages": [{"role": "user", "content": user_input}]},​
config={"configurable": {"thread_id": "1"}} #
对话ID​
)​
print(f"\nAI: {result['messages'][-1].content}")​
​
# 5.
清理​
await mcp_client.cleanup()​
关键点解析：​
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

---

<!-- p.16 -->

1. thread_id
：用于区分不同的对话会话，保持上下文​
2. ainvoke
：异步调用Agent处理消息​
3. 消息格式：LangChain标准消息格式 {"role": "user", "content": "..."}
​
四、工作流程详解​
4.1ReActAgent工作原理​
ReAct（ReasoningandActing）是一种让LLM具备"思考-行动-观察"能力的模式：​
代码块​
┌───────────────────────────────────────────────────────────────
──┐​
│ ReAct
循环 │​
├───────────────────────────────────────────────────────────────
──┤​
│ │​
│
用户问题: "
查询北京天气并保存到文件" │​
│ │​
│ ┌─────────────────────────────────────────────────────────┐
│​
│ │
循环 1 │ │​
│ │ ┌──────────┐ │ │​
│ │ │
思考 │ "
首先需要查询北京的天气" │ │​
│ │ └────┬─────┘ │ │​
│ │ ▼ │ │​
│ │ ┌──────────┐ │ │​
│ │ │
行动 │
调用 query_weather("Beijing") │ │​
│ │ └────┬─────┘ │ │​
│ │ ▼ │ │​
│ │ ┌──────────┐ │ │​
│ │ │
观察 │
返回: "
 温度: 15°C..." │ │​
│ │ └──────────┘ │ │​
│ └─────────────────────────────────────────────────────────┘
│​
│ │ │​
│ ▼ │​
│ ┌─────────────────────────────────────────────────────────┐
│​
│ │
循环 2 │ │​
│ │ ┌──────────┐ │ │​
│ │ │
思考 │ "
已获取天气，现在需要保存到文件" │ │​
│ │ └────┬─────┘ │ │​
│ │ ▼ │ │​
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

<!-- p.17 -->

│ │ ┌──────────┐ │ │​
│ │ │
行动 │
调用 write_file("
北京天气: 15°C...") │ │​
│ │ └────┬─────┘ │ │​
│ │ ▼ │ │​
│ │ ┌──────────┐ │ │​
│ │ │
观察 │
返回: "
✅ 已成功写入文件" │ │​
│ │ └──────────┘ │ │​
│ └─────────────────────────────────────────────────────────┘
│​
│ │ │​
│ ▼ │​
│ ┌─────────────────────────────────────────────────────────┐
│​
│ │
最终回复 │ │​
│ │ "
我已查询到北京今天的天气（温度15°C
），并保存到文件中" │ │​
│ └─────────────────────────────────────────────────────────┘
│​
│ │​
└───────────────────────────────────────────────────────────────
──┘​
4.2MCP通信协议​
MCP支持两种通信方式：​
STDIO模式（本地进程）：​
代码块​
┌───────────────┐ stdin/stdout ┌───────────────┐​
│ MCP Client │ ◄───────────────► │ MCP Server │​
│ (Agent) │ │ (weather.py) │​
└───────────────┘ └───────────────┘​
SSE模式（远程服务）：​
代码块​
┌───────────────┐ HTTP/SSE ┌───────────────┐​
│ MCP Client │ ◄───────────────► │
远程 MCP │​
│ (Agent) │ │
服务器 │​
└───────────────┘ └───────────────┘​
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
1
2
3
4
1
2
3
4

---

<!-- p.18 -->

五、快速开始​
5.1环境准备​
代码块​
# 1.
克隆项目​
git clone <
项目地址>​
cd mcp-agent-project​
​
# 2.
创建虚拟环境​
python -m venv venv​
source venv/bin/activate # Windows: venv\Scripts\activate​
​
# 3.
安装依赖​
pip install -r requirements.txt​
5.2配置环境变量​
创建 .env
文件：​
代码块​
#
阿里通义千问 API Key​
DASHSCOPE_API_KEY=your_api_key_here​
​
#
模型名称（可选，默认 qwen-plus
）​
MODEL=qwen-plus​
​
# OpenWeather API Key
（天气服务需要）​
OPENWEATHER_API_KEY=your_openweather_key​
5.3运行方式​
方式一：CLI交互模式​
代码块​
python client.py​
方式二：API服务模式​
代码块​
#
启动服务​
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
1
1

---

<!-- p.19 -->

python api_server.py​
​
#
调用 API​
curl -X POST http://localhost:8000/chat \​
-H "Content-Type: application/json" \​
-d '{"message": "
北京今天天气怎么样？"}'​
方式三：单次调用​
代码块​
python client_simple.py​
六、扩展指南​
6.1添加新的MCP工具​
1. 创建新的服务器文件，如 calculator_server.py
：​
代码块​
from mcp.server.fastmcp import FastMCP​
​
mcp = FastMCP("CalculatorServer")​
​
@mcp.tool()​
async def calculate(expression: str) -> str:​
"""​
计算数学表达式。​
:param expression:
数学表达式，如 "2 + 3 * 4"​
:return:
计算结果​
"""​
try:​
result = eval(expression) #
注意：生产环境需要安全处理​
return f"
结果: {result}"​
except Exception as e:​
return f"
计算错误: {e}"​
​
if __name__ == "__main__":​
mcp.run(transport='stdio')​
2. 在 servers_config.json
中注册：​
2
3
4
5
6
7
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
12
13
14
15
16
17
18
19

---

<!-- p.20 -->

代码块​
{​
"mcpServers": {​
"calculator": {​
"command": "python",​
"args": ["calculator_server.py"],​
"transport": "stdio"​
}​
}​
}​
6.2自定义Prompt​
修改 agent_prompts.txt
：​
代码块​
你是一个专业的智能助手，具备以下能力：​
​
1. **
天气查询**
：可以查询全球各地的实时天气​
2. **
文件管理**
：可以将信息保存到本地文件​
3. **
地图导航**
：可以查询地点、规划路线​
​
使用指南：​
-
用户询问天气时，请使用 query_weather
工具​
-
需要保存信息时，请使用 write_file
工具​
-
涉及地点搜索时，请使用地图相关工具​
​
请以友好、专业的方式回复用户。​
七、常见问题​
Q1:MCP服务器启动失败？​
检查以下几点：​
• Python环境是否正确激活​
• 依赖是否完整安装​
• servers_config.json
路径配置是否正确​
Q2:APIKey无效？​
1
2
3
4
5
6
7
8
9
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

---

<!-- p.21 -->

• 确认 .env
文件存在且格式正确​
• 确认APIKey没有过期​
• 检查是否有多余的空格或引号​
Q3:工具调用失败？​
• 查看工具的文档字符串是否清晰描述了功能​
• 确认参数类型和名称是否正确​
• 检查网络连接（对于远程API）​
八、技术栈总结​
九、参考资料​
• MCP官方文档​
• LangGraph文档​
• LangChainMCPAdapters​
• 通义千问API​
