# tests/agent/test_loop.py —— 假模型 + 假时钟，不需要网络与数据库
from app.agent.loop import Budget, run_agent


TOOLS = {"search": lambda q: "结果A", "read": lambda i: f"正文{i}", "same": lambda i: "同一段正文"}


def policy(*decisions):
    def p(task, trace, wrap_up=False):
        if wrap_up:
            return {"thought": "收口", "final": True, "final_text": "已有信息下的最佳答案", "tokens": 10}
        n = len([e for e in trace.entries if not e.final])
        return decisions[min(n, len(decisions) - 1)]
    return p


def slow_clock(step):
    t = {"v": 0.0}

    def now():
        t["v"] += step
        return t["v"]
    return now


def test_达成时不留收口调用():
    r = run_agent("t", policy({"thought": "a", "action": "read", "arg": "1", "tokens": 10},
                              {"thought": "答案", "final": True, "tokens": 10}),
                  TOOLS, Budget())
    assert r.reason == "模型给出最终答案" and r.calls == 2 and r.answer == "答案"


def test_相同动作三次就停():
    n = {"v": 0}

    def bumpy(q):            # 结果每次都变，所以「无新事实」这一口径拦不住它
        n["v"] += 1
        return f"结果{n['v']}"

    r = run_agent("t", policy({"thought": "重复", "action": "search", "arg": "q", "tokens": 10}),
                  {"search": bumpy}, Budget())
    assert "相同动作" in r.reason and r.steps == 3


def test_无新事实拦住换参数的重复():
    r = run_agent("t", policy(*[{"thought": f"第{n}次", "action": "same", "arg": str(n), "tokens": 10}
                                for n in range(1, 9)]), TOOLS, Budget())
    assert r.reason.startswith("无新事实") and r.steps == 2


def test_空结果不算_没有新事实():
    """两次不同的检索都返回空，是「这条线索也没有」，不是「它在原地打转」。

    3.9 的评测集第一轮真机跑就撞上了：反向题（「有没有讲 X 的文章」）两条试验全被判成卡死，
    而模型其实已经给出了正确的「没有找到」。**「没找到」是一条结论，不是一次打转。**
    """
    empty = {"search": lambda q: "[]"}
    r = run_agent("t", policy({"thought": "搜一下", "action": "search", "arg": "Kubernetes",
                              "tokens": 10},
                              {"thought": "换个词再搜", "action": "search", "arg": "调度",
                               "tokens": 10},
                              # 循环把 final 那一轮的 `thought` 当作最终答案（策略层会把它拷到
                              # `final_text`），所以这两处写同一句话
                              {"thought": "没有找到讲 Kubernetes 调度的文章。", "final": True,
                               "tokens": 10,
                               "final_text": "没有找到讲 Kubernetes 调度的文章。"}),
                  empty, Budget())
    assert r.reason == "模型给出最终答案", r.reason
    assert r.answer == "没有找到讲 Kubernetes 调度的文章。"
    # 但同一动作原封不动地再来一次，仍然由口径一拦住
    r2 = run_agent("t", policy({"thought": "再搜", "action": "search", "arg": "K", "tokens": 10}),
                   empty, Budget())
    assert "相同动作" in r2.reason and r2.steps == 3


def test_不存在的工具在动它之前就被拦下():
    r = run_agent("t", policy({"thought": "删库", "action": "drop_db", "arg": "1", "tokens": 10}),
                  TOOLS, Budget())
    assert "不存在" in r.reason and r.steps == 1


def test_词元预算耗尽后仍给答案():
    r = run_agent("t", policy(*[{"thought": "读", "action": "read", "arg": str(n), "tokens": 100}
                                for n in range(1, 9)]), TOOLS, Budget(max_tokens=150))
    assert r.reason.startswith("预算耗尽") and r.answer


def test_墙钟超时可重复复现():
    r = run_agent("t", policy(*[{"thought": "读", "action": "read", "arg": str(n), "tokens": 1}
                                for n in range(1, 9)]),
                  TOOLS, Budget(max_tokens=9999, clock=slow_clock(12.0)))
    assert "超时" in r.reason and r.steps == 2
