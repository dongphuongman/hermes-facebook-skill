import os
import unicodedata

import requests

# Load .env automatically so users can run this script directly
# without manually exporting environment variables.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; assume env vars are already set

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"

_HTTP_TIMEOUT = 30


def normalize_vi(text):
    """Chuẩn hoá chuỗi để so khớp từ khoá tiếng Việt.

    Bỏ dấu và hạ chữ thường, để "Khiếu Nại" và "khieu nai" cùng khớp một từ
    khoá. Người dùng Facebook Việt Nam rất hay gõ không dấu, nên so khớp chuỗi
    thô sẽ bỏ sót phần lớn bình luận thật — nguy hiểm nhất là bình luận khiếu
    nại không được nhận diện, agent tự trả lời thay vì đánh dấu cho người xem.

    Dùng cho CẢ HAI vế khi so khớp:

        msg = normalize_vi(comment["message"])
        if any(normalize_vi(w) in msg for w in TU_KHOA):
            ...
    """
    text = unicodedata.normalize("NFD", str(text or "").lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # "đ" không phải dấu tổ hợp nên NFD không tách được, phải thay riêng.
    return text.replace("đ", "d")


def _page_id():
    return os.getenv("FB_PAGE_ID")


def _token():
    return os.getenv("FB_PAGE_ACCESS_TOKEN")


def _check_env():
    if not _page_id() or not _token():
        raise EnvironmentError(
            "FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN must be set.\n"
            "Copy .env.example to .env and fill in your credentials."
        )


def _auth_headers():
    """PATCH: gửi token qua header thay vì query string.

    Upstream đặt access_token vào ``params`` cho các lời gọi GET, nên token
    lọt vào access log của server/proxy. Graph API v19 chấp nhận
    ``Authorization: Bearer``.
    """
    return {"Authorization": f"Bearer {_token()}"}


def _safe_err(response, data):
    """PATCH: không in ``response.text`` thô.

    Upstream fallback về ``response.text`` khi Meta không trả JSON có
    ``error.message`` — thân phản hồi có thể chứa lại tham số request (kèm
    token) và bị in thẳng ra chat/log. Hàm này lấy message của Meta, cắt ngắn,
    và che token nếu nó lọt vào chuỗi.
    """
    msg = ""
    if isinstance(data, dict):
        msg = str((data.get("error") or {}).get("message") or "")
    if not msg:
        msg = f"HTTP {response.status_code} (phản hồi không phải JSON hợp lệ)"
    token = _token()
    if token and token in msg:
        msg = msg.replace(token, "<token bị che>")
    return msg[:200]


def _publish_allowed(explicit):
    """PATCH: chốt an toàn — ``publish=True`` chỉ có tác dụng khi bật cờ.

    Skill này đăng bài lên một Facebook Page CÔNG KHAI. Upstream mặc định
    ``publish=True``, nên một lời gọi sai của agent là bài lên Page ngay lập
    tức, không thu hồi được. Mặc định của fork này là tạo bài nháp
    (unpublished); muốn đăng thật phải đặt ``FB_ALLOW_PUBLISH=true``.
    """
    if not explicit:
        return False
    return os.getenv("FB_ALLOW_PUBLISH", "").strip().lower() in {"1", "true", "yes"}


def post_to_facebook(text, image_url=None, link=None, publish=True):
    """
    Publish a post to the Facebook Page.
    Returns the new post ID on success, None on failure.

    Mặc định tạo bài NHÁP. Đặt FB_ALLOW_PUBLISH=true trong môi trường để bài
    được đăng công khai thật.
    """
    _check_env()

    will_publish = _publish_allowed(publish)
    if publish and not will_publish:
        print(
            "[facebook] publish bị chặn — đặt FB_ALLOW_PUBLISH=true để đăng thật. "
            "Đang tạo bài nháp (unpublished)."
        )

    # PATCH: Graph API kỳ vọng chuỗi lowercase; requests encode bool Python
    # thành "True"/"False".
    published_param = "true" if will_publish else "false"

    if image_url:
        url = f"{GRAPH_API_BASE}/{_page_id()}/photos"
        payload = {
            "caption": text,
            "url": image_url,
            "published": published_param,
            "access_token": _token(),
        }
    else:
        url = f"{GRAPH_API_BASE}/{_page_id()}/feed"
        payload = {
            "message": text,
            "published": published_param,
            "access_token": _token(),
        }
        if link:
            payload["link"] = link

    response = requests.post(url, data=payload, timeout=_HTTP_TIMEOUT)
    data = response.json()

    if response.ok and ("id" in data or "post_id" in data):
        post_id = data.get("id") or data.get("post_id")
        state = "published" if will_publish else "draft (unpublished)"
        print(f"[facebook] Post created [{state}]. ID: {post_id}")
        return post_id

    print(f"[facebook] Failed to post: {_safe_err(response, data)}")
    return None


def like_facebook_post(post_id):
    """
    Like a post or comment as the Page.
    Returns True on success, False on failure.
    """
    _check_env()

    url = f"{GRAPH_API_BASE}/{post_id}/likes"
    response = requests.post(
        url, data={"access_token": _token()}, timeout=_HTTP_TIMEOUT
    )
    data = response.json()

    if response.ok and data.get("success"):
        print(f"[facebook] Liked: {post_id}")
        return True

    print(f"[facebook] Failed to like {post_id}: {_safe_err(response, data)}")
    return False


def comment_on_facebook_post(post_id, text):
    """
    Post a top-level comment on a Facebook post.
    Returns the new comment ID on success, None on failure.
    """
    _check_env()

    url = f"{GRAPH_API_BASE}/{post_id}/comments"
    payload = {"message": text, "access_token": _token()}

    response = requests.post(url, data=payload, timeout=_HTTP_TIMEOUT)
    data = response.json()

    if response.ok and "id" in data:
        print(f"[facebook] Comment posted on {post_id}. ID: {data['id']}")
        return data["id"]

    print(f"[facebook] Failed to comment on {post_id}: {_safe_err(response, data)}")
    return None


def reply_to_facebook_comment(comment_id, text):
    """
    Reply to an existing comment.
    Returns the new reply ID on success, None on failure.
    """
    _check_env()

    url = f"{GRAPH_API_BASE}/{comment_id}/comments"
    payload = {"message": text, "access_token": _token()}

    response = requests.post(url, data=payload, timeout=_HTTP_TIMEOUT)
    data = response.json()

    if response.ok and "id" in data:
        print(f"[facebook] Replied to {comment_id}. Reply ID: {data['id']}")
        return data["id"]

    print(f"[facebook] Failed to reply to {comment_id}: {_safe_err(response, data)}")
    return None


def get_page_comments(post_id, limit=25):
    """
    Fetch recent comments on a post.
    Returns a list of dicts with keys: id, message, from, created_time.
    """
    _check_env()

    url = f"{GRAPH_API_BASE}/{post_id}/comments"
    params = {"fields": "id,message,from,created_time", "limit": limit}

    response = requests.get(
        url, params=params, headers=_auth_headers(), timeout=_HTTP_TIMEOUT
    )
    data = response.json()

    if response.ok and "data" in data:
        comments = data["data"]
        print(f"[facebook] Fetched {len(comments)} comments from {post_id}.")
        return comments

    print(f"[facebook] Failed to fetch comments for {post_id}: {_safe_err(response, data)}")
    return []


def get_recent_posts(limit=10):
    """
    Fetch the Page's recent posts.
    Returns a list of dicts with keys: id, message, created_time.
    """
    _check_env()

    url = f"{GRAPH_API_BASE}/{_page_id()}/feed"
    params = {"fields": "id,message,created_time", "limit": limit}

    response = requests.get(
        url, params=params, headers=_auth_headers(), timeout=_HTTP_TIMEOUT
    )
    data = response.json()

    if response.ok and "data" in data:
        posts = data["data"]
        print(f"[facebook] Fetched {len(posts)} recent posts.")
        return posts

    print(f"[facebook] Failed to fetch posts: {_safe_err(response, data)}")
    return []


if __name__ == "__main__":
    # không được phép để lại dấu vết trên Page của người dùng, nên kiểm tra
    # kết nối bằng một lời gọi CHỈ-ĐỌC.
    print("Facebook connector — kiểm tra kết nối (chỉ đọc, không đăng gì).")
    _check_env()

    _allow = os.getenv("FB_ALLOW_PUBLISH", "").strip().lower() in {"1", "true", "yes"}
    print(f"  FB_PAGE_ID       : {_page_id()}")
    print(
        "  FB_ALLOW_PUBLISH : "
        + ("true — post_to_facebook SẼ đăng thật" if _allow else "chưa bật — mọi bài sẽ là nháp")
    )

    _posts = get_recent_posts(limit=1)
    if _posts:
        print(f"✓ Token hợp lệ. Bài gần nhất: {_posts[0].get('id')}")
    else:
        print("✗ Không đọc được feed. Kiểm tra token còn hạn và FB_PAGE_ID là ID số của Page.")
