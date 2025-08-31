import os, json, hmac, hashlib, uuid
from datetime import datetime
LOG = "private/audit/security.jsonl"
SECRET = os.getenv("AUDIT_HMAC_SECRET","change-me")

def secure_log(event, data, sev="INFO"):
    e = {
        "ts": datetime.utcnow().isoformat()+"Z",
        "id": str(uuid.uuid4()),
        "type": event,
        "sev": sev,
        "data": data
    }
    e["hmac"] = hmac.new(
        SECRET.encode(),
        json.dumps(e, sort_keys=True).encode(),
        hashlib.sha256
    ).hexdigest()
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(e, separators=(",",":"))+"\n")
