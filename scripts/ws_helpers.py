import json
from urllib.parse import urlsplit, urlunsplit


def safe_event(raw):
    def redact(value):
        if isinstance(value, dict):
            return {key: redact(item) for key, item in value.items()}
        if isinstance(value, list):
            return [redact(item) for item in value]
        if isinstance(value, str) and "access_token=" in value:
            parsed = urlsplit(value)
            return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
        return value
    try:
        return json.dumps(redact(json.loads(raw)), ensure_ascii=False)
    except ValueError:
        return "Unrecognized server event"
