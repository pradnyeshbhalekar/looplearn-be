import threading
import time

class RateLimiter:
    def __init__(self,delay_seconds=2.0):
        self.delay = delay_seconds
        self.lock = threading.Lock()
        self.last_call_time = 0.0

    def execute(self, func, *args, **kwargs):
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_call_time
            
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)

            try:
                result = func(*args, **kwargs)
            finally:
                self.last_call_time = time.time()

            return result


llm_limiter = RateLimiter(delay_seconds=2.0)