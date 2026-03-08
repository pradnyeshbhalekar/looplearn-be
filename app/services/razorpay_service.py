import razorpay
import os


razorpay_client = razorpay.Client(auth=(
    os.getenv('TEST_KEY_ID'),
    os.getenv("TEST_KEY_SECRET")
))