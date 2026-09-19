"""诊断端点：把一份提示的词元构成与余量报出来。只读、无副作用、**只在开发环境挂载**。"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.result import Result
from app.llm.budget import ContextBudget
from app.llm.tokens import Counter, Prompt, local_counter, official_counter

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])

COUNTER = Counter(official_counter(), local_counter())


class BudgetProbe(BaseModel):
    parts: dict[str, str] = Field(default_factory=dict)
    window: int = 200_000
    max_output: int = 4_096


@router.post("/_budget", response_model=Result)
def budget_probe(req: BudgetProbe) -> Result:
    c = COUNTER.report(Prompt(req.parts))
    v = ContextBudget(window=req.window, max_output=req.max_output).check(c)
    return Result.success({"input_tokens": c.input_tokens, "parts": c.parts,
                           "remaining": v.remaining, "fits": v.fits,
                           "over_water": v.over_water, "source": c.source})
