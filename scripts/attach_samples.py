#!/usr/bin/env python3
"""Attach sample image URLs to every notebook-capture item in HW-007."""
import json, urllib.request

BUILDER = "http://127.0.0.1:8000"
HW_ID = "HW-20260427-007"

# Mapping item -> sample SVG path (served by the deployed playable's static)
SAMPLES = {
    # Adaptive Quiz items by index
    "AQ_INDEX": ["/samples/aq_q1.png", "/samples/aq_q2.png", "/samples/aq_q3.png",
                 "/samples/aq_q4.png", "/samples/aq_q5.png"],
    # Real-Life sub-questions by key
    "RL": {
        "q1": "/samples/rl_q1.png",
        "q2": "/samples/rl_q2.png",
        "q3": "/samples/rl_q3.png",
    },
}


def http_get(url):
    return json.loads(urllib.request.urlopen(url, timeout=15).read().decode("utf-8"))

def http_put(url, body):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="PUT",
                                  headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))


def main():
    record = http_get(f"{BUILDER}/api/homeworks/{HW_ID}")
    c = record["content_json"]

    # Attach to gb_adaptive_quiz items
    for i, q in enumerate(c.get("gb_adaptive_quiz", [])):
        if q.get("capture") and i < len(SAMPLES["AQ_INDEX"]):
            q["notebook_sample"] = SAMPLES["AQ_INDEX"][i]
            print(f"  AQ Q{i+1} -> {q['notebook_sample']}")

    # Attach to real_life sub-questions
    rl = c.get("real_life") or {}
    for k, sample in SAMPLES["RL"].items():
        if k in rl and rl[k].get("capture"):
            rl[k]["notebook_sample"] = sample
            print(f"  RL {k} -> {sample}")

    http_put(f"{BUILDER}/api/homeworks/{HW_ID}", {"content_json": c})
    print("\n[OK] Sample paths attached to HW-20260427-007")


if __name__ == "__main__":
    main()
