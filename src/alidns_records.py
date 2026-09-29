#!/usr/bin/env python3
import base64
import hashlib
import hmac
import json
import os
import sys
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone


def enc(value):
    return urllib.parse.quote(str(value), safe="-_.~")


def call(action, extra):
    params = {
        "AccessKeyId": os.environ["ALIYUN_ACCESS_KEY_ID"],
        "Action": action,
        "Format": "JSON",
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": str(uuid.uuid4()),
        "SignatureVersion": "1.0",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Version": "2015-01-09",
        **extra,
    }
    canonical = "&".join(f"{enc(k)}={enc(params[k])}" for k in sorted(params))
    string_to_sign = "GET&%2F&" + enc(canonical)
    signature = base64.b64encode(
        hmac.new(
            (os.environ["ALIYUN_ACCESS_KEY_SECRET"] + "&").encode(),
            string_to_sign.encode(),
            hashlib.sha1,
        ).digest()
    ).decode()
    params["Signature"] = signature
    url = "https://alidns.aliyuncs.com/?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode())


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "list"
    if action == "list":
        domain = os.environ.get("ALIYUN_DOMAIN", "example.com")
        result = call("DescribeDomainRecords", {"DomainName": domain, "PageSize": "100"})
        for record in result.get("DomainRecords", {}).get("Record", []):
            print(json.dumps({k: record.get(k) for k in ("RecordId", "RR", "Type", "Value", "Status")}, ensure_ascii=False))
        return 0
    if action == "update":
        if len(sys.argv) != 3:
            print("usage: alidns_records.py update RECORD_ID", file=sys.stderr)
            return 2
        value = os.environ.get("ALIYUN_RECORD_VALUE")
        if not value:
            print("ALIYUN_RECORD_VALUE is required for update", file=sys.stderr)
            return 2
        result = call("UpdateDomainRecord", {
            "RecordId": sys.argv[2],
            "RR": os.environ.get("ALIYUN_RECORD_RR", "@"),
            "Type": os.environ.get("ALIYUN_RECORD_TYPE", "A"),
            "Value": value,
        })
        print(json.dumps({k: result.get(k) for k in ("RecordId", "RequestId", "Code", "Message")}, ensure_ascii=False))
        return 0 if "Code" not in result else 1
    print("unknown action", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
