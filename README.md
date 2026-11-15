# ⚡ WheyStore - Hệ Thống E-Commerce Thực Phẩm Bổ Sung Thể Hình Chính Hãng

Dự án **WheyStore** là nền tảng thương mại điện tử chuyên nghiệp dành cho cộng đồng Gymer & Fitness Athletes tại Việt Nam, được xây dựng bằng **Django**, **GSAP 3.12+** (60fps GPU-accelerated animations), **Chart.js** và chuẩn **SEO / Google Rich Results JSON-LD Schema**.

---

## 🎨 Phong Cách Thiết Kế & Bảng Màu Chủ Đạo
- **Nền Đen Nhám (Matte Black):** `#222222` / `#181818` / `#2A2A2A`
- **Chữ Trắng Sáng (Bright White):** `#F4F4F4`
- **Điểm Nhấn & Nút Bấm (Crimson Red):** `#D33F49`

---

## 🚀 Tính Năng Nổi Bật

### 1. Danh Mục & 10 Sản Phẩm Thực Tế Bán Chạy Nhất Thị Trường Việt Nam
- **4 Danh mục chuẩn:** `Whey Protein Isolate`, `Hydrolyzed Whey`, `Mass Gainer (Tăng cân)`, `Pre-Workout & Creatine`.
- **10 Sản phẩm chính hãng** kèm bộ ảnh Studio 800x800px sắc nét (`media/products/`):
  1. **Rule 1 R1 Protein 5lbs (2.3kg)** (`Rule 1` - USA)
  2. **Optimum Nutrition Gold Standard 100% Whey 5lbs** (`Optimum Nutrition` - USA)
  3. **Dymatize ISO 100 Hydrolyzed 5lbs (2.27kg)** (`Dymatize` - USA)
  4. **BPI Sports ISO HD 100% Pure Isolate 5lbs** (`BPI Sports` - USA)
  5. **Applied Nutrition ISO-XP 100% Whey Isolate 2kg** (`Applied Nutrition` - UK)
  6. **Mutant ISO Surge 5lbs (2.27kg)** (`Mutant` - USA)
  7. **BioTechUSA Hydro Whey Zero 1.8kg** (`BioTechUSA` - USA)
  8. **Labrada Muscle Mass Gainer 12lbs (5.4kg)** (`Labrada` - USA)
  9. **Cellucor C4 Original Pre-Workout (60 Servings)** (`Cellucor` - USA)
  10. **OstroVit Creatine Monohydrate 500g** (`OstroVit` - Poland)

### 2. Công Cụ Tính Macro & Gợi Ý Whey (AI Fitness Coach)
- Tính toán chính xác **TDEE (Calories/ngày)** và **Lượng Protein cần nạp (g/ngày)** theo công thức Mifflin-St Jeor dựa trên Giới tính, Độ tuổi, Chiều cao, Cân nặng, Cường độ tập luyện và Mục tiêu (`Lean Bulk`, `Cutting`, `Mass Gain`).
- Hiệu ứng đếm số GSAP Counter mượt mà và tự động gợi ý Combo Whey/Pre-Workout phù hợp nhất.

### 3. Tìm Kiếm, Bộ Lọc & Sắp Xếp Trực Tiếp (Live Filter + GSAP Flip)
- Lọc tức thì theo tên sản phẩm, thương hiệu, mùi vị, khoảng giá và sắp xếp giá tăng/giảm với chuyển động bố cục **GSAP Flip 60fps** không cần tải lại trang.

### 4. Giỏ Hàng Session, Mã Giảm Giá (Voucher) & Thanh Toán VietQR Động
- Hỗ trợ mã giảm giá (`GYMBRO10` giảm 10%, `WHEYVIP20` giảm 20%).
- Đặt hàng kèm kiểm tra tồn kho (`transaction.atomic`), tự động trừ `stock` và sinh mã **QR Chuyển khoản VietQR** động theo đúng số tiền & mã đơn hàng `#DH<id>`.
- Hệ thống **Tra cứu đơn hàng (`/orders/track/`)** theo Số điện thoại hoặc Mã đơn hàng kèm thanh tiến trình 4 bước.

### 5. Trang Quản Trị Nội Bộ Chủ Shop (`/dashboard/`)
- Thiết kế chuẩn Dark-Mode đồng bộ thương hiệu với bộ đếm KPI GSAP, biểu đồ doanh thu 7 ngày & tỷ lệ COD vs VietQR (**Chart.js**).
- Cảnh báo hàng sắp hết (`stock <= 5`), nhập nhanh tồn kho và đổi trạng thái đơn hàng chỉ bằng **1 cú click**.

### 6. Chuẩn SEO E-Commerce & Google Rich Results
- Hệ thống thẻ `<title>`, `<meta name="description">`, `<link rel="canonical">` và bộ thẻ **Open Graph** động.
- Tự động sinh **JSON-LD Product Schema** (`Offers`, `Brand`, `AggregateRating`, `Review`) và **BreadcrumbList Schema** trên trang chi tiết sản phẩm.
- Tích hợp `/sitemap.xml` và `/robots.txt` tự động lập chỉ mục toàn bộ danh mục và sản phẩm.

---

## 🛠️ Hướng Dẫn Cài Đặt & Chạy Dự Án

```bash
# 1. Tạo và kích hoạt môi trường ảo (Virtual Environment)
python -m venv venv
.\venv\Scripts\activate

# 2. Cài đặt thư viện (đã ghim phiên bản UTF-8)
pip install -r requirements.txt

# 3. Cấu hình biến môi trường (.env)
copy .env.example .env

# 4. Chạy Migration & Nạp dữ liệu mẫu an toàn (không ghi đè dữ liệu thật)
python manage.py migrate
python manage.py seed_demo

# 5. Chạy kiểm thử tự động & kiểm tra bảo mật triển khai
python manage.py test -v 2
python manage.py check --deploy

# 6. Khởi động Server tại cổng 8000
python manage.py runserver 8000
```

### 🔑 Tài Khoản Quản Trị Mẫu (`/dashboard/` & `/admin/`)
- **Username:** `admin`
- **Password:** `admin123`
- **Trang chủ:** `http://127.0.0.1:8000/`
- **Dashboard Chủ Shop:** `http://127.0.0.1:8000/dashboard/`
