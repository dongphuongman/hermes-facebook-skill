---
name: facebook-marketing
description: >
  Post content to a Facebook Page, like posts and comments, reply to comments,
  and fetch page activity using the Meta Graph API. Use this skill when the agent
  needs to publish Facebook posts, engage with audience comments, or run automated
  social media marketing for a Facebook Page.
  Requires FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN in the environment.
version: 1.0.0
license: MIT
platforms:
  - linux
  - macos
  - windows
required_environment_variables:
  - name: FB_PAGE_ID
    description: The numeric ID of your Facebook Page
  - name: FB_PAGE_ACCESS_TOKEN
    description: >
      Long-lived Page Access Token with permissions:
      pages_manage_posts, pages_read_engagement, pages_manage_engagement
metadata:
  category: social-media
  author: hermes-facebook-skill
---

# Facebook Marketing Skill

Connects Hermes to a Facebook Page via the Meta Graph API. Provides autonomous
posting, comment engagement, and rule-based reply logic for business Pages.

## When to Use

- The user asks you to post something on Facebook
- The user wants to engage with comments on their Page
- You are running a scheduled daily marketing loop
- You need to fetch recent posts or comments for analysis

## Procedure

### Setup (one-time)

1. Ensure `FB_PAGE_ID` and `FB_PAGE_ACCESS_TOKEN` are set in the environment.
   The connector loads them automatically from `.env` if present.
   With Hermes: `hermes config set fb_page_access_token <token>` writes to `.env`,
   `hermes config set FB_PAGE_ID <id>` writes an uppercase top-level config key.
2. Dependencies `requests` and `python-dotenv` ship with Hermes — nothing to install.

**`FB_APP_ID` / `FB_APP_SECRET` are NOT needed.** They appear in `.env.example`
but the connector never reads them.

### ⚠️ Publish gate — read before posting

`post_to_facebook()` creates an **unpublished draft by default**. A post only goes
live on the public Page when `FB_ALLOW_PUBLISH` is set:

```bash
hermes config set FB_ALLOW_PUBLISH true     # VIẾT HOA — top-level config key
```

Without it you will see, and the post stays a draft:

```
[facebook] publish bị chặn — đặt FB_ALLOW_PUBLISH=true để đăng thật.
Đang tạo bài nháp (unpublished).
```

This gate is specific to this fork. Upstream publishes immediately by default.

### Posting content

Import the connector by absolute path — this works regardless of the agent's
current working directory:

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.hermes-dev/skills/facebook/scripts"))
from connector import post_to_facebook

post_id = post_to_facebook(
    text="Your post text here.",
    link="https://yourbroker.ly/product",   # optional
    image_url="https://cdn.example.com/image.jpg",  # optional
    publish=True,  # False = save as draft
)
```

### Engaging with comments

```python
import sys, os
sys.path.insert(0, os.path.expanduser("~/.hermes-dev/skills/facebook/scripts"))
from connector import (
    get_page_comments,
    like_facebook_post,
    reply_to_facebook_comment,
)

comments = get_page_comments(post_id)
for comment in comments:
    like_facebook_post(comment["id"])
    # classify comment["message"] and call reply_to_facebook_comment if appropriate
```

### Reply decision logic

Classify the comment text before replying. See
`references/reply-templates.md` for bilingual (VI/EN) reply templates and
the full classification ruleset.

**Rule summary:**

| Comment type | Action |
|---|---|
| Price / quote request | Auto-reply with DM CTA |
| Compliment / positive | Auto-reply with thank-you |
| Claim / complaint / problem | Flag for human review, do NOT auto-reply |
| General question | Auto-reply with contact prompt |

### Flagging sensitive comments

Do not auto-reply when any of these keywords appear:
`claim, problem, issue, complaint, unhappy

Instead, output:
```
[REVIEW NEEDED] comment_id=<id> message="<text>"
```
and skip the `reply_to_facebook_comment` call.

## Available Functions

| Function | Description |
|---|---|
| `post_to_facebook(text, image_url, link, publish)` | Create a post — **draft unless `FB_ALLOW_PUBLISH=true`** |
| `like_facebook_post(post_id)` | Like a post or comment as the Page |
| `comment_on_facebook_post(post_id, text)` | Add a top-level comment |
| `reply_to_facebook_comment(comment_id, text)` | Reply to a comment |
| `get_page_comments(post_id, limit)` | Fetch comments on a post |
| `get_recent_posts(limit)` | Fetch the Page's recent feed |

## Daily Automation Loop (SOUL / cron prompt)

```
Every day at 09:00:
1. Generate 1–3 Facebook posts aligned with the content plan.
2. Call post_to_facebook() for each approved post.
3. Fetch comments on all posts from the last 7 days.
4. For each comment:
   a. Call like_facebook_post(comment_id).
   b. Classify the comment text.
   c. If safe to reply, call reply_to_facebook_comment(comment_id, reply).
   d. If sensitive, print REVIEW NEEDED and stop.
```

## Pitfalls

- **Tokens expire**: Long-lived tokens last ~60 days. Renew before expiry.
- **Rate limits**: Do not loop over hundreds of objects without a `time.sleep(0.5)` between calls.
- **Draft vs publish**: `publish=False` creates an unpublished post — it will not appear on the Page until manually published.
- **Likes on comments**: `like_facebook_post` works on both post IDs and comment IDs.

## Verification

Check the connection without touching the Page — this is read-only and posts nothing:

```bash
python ~/.hermes-dev/skills/facebook/scripts/connector.py
```

```
Facebook connector — kiểm tra kết nối (chỉ đọc, không đăng gì).
  FB_PAGE_ID       : 1234567890
  FB_ALLOW_PUBLISH : chưa bật — mọi bài sẽ là nháp
[facebook] Fetched 1 recent posts.
✓ Token hợp lệ. Bài gần nhất: <post_id>
```

After `post_to_facebook`, the function prints the resulting state:

```
[facebook] Post created [draft (unpublished)]. ID: <post_id>
[facebook] Post created [published]. ID: <post_id>
```

If you see `[facebook] Failed to post:` check that your token has not expired
and that `FB_PAGE_ID` is the numeric page ID, not the page username.

