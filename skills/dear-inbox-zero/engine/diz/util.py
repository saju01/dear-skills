import hashlib, json, re
from datetime import datetime, timedelta, timezone


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(obj):
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()


def parse_ts(s):
    if not s:
        return None
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
    s = s.strip().replace("Z", "+00:00")
    # Python 3.10 accepts only 3 or 6 fractional digits; Microsoft Graph sends 7.
    s = re.sub(r"(\.\d{6})\d+", r"\1", s)
    s = re.sub(r"\.(\d{1,5})(?=[+-]|$)", lambda m: "." + m.group(1).ljust(6, "0"), s)
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_utc():
    return datetime.now(timezone.utc)


def working_days_between(a, b):
    """Whole working days (Mon-Fri) from a to b."""
    if b <= a:
        return 0
    days, d = 0, a.date()
    while d < b.date():
        d += timedelta(days=1)
        if d.weekday() < 5:
            days += 1
    return days


_PREFIX = re.compile(r"^\s*((re|fw|fwd|aw|wg|antw|tr)\s*:\s*)+", re.I)
_DATE = re.compile(r"\b(\d{1,4}[-/.]\d{1,2}([-/.]\d{1,4})?|(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{0,4}|\d{1,2}(st|nd|rd|th)?)\b", re.I)
_NUM = re.compile(r"\d+")


def series_key(subject):
    s = _PREFIX.sub("", subject or "").lower()
    s = _DATE.sub(" ", s)
    s = _NUM.sub("#", s)
    s = re.sub(r"[^\w#]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def domain_of(addr):
    addr = (addr or "").lower()
    return addr.rsplit("@", 1)[1] if "@" in addr else ""


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        if default is not None:
            return default
        raise


def dump(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")
