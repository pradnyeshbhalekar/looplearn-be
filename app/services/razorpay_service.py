import razorpay
import os
from tenacity import retry, stop_after_attempt, wait_exponential

_key_id = os.getenv("RAZORPAY_KEY_ID") or os.getenv("TEST_KEY_ID")
_key_secret = os.getenv("RAZORPAY_KEY_SECRET") or os.getenv("TEST_KEY_SECRET")
if not _key_id or not _key_secret:
    raise RuntimeError("Razorpay keys not configured")

razorpay_client = razorpay.Client(auth=(_key_id, _key_secret))

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=20), reraise=True)
def create_plan(period: str, interval: int, item: dict):
    return razorpay_client.plan.create({
        "period": period,
        "interval": interval,
        "item": item
    })

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=20), reraise=True)
def create_subscription(plan_id: str, total_count: int, customer_notify: int, notes: dict):
    return razorpay_client.subscription.create({
        "plan_id": plan_id,
        "total_count": total_count,
        "customer_notify": customer_notify,
        "notes": notes
    })
