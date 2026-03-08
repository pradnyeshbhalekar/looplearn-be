import json
import hmac
import hashlib
import argparse
import os
import urllib.request

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--user-id", required=True)
    p.add_argument("--plan-id", required=True)
    p.add_argument("--event", default="subscription.activated")
    p.add_argument("--rzp-sub-id", default="sub_test_123")
    p.add_argument("--secret", default=os.getenv("RAZORPAY_WEBHOOK_SECRET", ""))
    args = p.parse_args()

    payload = {
        "event": args.event,
        "payload": {
            "subscription": {
                "entity": {
                    "id": args.rzp_sub_id,
                    "status": "active" if args.event == "subscription.activated" else "paused",
                    "notes": {
                        "user_id": args.user_id,
                        "plan_id": args.plan_id
                    }
                }
            }
        }
    }
    body = json.dumps(payload).encode()
    sig = hmac.new(args.secret.encode(), body, hashlib.sha256).hexdigest()
    req = urllib.request.Request(args.url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Razorpay-Signature", sig)
    try:
        with urllib.request.urlopen(req) as r:
            print(r.status)
            print(r.read().decode())
    except urllib.error.HTTPError as e:
        print(e.code)
        print(e.read().decode())

if __name__ == "__main__":
    main()
