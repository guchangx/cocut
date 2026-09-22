import time
from contextlib import contextmanager


class Tracer:
    def __init__(self):
        self.step = 0

    @contextmanager
    def span(self, name: str, **meta):
        self.step += 1
        stepid = self.step
        starttime = time.time()
        print(f"\n🔍 [TRACE #{stepid} 开始] ➔ {name} | 参数: {meta if meta else '无'}")

        info = {"status": "成功"}
        try:
            yield info
        except Exception as e:
            info["status"] = f"失败: {e}"
            raise e
        finally:
            cost = (time.time() - starttime) * 1000
            print(f"⏱️ [TRACE #{stepid} 结束] ➔ {name} | 耗时: {cost:.2f}ms | 状态: {info['status']}")


tracer = Tracer()