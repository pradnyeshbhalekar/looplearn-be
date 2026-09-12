from groq import Groq

_client = None


def get_groq_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq()
    return _client
