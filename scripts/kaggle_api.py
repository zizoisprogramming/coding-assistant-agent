"""Minimal Kaggle API helper.

Reads the API token from ~/.kaggle/access_token (never prints it) and calls Kaggle's
public (/api/v1/...) and internal (/api/i/...) endpoints.

Examples:
    from kaggle_api import get
    get("/api/v1/competitions/list?search=gemma-4-developer-agent")
    get("/api/i/competitions.PageService/ListPages", {"competitionId": 149921})
    blob = get("https://www.kaggle.com/api/v1/competitions/data/download/"
               "gemma-4-developer-agent/tasks.jsonl", raw=True)  # may be zip-wrapped
"""

import json
import os
import urllib.error
import urllib.request

TOKEN = open(os.path.expanduser("~/.kaggle/access_token")).read().strip()


def get(path, data=None, raw=False):
    """GET (or POST when `data` is given) a Kaggle API path; returns JSON, bytes, or an error dict."""
    url = path if path.startswith("http") else "https://www.kaggle.com" + path
    req = urllib.request.Request(
        url,
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"},
        data=json.dumps(data).encode() if data is not None else None,
    )
    try:
        body = urllib.request.urlopen(req, timeout=90).read()
        return body if raw else json.loads(body)
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read()[:300].decode(errors="replace")}
