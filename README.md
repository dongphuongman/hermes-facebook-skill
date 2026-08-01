# hermes-facebook-skill (bản fork)

Skill cắm-là-chạy cho [Hermes Agent của Nous Research](https://github.com/NousResearch/hermes-agent),
kết nối agent với một Trang Facebook qua Meta Graph API.

Thiết kế cho môi giới bảo hiểm và tái bảo hiểm — và bất kỳ doanh nghiệp nào — muốn
làm marketing Facebook tự động theo luật định sẵn mà không cần đội chuyên trách.

---

## Skill này làm được gì

- Đăng bài lên Trang Facebook (chữ, ảnh, liên kết)
- Tự động thích bài viết và bình luận với tư cách Trang
- Đăng bình luận và trả lời bình luận theo luật định sẵn, song ngữ
- Lấy về bài viết và bình luận gần đây để agent xử lý
- Đánh dấu bình luận nhạy cảm (khiếu nại, phàn nàn) để người thật xem trước khi trả lời

---

## Cấu trúc kho mã

```
hermes-facebook-skill/
├── skills/
│   └── facebook/               <- chép nguyên thư mục này vào ~/.hermes/skills/facebook/
│       ├── SKILL.md            <- định nghĩa skill theo chuẩn agentskills.io, Hermes nạp file này
│       ├── scripts/
│       │   └── connector.py    <- connector Meta Graph API
│       └── references/
│           └── reply-templates.md  <- mẫu câu trả lời song ngữ Anh/Việt
├── .env.example                <- mẫu khai báo thông tin đăng nhập
├── .gitignore
├── README.md
└── LICENSE
```

---

## Yêu cầu trước khi cài

- Đã cài [Hermes Agent](https://github.com/NousResearch/hermes-agent)
- Python 3.9 trở lên
- `requests` và `python-dotenv` — **đã có sẵn trong Hermes**, không cần cài thêm
- Một Meta Developer App đã liên kết với Trang Facebook
- Một Page Access Token dài hạn với các quyền:
  - `pages_manage_posts`
  - `pages_read_engagement`
  - `pages_manage_engagement`

Cách lấy token dài hạn, theo hướng dẫn của Meta:
<https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived>

---

## Cài đặt

**Bước 1.** Tải hoặc clone kho mã này về.

**Bước 2.** Chép thư mục skill vào thư mục skills của Hermes:

```bash
cp -R skills/facebook "$HERMES_HOME/skills/facebook"
```

`$HERMES_HOME` mặc định là `~/.hermes`; kiểm tra bằng `hermes config path`.

**Bước 3.** Khai báo thông tin đăng nhập.

Cách gọn nhất là dùng chính lệnh của Hermes, không phải sửa file tay:

```bash
hermes config set fb_page_access_token <token>   # tự ghi vào .env
hermes config set FB_PAGE_ID <mã-số-trang>       # ghi vào config.yaml, VIẾT HOA
```

> Khoá cấp cao nhất **bắt buộc VIẾT HOA**. Hermes chuyển khoá cấp cao nhất sang biến môi
> trường giữ nguyên văn tên, nên `fb_page_id` viết thường sẽ thành `fb_page_id` — connector
> đọc `FB_PAGE_ID` nên không thấy, mà lệnh cũng không báo lỗi gì.

Hoặc chép `.env.example` rồi điền tay:

```bash
cp .env.example "$HERMES_HOME/skills/facebook/.env"
```

**Bước 4.** Thư viện phụ thuộc — không cần cài gì.

`requests` và `python-dotenv` đi kèm Hermes. Kiểm tra:

```bash
python -c "import requests, dotenv; print('ok')"
```

**Bước 5.** Kiểm tra connector — chỉ đọc, không đăng gì:

```bash
python "$HERMES_HOME/skills/facebook/scripts/connector.py"
```

Nó lấy về một bài gần nhất để xác nhận token còn dùng được, và in trạng thái
`FB_ALLOW_PUBLISH`. **Bản fork này không bao giờ đăng bài khi chạy thử.** Bản gốc đăng
một bài thật ở bước này.

**Bước 6.** Khởi động lại Hermes (hoặc gửi `/reset`) để nó nhận skill mới:

```bash
hermes skills list | grep -i facebook     # kỳ vọng: facebook-marketing ... enabled
```

---

## Hermes kích hoạt skill này thế nào

Hermes đọc phần frontmatter của `SKILL.md` lúc khởi động. Trường `description` đóng vai
trò điều kiện kích hoạt. Khi bạn giao cho Hermes một việc như:

> "Đăng bài về gói bảo hiểm xe máy lên Facebook"
> "Kiểm tra bình luận mới trên trang và trả lời"
> "Chạy vòng marketing Facebook hằng ngày"

...Hermes sẽ nạp toàn bộ nội dung `SKILL.md`, đọc quy trình, rồi gọi các hàm trong
`connector.py` tương ứng.

---

## Bắt đầu nhanh — đoạn mã Python

Bạn cũng có thể gọi connector trực tiếp từ script Python của mình hoặc từ một plugin Hermes:

```python
import sys, os
# os.path.expanduser là BẮT BUỘC — sys.path KHÔNG tự mở rộng dấu "~",
# thiếu nó sẽ báo ModuleNotFoundError: No module named 'connector'.
sys.path.insert(0, os.path.expanduser("~/.hermes/skills/facebook/scripts"))

from connector import (
    normalize_vi,
    post_to_facebook,
    like_facebook_post,
    reply_to_facebook_comment,
    get_page_comments,
    get_recent_posts,
)

# Connector tự nạp .env — không cần gọi load_dotenv() thủ công.

# 1. Tạo bài đăng — là bài NHÁP trừ khi đã đặt FB_ALLOW_PUBLISH=true
post_id = post_to_facebook(
    text="Bảo vệ doanh nghiệp của bạn với các gói bảo hiểm thương mại. Liên hệ ngay hôm nay.",
    link="https://yourbroker.ly/commercial"
)

# 2. Lấy bình luận về và xử lý
comments = get_page_comments(post_id)

NHAY_CAM = ["khiếu nại", "bồi thường", "phàn nàn", "sự cố", "lừa đảo",
            "không hài lòng", "thất vọng", "claim", "complaint", "problem"]
HOI_GIA  = ["giá", "bao nhiêu", "phí", "báo giá", "chi phí",
            "price", "cost", "quote", "how much"]
TICH_CUC = ["cảm ơn", "tuyệt", "uy tín", "hài lòng", "ủng hộ",
            "thank", "great", "excellent"]

for comment in comments:
    cid     = comment["id"]
    # normalize_vi bỏ dấu + hạ chữ thường, để "toi muon khieu nai" khớp
    # được từ khoá "khiếu nại". Phải áp cho CẢ HAI vế khi so sánh.
    message = normalize_vi(comment["message"])

    # Luôn thích mọi bình luận
    like_facebook_post(cid)

    if any(normalize_vi(w) in message for w in NHAY_CAM):
        print(f"[REVIEW NEEDED] comment_id={cid} message=\"{comment['message']}\"")

    elif any(normalize_vi(w) in message for w in HOI_GIA):
        reply_to_facebook_comment(
            cid,
            "Cảm ơn bạn đã quan tâm! Vui lòng nhắn tin trực tiếp kèm thông tin "
            "để chúng tôi chuẩn bị báo giá phù hợp cho bạn."
        )

    elif any(normalize_vi(w) in message for w in TICH_CUC):
        reply_to_facebook_comment(
            cid,
            "Chúng tôi rất trân trọng lời khen của bạn! Ghé thăm website để biết thêm."
        )

    else:
        reply_to_facebook_comment(
            cid,
            "Cảm ơn bạn đã liên hệ! Vui lòng nhắn tin trực tiếp để được hỗ trợ thêm."
        )
```

---

## Thiết kế tính cách cho agent

### Vòng tự động hằng ngày

Giao cho Hermes chạy các việc này mỗi ngày (cú pháp lịch bằng ngôn ngữ tự nhiên):

```
Mỗi ngày lúc 09:00:
  - Soạn 1-3 bài Facebook từ kế hoạch nội dung tháng và đăng lên.
  - Lấy toàn bộ bình luận trong 7 ngày gần nhất trên các bài của trang.
  - Với mỗi bình luận: thích nó, phân loại, và trả lời nếu phù hợp.
  - Đánh dấu bình luận nhạy cảm cho người thật xem, tuyệt đối không tự trả lời.
```

### Mẫu SOUL / system prompt

Thêm khối này vào file SOUL của Hermes hoặc system prompt của agent:

```
Bạn là agent marketing Facebook cho [TÊN_DOANH_NGHIỆP], một nhà môi giới bảo hiểm
và tái bảo hiểm tại [QUỐC_GIA].

Giọng điệu chuyên nghiệp, ấm áp, song ngữ (Việt và Anh).
Bạn có quyền dùng skill facebook-marketing.

Khi thấy bình luận mới trên bài của doanh nghiệp, xử lý theo luật sau:

  HỎI GIÁ hoặc XIN BÁO GIÁ
  (từ khoá: giá, bao nhiêu, phí, báo giá, chi phí, price, cost, quote)
  → Trả lời: "Cảm ơn bạn đã quan tâm! Vui lòng nhắn tin trực tiếp kèm thông tin
    để chúng tôi chuẩn bị báo giá phù hợp."
  → Gọi: reply_to_facebook_comment(comment_id, nội_dung_trả_lời)

  KHEN NGỢI hoặc PHẢN HỒI TÍCH CỰC
  (từ khoá: cảm ơn, tuyệt, uy tín, hài lòng, ủng hộ, thank, great)
  → Trả lời: "Chúng tôi rất trân trọng lời khen của bạn! Ghé [WEBSITE] để biết thêm."
  → Gọi: reply_to_facebook_comment(comment_id, nội_dung_trả_lời)

  KHIẾU NẠI, SỰ CỐ hoặc PHÀN NÀN
  (từ khoá: khiếu nại, bồi thường, phàn nàn, sự cố, lừa đảo, claim, complaint)
  → TUYỆT ĐỐI KHÔNG tự trả lời.
  → In ra: "[REVIEW NEEDED] comment_id=<id> message=<nội dung>"

  CÂU HỎI CHUNG hoặc TRƯỜNG HỢP KHÁC
  → Trả lời: "Cảm ơn bạn! Vui lòng nhắn tin hoặc gọi [SỐ_ĐIỆN_THOẠI] để biết thêm."
  → Gọi: reply_to_facebook_comment(comment_id, nội_dung_trả_lời)

BỎ QUA DẤU khi so khớp từ khoá — người dùng hay gõ không dấu, "toi muon khieu nai"
phải xử lý y như "tôi muốn khiếu nại".

Luôn gọi like_facebook_post(comment_id) cho mọi bình luận trước khi quyết định trả lời.

Với bài đăng hằng ngày, soạn nội dung quanh các chủ đề: bảo hiểm xe cơ giới, bảo hiểm
sức khoẻ, bảo hiểm hàng hoá đường biển, cháy nổ và tài sản, bảo hiểm nhân thọ, tái bảo
hiểm. Mỗi bài 2-4 câu, có lời kêu gọi hành động và hashtag tiếng Việt lẫn Anh.
```

### Bảng tra thiết lập tự động hoá

> ⚠️ **`AUTO_PUBLISH_POSTS`, `AUTO_LIKE_COMMENTS`, `AUTO_REPLY_COMMENTS` không được
> `connector.py` đọc.** Chúng chỉ là gợi ý hành vi cho agent, không phải chốt chặn kỹ
> thuật. Chốt duy nhất có hiệu lực thật là **`FB_ALLOW_PUBLISH`** .

| Chức năng | Thiết lập | Có hiệu lực? | Lý do |
|---|---|---|---|
| **Xuất bản bài** | `FB_ALLOW_PUBLISH=true` | ✅ **có** — code kiểm tra | không bật thì mọi bài là nháp |
| Đăng bài | `AUTO_PUBLISH_POSTS=true` | ❌ chỉ là gợi ý cho agent | an toàn với nội dung đã lên lịch |
| Thích bình luận | `AUTO_LIKE_COMMENTS=true` | ❌ chỉ là gợi ý cho agent | không rủi ro, tạo tín hiệu tích cực |
| Trả lời câu hỏi | `AUTO_REPLY_COMMENTS=true` | ❌ chỉ là gợi ý cho agent | theo luật định sẵn, rủi ro thấp |
| Trả lời phàn nàn | luôn làm thủ công | ❌ chỉ là gợi ý cho agent | không bao giờ tự trả lời khách đang bực |

---

## Hướng dẫn an toàn và tự động hoá

- **Tuyệt đối không commit file `.env` lên GitHub.** File `.gitignore` trong kho này đã
  loại trừ sẵn. Page Access Token cho phép đăng bài toàn quyền lên trang doanh nghiệp
  của bạn.
- **Giới hạn tần suất**: Meta áp giới hạn gọi API theo app và theo trang. Thêm
  `time.sleep(0.3)` giữa các lời gọi khi xử lý lô bình luận lớn.
- **Tránh trả lời lặp lại**: bộ phân loại theo luật ở trên bảo đảm mỗi câu trả lời bám
  đúng ngữ cảnh. Đừng gửi cùng một câu chung chung cho mọi bình luận.
- **Token hết hạn**: token dài hạn sống khoảng 60 ngày. Đặt lịch nhắc làm mới
  `FB_PAGE_ACCESS_TOKEN` trước khi hết hạn.
- **Giữ quyền tối thiểu**: chỉ xin đúng ba quyền liệt kê ở phần Yêu cầu. Thu hồi mọi
  quyền thừa trong bảng điều khiển Meta App.

---

## Giấy phép

Giấy phép MIT. Xem file `LICENSE`.
