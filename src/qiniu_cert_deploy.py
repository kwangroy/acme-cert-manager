#!/usr/bin/env python3
"""Upload a certificate to Qiniu and bind it to one CDN domain."""

import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def qbox_token(path: str) -> str:
    key = os.environ["QINIU_SECRET_KEY"].encode()
    digest = hmac.new(key, (path + "\n").encode(), hashlib.sha1).digest()
    return "QBox " + os.environ["QINIU_ACCESS_KEY"] + ":" + base64.urlsafe_b64encode(digest).decode()


def qiniu_token(method: str, path: str, body: bytes, date: str) -> str:
    key = os.environ["QINIU_SECRET_KEY"].encode()
    data = (
        f"{method} {path}\n"
        "Host: api.qiniu.com\n"
        "Content-Type: application/json\n"
        f"X-Qiniu-Date: {date}\n\n"
    ).encode() + body
    digest = hmac.new(key, data, hashlib.sha1).digest()
    return "Qiniu " + os.environ["QINIU_ACCESS_KEY"] + ":" + base64.urlsafe_b64encode(digest).decode()


def request(url: str, method: str, body: dict, auth: str, extra_headers=None) -> dict:
    payload = json.dumps(body, separators=(",", ":")).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        method=method,
        headers={
            "Content-Type": "application/json",
            "Authorization": auth,
            **(extra_headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"Qiniu HTTP {exc.code}: {detail}") from exc


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: qiniu_cert_deploy.py DOMAIN FULLCHAIN KEY", file=sys.stderr)
        return 2

    domain, cert_path, key_path = sys.argv[1:]
    cert = open(cert_path, encoding="utf-8").read()
    private_key = open(key_path, encoding="utf-8").read()
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())

    upload_path = "/sslcert"
    upload = {"name": f"{domain}-{stamp}", "pri": private_key, "ca": cert}
    uploaded = request(
        "https://fusion.qiniuapi.com" + upload_path,
        "POST",
        upload,
        qbox_token(upload_path),
    )
    cert_id = uploaded.get("certID")
    if not cert_id:
        raise RuntimeError(f"Qiniu upload did not return certID: {uploaded}")

    config_path = "/domain/" + urllib.parse.quote(domain, safe="") + "/httpsconf"
    config = {
        "certId": cert_id,
        "forceHttps": True,
        "http2Enable": True,
        "tlsVersions": ["TLSv1.2", "TLSv1.3"],
    }
    date = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    result = request(
        "https://api.qiniu.com" + config_path,
        "PUT",
        config,
        qiniu_token(
            "PUT",
            config_path,
            json.dumps(config, separators=(",", ":")).encode(),
            date,
        ),
        {"X-Qiniu-Date": date},
    )
    if result.get("code") not in (None, 200):
        raise RuntimeError(f"Qiniu HTTPS update failed: {result}")
    print(f"updated {domain} with certificate {cert_id}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
