"""Read the competition forum through the Kaggle API.

Usage:
    python3 scripts/forum.py list [pages]          # recent topics: id, last activity, comments, title
    python3 scripts/forum.py read 745775 [chars]   # one thread with all comments (each cut to `chars`)
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kaggle_api import get  # noqa: E402

FORUM_ID = 11630393  # gemma-4-developer-agent


def plain(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def list_topics(pages=2):
    for page in range(1, pages + 1):
        r = get("/api/i/discussions.DiscussionsService/GetTopicListByForumId",
                {"forumId": FORUM_ID, "page": page, "sortBy": "recent"})
        for t in r.get("topics", []):
            date = (t.get("lastCommentPostDate") or t.get("postDate") or "")[:10]
            print(f"{t['id']}  {date}  {t.get('commentCount') or 0:>3}  {t.get('authorType', ''):<6} {t.get('title')}")


def read_topic(topic_id, chars=1500):
    t = get("/api/i/discussions.DiscussionsService/GetForumTopicById",
            {"forumTopicId": topic_id, "includeComments": True}).get("forumTopic", {})
    first = t.get("firstMessage") or {}
    print(f"### {t.get('name')} (id {topic_id})")
    print(f"[OP {t.get('authorUserDisplayName')}]", (first.get("rawMarkdown") or plain(first.get("content")))[:chars])

    def walk(comments, depth=0):
        for c in comments or []:
            who = (c.get("author") or {}).get("displayName") or c.get("authorUserDisplayName")
            role = c.get("authorType") or ""
            body = c.get("rawMarkdown") or plain(c.get("content"))
            print("  " * depth + f"> [{who} | {role} | {str(c.get('postDate'))[:10]}]", body[:chars])
            walk(c.get("replies"), depth + 1)

    walk(t.get("comments"))


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("list", "read"):
        sys.exit(__doc__)
    if sys.argv[1] == "list":
        list_topics(int(sys.argv[2]) if len(sys.argv) > 2 else 2)
    else:
        read_topic(int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 1500)
