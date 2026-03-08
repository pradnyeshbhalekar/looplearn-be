import razorpay
import os

_key_id = os.getenv("RAZORPAY_KEY_ID") or os.getenv("TEST_KEY_ID")
_key_secret = os.getenv("RAZORPAY_KEY_SECRET") or os.getenv("TEST_KEY_SECRET")
if not _key_id or not _key_secret:
    raise RuntimeError("Razorpay keys not configured")

razorpay_client = razorpay.Client(auth=(_key_id, _key_secret))
