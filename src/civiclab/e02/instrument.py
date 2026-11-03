import math


def score(response, party):
    values = []
    for key in ("democratic_party", "republican_party"):
        value = response.get(key)
        if value is None:
            return {"status": "MISSING", "primary": None, "absolute_gap": None}
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
            return {"status": "INVALID", "primary": None, "absolute_gap": None}
        values.append(value)
    difference = values[0] - values[1]
    return {"status": "VALID", "primary": difference if party == "D" else -difference if party == "R" else None,
            "absolute_gap": abs(difference)}


def change(pre, post, party):
    before, after = score(pre, party), score(post, party)
    if before["status"] != "VALID" or after["status"] != "VALID":
        return {"status": "INVALID_PAIR", "primary": None, "absolute_gap": None}
    return {"status": "VALID", "primary": None if before["primary"] is None else after["primary"] - before["primary"],
            "absolute_gap": after["absolute_gap"] - before["absolute_gap"]}
