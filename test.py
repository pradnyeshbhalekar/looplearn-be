from app.services.topic_compiler import compile_topic

result = compile_topic(
    "Load Balancing",
    [
        "Round Robin",
        "Least Connections",
        "Health Checks",
        "Horizontal Scaling",
        "Reverse Proxy"
    ]
)

print(result)