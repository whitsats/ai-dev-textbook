"""让 `pytest` 直接可用：把项目根放进 sys.path。

参考实现是**拷贝出去就能跑**的：不依赖 pip install -e，也不依赖环境变量里的 PYTHONPATH。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
