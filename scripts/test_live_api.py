"""
Test script to verify live REST API inspection on running server.
"""
import json
import urllib.request
import uuid
from pathlib import Path

def test_api(image_path: str = "dataset/images/test/acceptance_01_pass_full.jpg"):
    url = "http://127.0.0.1:8080/inspect/image?operator=Factory-QA-Robot"
    test_img = Path(image_path)
    if not test_img.exists():
        print("Test image not found.")
        return

    boundary = uuid.uuid4().hex
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}

    with open(test_img, "rb") as f:
        file_bytes = f.read()

    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="file"; filename="test_000000.jpg"\r\n')
    body.extend(b"Content-Type: image/jpeg\r\n\r\n")
    body.extend(file_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(url, data=bytes(body), headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))

    print("==================================================")
    print("LIVE FASTAPI INSPECTION RESPONSE")
    print("==================================================")
    print("Inspection ID: ", res.get("inspection_id"))
    print("Overall Status:", res.get("overall_status"))
    print("Confidence:    ", f"{res.get('confidence', 0.0) * 100:.1f}%")
    print("Decision Reason:", res.get("reason"))
    print("Latency:       ", f"{res.get('timing', {}).get('total_time_ms', 0.0):.1f} ms")
    print("Evidence Path: ", res.get("evidence_path"))
    print("PDF Report:    ", res.get("report_path"))
    print("\nIndividual Safety Checks:")
    checks = res.get("checks", [])
    if isinstance(checks, list):
        for chk in checks:
            if isinstance(chk, dict):
                print(f"  - [{chk.get('status')}] {chk.get('rule_name')} (conf: {chk.get('confidence', 0.0)*100:.1f}%)")
    elif isinstance(checks, dict):
        for r_id, chk in checks.items():
            print(f"  - [{chk.get('status')}] {chk.get('rule_name', r_id)} (conf: {chk.get('confidence', 0.0)*100:.1f}%)")
    print("==================================================")

if __name__ == "__main__":
    test_api()
