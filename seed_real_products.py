import os
import math
import django
from decimal import Decimal
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from shop.models import Category, Product, Review
from orders.models import Coupon, Order, OrderItem


def load_font(names, size):
    """Load a TrueType font from Windows fonts or fallback to default."""
    font_dirs = [
        r"C:\Windows\Fonts",
        "/usr/share/fonts/truetype/dejavu",
    ]
    for name in names:
        for d in font_dirs:
            full_path = os.path.join(d, name)
            if os.path.exists(full_path):
                try:
                    return ImageFont.truetype(full_path, size)
                except Exception:
                    pass
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def generate_studio_product_image(spec, media_root):
    """
    Generate an 800x800px high-resolution studio product render using Pillow (PIL).
    Includes studio radial lighting, 3D supplement tub/bag shading, metallic cap,
    and crisp brand/macro typography on the label.
    """
    W, H = 800, 800
    accent_rgb = hex_to_rgb(spec['theme_color'])
    secondary_rgb = hex_to_rgb(spec['theme_secondary'])

    # 1. Dark Studio Background with Radial Spotlight Glow
    base = Image.new('RGBA', (W, H), (16, 16, 18, 255))
    glow_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    cx, cy = W // 2, int(H * 0.46)
    for r in range(380, 20, -8):
        alpha = int(68 * (1 - (r / 380.0)) ** 1.8)
        glow_draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], alpha)
        )
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=22))
    img = Image.alpha_composite(base, glow_layer)
    draw = ImageDraw.Draw(img)

    # Studio floor reflection & podium shadow
    floor_y = 695
    draw.rectangle([0, floor_y, W, H], fill=(12, 12, 14, 255))
    draw.line([(0, floor_y), (W, floor_y)], fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 95), width=2)

    shadow_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_layer)
    s_draw.ellipse([175, 675, 625, 742], fill=(0, 0, 0, 215))
    s_draw.ellipse([220, 685, 580, 725], fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 55))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=14))
    img = Image.alpha_composite(img, shadow_layer)
    draw = ImageDraw.Draw(img)

    # Fonts
    font_tag = load_font(["segoeuib.ttf", "arialbd.ttf"], 17)
    font_brand = load_font(["impact.ttf", "arialbd.ttf", "segoeuib.ttf"], 32)
    font_title_lg = load_font(["impact.ttf", "arialbd.ttf", "segoeuib.ttf"], 52)
    font_title_md = load_font(["segoeuib.ttf", "arialbd.ttf"], 21)
    font_spec_big = load_font(["impact.ttf", "arialbd.ttf"], 29)
    font_spec_sm = load_font(["segoeuib.ttf", "arialbd.ttf"], 16)
    font_flavor = load_font(["segoeuib.ttf", "arialbd.ttf"], 17)

    # Top Studio Corner Badges (Origin + Authentic)
    origin_text = f"ORIGIN: {spec['origin'].upper()}"
    draw.rounded_rectangle(
        [36, 32, 230, 72],
        radius=8,
        fill=(28, 28, 32, 235),
        outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 190),
        width=2
    )
    draw.text((133, 52), origin_text, font=font_tag, fill=(244, 244, 244, 255), anchor="mm")

    auth_top_text = "100% AUTHENTIC"
    draw.rounded_rectangle(
        [545, 32, 764, 72],
        radius=8,
        fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 235),
        outline=(255, 255, 255, 90),
        width=1
    )
    draw.text((654, 52), auth_top_text, font=font_tag, fill=(255, 255, 255, 255), anchor="mm")

    # 2. Draw 3D Supplement Container Geometry
    container_type = spec.get('container_type', 'tub')  # 'tub', 'compact', 'bag'
    if container_type == 'compact':
        tub_left, tub_right = 190, 610
        tub_top, tub_bottom = 215, 695
        lid_left, lid_right = 225, 575
        lid_top, lid_bottom = 148, 198
        neck_top, neck_bottom = 198, 218
    elif container_type == 'bag':
        tub_left, tub_right = 155, 645
        tub_top, tub_bottom = 135, 700
        lid_left, lid_right = 175, 625
        lid_top, lid_bottom = 105, 138
        neck_top, neck_bottom = 135, 145
    else:
        tub_left, tub_right = 160, 640
        tub_top, tub_bottom = 175, 700
        lid_left, lid_right = 205, 595
        lid_top, lid_bottom = 102, 156
        neck_top, neck_bottom = 156, 180

    # Neck & Cap (for tub & compact)
    if container_type in ('tub', 'compact'):
        draw.rectangle(
            [lid_left + 16, neck_top, lid_right - 16, neck_bottom + 8],
            fill=(22, 22, 25, 255),
            outline=(62, 62, 68, 255),
            width=2
        )
        # Cap main body
        lid_color = accent_rgb if spec.get('colored_lid', True) else (32, 32, 36)
        draw.rounded_rectangle(
            [lid_left, lid_top, lid_right, lid_bottom],
            radius=12,
            fill=(lid_color[0], lid_color[1], lid_color[2], 255),
            outline=(255, 255, 255, 75),
            width=2
        )
        # Vertical grip ridges on the lid
        for gx in range(lid_left + 16, lid_right - 12, 14):
            draw.line(
                [(gx, lid_top + 6), (gx, lid_bottom - 6)],
                fill=(0, 0, 0, 85),
                width=3
            )
            draw.line(
                [(gx + 3, lid_top + 6), (gx + 3, lid_bottom - 6)],
                fill=(255, 255, 255, 45),
                width=1
            )
    else:
        # Stand-up Mass Gainer Bag top heat-seal bar
        draw.rounded_rectangle(
            [lid_left, lid_top, lid_right, lid_bottom],
            radius=6,
            fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 255),
            outline=(255, 255, 255, 80),
            width=2
        )
        draw.line([(lid_left + 20, lid_top + 16), (lid_right - 20, lid_top + 16)], fill=(18, 18, 20, 200), width=4)

    # Main Tub/Bag Body
    draw.rounded_rectangle(
        [tub_left, tub_top, tub_right, tub_bottom],
        radius=36 if container_type != 'bag' else 24,
        fill=(26, 26, 30, 255),
        outline=(75, 75, 82, 255),
        width=3
    )

    # 3D Cylindrical Specular Highlights (Left & Right vertical sheen)
    sheen_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sh_draw = ImageDraw.Draw(sheen_layer)
    sh_draw.rectangle([tub_left + 18, tub_top + 12, tub_left + 58, tub_bottom - 12], fill=(255, 255, 255, 26))
    sh_draw.rectangle([tub_right - 64, tub_top + 12, tub_right - 18, tub_bottom - 12], fill=(0, 0, 0, 90))
    sheen_layer = sheen_layer.filter(ImageFilter.GaussianBlur(radius=8))
    img = Image.alpha_composite(img, sheen_layer)
    draw = ImageDraw.Draw(img)

    # 3. Main Wrap-Around Metallic Label Band
    label_top = tub_top + 38
    label_bottom = tub_bottom - 34
    draw.rectangle(
        [tub_left + 4, label_top, tub_right - 4, label_bottom],
        fill=(18, 18, 22, 255)
    )

    # Top and bottom metallic accent stripes on the label
    draw.rectangle(
        [tub_left + 4, label_top, tub_right - 4, label_top + 12],
        fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 255)
    )
    draw.rectangle(
        [tub_left + 4, label_bottom - 12, tub_right - 4, label_bottom],
        fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 255)
    )

    # Diagonal dynamic accent slash inside label
    draw.polygon(
        [
            (tub_left + 4, label_top + 95),
            (tub_right - 4, label_top + 55),
            (tub_right - 4, label_top + 165),
            (tub_left + 4, label_top + 205),
        ],
        fill=(secondary_rgb[0], secondary_rgb[1], secondary_rgb[2], 42)
    )

    # 4. Typography on the Tub Label
    center_x = W // 2
    y_cursor = label_top + 46

    # Brand Name Pill
    brand_upper = spec['brand'].upper()
    draw.rounded_rectangle(
        [tub_left + 48, y_cursor - 22, tub_right - 48, y_cursor + 22],
        radius=6,
        fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 48),
        outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 210),
        width=2
    )
    draw.text((center_x, y_cursor), brand_upper, font=font_brand, fill=(255, 255, 255, 255), anchor="mm")

    # Product Short Title (Big Impact Font)
    y_cursor += 68
    draw.text(
        (center_x, y_cursor),
        spec['label_title'],
        font=font_title_lg,
        fill=(255, 255, 255, 255),
        anchor="mm"
    )

    # Product Subtitle (e.g., 100% WHEY ISOLATE / HYDROLYZED)
    y_cursor += 48
    draw.text(
        (center_x, y_cursor),
        spec['label_subtitle'],
        font=font_title_md,
        fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 255),
        anchor="mm"
    )

    # Central Macro Callout Box (e.g. "25G PROTEIN | 100% AUTHENTIC")
    y_cursor += 58
    box_top = y_cursor - 32
    box_bottom = y_cursor + 34
    draw.rounded_rectangle(
        [tub_left + 26, box_top, tub_right - 26, box_bottom],
        radius=10,
        fill=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 255),
        outline=(255, 255, 255, 140),
        width=2
    )
    draw.text(
        (center_x, y_cursor - 8),
        spec['macro_badge_main'],
        font=font_spec_big,
        fill=(255, 255, 255, 255),
        anchor="mm"
    )
    draw.text(
        (center_x, y_cursor + 18),
        spec['macro_badge_sub'],
        font=font_spec_sm,
        fill=(245, 245, 245, 240),
        anchor="mm"
    )

    # Secondary nutrition pills row (BCAA + Calories + Sugar)
    y_cursor += 66
    spec_line = f"{spec['bcaa_per_serving']}  •  {spec['calories']}  •  {spec['sugar']} SUGAR"
    draw.text(
        (center_x, y_cursor),
        spec_line.upper(),
        font=font_spec_sm,
        fill=(210, 210, 215, 255),
        anchor="mm"
    )

    # Flavor & Weight / Servings Footer on Label
    y_cursor = label_bottom - 52
    draw.rounded_rectangle(
        [tub_left + 20, y_cursor - 22, tub_right - 20, y_cursor + 22],
        radius=20,
        fill=(34, 34, 40, 255),
        outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2], 180),
        width=2
    )
    footer_label = f"{spec['flavor'].upper()}  •  {spec['weight'].upper()}  •  {spec['servings'].upper()}"
    draw.text(
        (center_x, y_cursor),
        footer_label,
        font=font_flavor,
        fill=(255, 255, 255, 255),
        anchor="mm"
    )

    # Save PNG to media/products/<slug>.png
    products_dir = os.path.join(media_root, 'products')
    os.makedirs(products_dir, exist_ok=True)
    rel_path = f"products/{spec['slug']}.png"
    abs_path = os.path.join(media_root, 'products', f"{spec['slug']}.png")
    img.convert('RGB').save(abs_path, format='PNG', quality=95)
    return rel_path


def run_seed():
    print("=" * 72)
    print("WHEYSTORE - SEED 10 REAL SUPPLEMENT PRODUCTS & STUDIO 800x800 IMAGES")
    print("=" * 72)

    # 1. Create the 4 standard categories & remove obsolete categories
    categories_spec = [
        ("Whey Protein Isolate", "whey-protein-isolate"),
        ("Hydrolyzed Whey", "hydrolyzed-whey"),
        ("Mass Gainer (Tăng cân)", "mass-gainer-tang-can"),
        ("Pre-Workout & Creatine", "pre-workout-creatine"),
    ]
    cat_map = {}
    valid_cat_slugs = [slug for _, slug in categories_spec]

    for name, slug in categories_spec:
        cat_obj, _ = Category.objects.update_or_create(
            slug=slug,
            defaults={'name': name}
        )
        cat_map[name] = cat_obj
        print(f"[+] Danh mục chuẩn: {cat_obj.name} (slug={cat_obj.slug})")

    # 2. Define the 10 top-selling real supplement products in Vietnam
    products_data = [
        {
            "name": "Rule 1 R1 Protein 5lbs (2.3kg)",
            "slug": "rule-1-r1-protein-5lbs",
            "brand": "Rule 1",
            "category": "Whey Protein Isolate",
            "price": Decimal("1950000"),
            "old_price": Decimal("2350000"),
            "weight": "5lbs (2.3kg)",
            "servings": "76 Servings",
            "protein_per_serving": "25g",
            "bcaa_per_serving": "6g BCAA",
            "calories": "110 kcal",
            "sugar": "0g",
            "flavor": "Chocolate Fudge",
            "origin": "USA",
            "stock": 28,
            "theme_color": "#D33F49",
            "theme_secondary": "#991b1b",
            "container_type": "tub",
            "colored_lid": True,
            "label_title": "R1 PROTEIN",
            "label_subtitle": "100% WHEY ISOLATE & HYDROLYZED",
            "macro_badge_main": "25G PROTEIN | 100% AUTHENTIC",
            "macro_badge_sub": "ZERO SUGAR • ZERO FAT • ZERO GLUTEN",
            "description": (
                "Rule 1 R1 Protein 5lbs (2.3kg) là dòng Whey Protein Isolate kết hợp Hydrolyzed siêu tinh khiết "
                "bán chạy số 1 tại thị trường Việt Nam.\n\n"
                "• 25g Whey Isolate & Hydrolyzed hấp thu cực nhanh vào cơ bắp ngay sau tập.\n"
                "• 6g BCAAs tự nhiên giúp chống dị hóa và phục hồi sợi cơ tối đa.\n"
                "• Hoàn toàn KHÔNG Đường (0g Sugar), KHÔNG Chất béo, KHÔNG Lactose — êm bụng tuyệt đối.\n"
                "• Hướng dẫn sử dụng: Pha 1 muỗng (30g) với 250-300ml nước nguội hoặc sữa tươi không đường, lắc đều 15 giây dùng ngay sau tập."
            ),
        },
        {
            "name": "Optimum Nutrition Gold Standard 100% Whey 5lbs",
            "slug": "on-gold-standard-100-whey-5lbs",
            "brand": "Optimum Nutrition",
            "category": "Whey Protein Isolate",
            "price": Decimal("2150000"),
            "old_price": Decimal("2440000"),
            "weight": "5lbs (2.27kg)",
            "servings": "74 Servings",
            "protein_per_serving": "24g",
            "bcaa_per_serving": "5.5g BCAA",
            "calories": "120 kcal",
            "sugar": "1g",
            "flavor": "Double Rich Chocolate",
            "origin": "USA",
            "stock": 35,
            "theme_color": "#d97706",
            "theme_secondary": "#D33F49",
            "container_type": "tub",
            "colored_lid": False,
            "label_title": "GOLD STANDARD",
            "label_subtitle": "100% WHEY PROTEIN ISOLATE BLEND",
            "macro_badge_main": "24G PROTEIN | 100% AUTHENTIC",
            "macro_badge_sub": "5.5G BCAA • 4G GLUTAMINE • WORLD #1 WHEY",
            "description": (
                "Optimum Nutrition Gold Standard 100% Whey 5lbs là huyền thoại Whey Protein bán chạy nhất thế giới suốt hơn 20 năm qua.\n\n"
                "• Cung cấp 24g Protein chất lượng cao (Whey Protein Isolate là thành phần chính).\n"
                "• 5.5g BCAAs tự nhiên cùng 4g Glutamine và Glutamic Acid mỗi lần dùng.\n"
                "• Công nghệ Instantized giúp bột tan 100% chỉ sau vài lần lắc, vị Double Rich Chocolate thơm ngon chuẩn Mỹ.\n"
                "• Đạt chứng nhận Informed-Choice không chất cấm thể thao."
            ),
        },
        {
            "name": "Dymatize ISO 100 Hydrolyzed 5lbs (2.27kg)",
            "slug": "dymatize-iso-100-hydrolyzed-5lbs",
            "brand": "Dymatize",
            "category": "Hydrolyzed Whey",
            "price": Decimal("2650000"),
            "old_price": Decimal("2990000"),
            "weight": "5lbs (2.27kg)",
            "servings": "71 Servings",
            "protein_per_serving": "25g",
            "bcaa_per_serving": "5.5g BCAA",
            "calories": "110 kcal",
            "sugar": "0g",
            "flavor": "Gourmet Vanilla",
            "origin": "USA",
            "stock": 18,
            "theme_color": "#0284c7",
            "theme_secondary": "#0369a1",
            "container_type": "tub",
            "colored_lid": True,
            "label_title": "ISO 100",
            "label_subtitle": "100% HYDROLYZED WHEY ISOLATE",
            "macro_badge_main": "25G PROTEIN | 100% AUTHENTIC",
            "macro_badge_sub": "5.5G BCAA • 2.7G LEUCINE • ULTRA FAST DIGESTING",
            "description": (
                "Dymatize ISO 100 Hydrolyzed 5lbs (2.27kg) là đỉnh cao của dòng Whey thủy phân (Hydrolyzed Whey Protein Isolate) "
                "dành cho vận động viên và Gymer chuyên nghiệp.\n\n"
                "• 25g Protein thủy phân siêu phân tử, thẩm thấu vào cơ bắp chỉ trong 15-20 phút.\n"
                "• 5.5g BCAAs trong đó chứa tới 2.7g L-Leucine kích hoạt tổng hợp Protein cơ bắp mạnh mẽ.\n"
                "• Loại bỏ hoàn toàn Lactose, Gluten và Đường (0g Sugar), chỉ 110 kcal mỗi muỗng."
            ),
        },
        {
            "name": "BPI Sports ISO HD 100% Pure Isolate 5lbs",
            "slug": "bpi-sports-iso-hd-5lbs",
            "brand": "BPI Sports",
            "category": "Whey Protein Isolate",
            "price": Decimal("1540000"),
            "old_price": Decimal("1850000"),
            "weight": "5lbs (2.27kg)",
            "servings": "69 Servings",
            "protein_per_serving": "25g",
            "bcaa_per_serving": "5g BCAA",
            "calories": "120 kcal",
            "sugar": "0g",
            "flavor": "Cookies & Cream",
            "origin": "USA",
            "stock": 4,  # Low stock (<= 5) for Dashboard alert demonstration
            "theme_color": "#0ea5e9",
            "theme_secondary": "#1e3a8a",
            "container_type": "tub",
            "colored_lid": True,
            "label_title": "ISO HD",
            "label_subtitle": "100% PURE WHEY PROTEIN ISOLATE",
            "macro_badge_main": "25G PROTEIN | 100% AUTHENTIC",
            "macro_badge_sub": "5G BCAA • 0G SUGAR • ULTRA LEAN MUSCLE",
            "description": (
                "BPI Sports ISO HD 100% Pure Isolate 5lbs mang lại nguồn đạm Isolate tinh khiết 25g mỗi muỗng với mức giá cực kỳ kinh tế.\n\n"
                "• 100% Whey Protein Isolate tinh khiết, hỗ trợ tăng cơ nạc và siết cơ giảm mỡ hiệu quả.\n"
                "• 5g BCAAs giúp giảm đau nhức cơ bắp DOMS sau các buổi tập nặng.\n"
                "• Hương vị Cookies & Cream thơm béo nhưng hoàn toàn 0g Sugar."
            ),
        },
        {
            "name": "Applied Nutrition ISO-XP 100% Whey Isolate 2kg",
            "slug": "applied-nutrition-iso-xp-2kg",
            "brand": "Applied Nutrition",
            "category": "Whey Protein Isolate",
            "price": Decimal("1850000"),
            "old_price": Decimal("2100000"),
            "weight": "2kg (4.4lbs)",
            "servings": "80 Servings",
            "protein_per_serving": "23.4g",
            "bcaa_per_serving": "5.3g BCAA",
            "calories": "94 kcal",
            "sugar": "0g",
            "flavor": "Cafe Latte",
            "origin": "UK",
            "stock": 22,
            "theme_color": "#2563eb",
            "theme_secondary": "#38bdf8",
            "container_type": "tub",
            "colored_lid": True,
            "label_title": "ISO-XP",
            "label_subtitle": "100% WHEY PROTEIN ISOLATE • GRASS FED",
            "macro_badge_main": "23.4G PROTEIN | 100% AUTHENTIC",
            "macro_badge_sub": "80 SERVINGS • 94 KCAL • 0G SUGAR • MADE IN UK",
            "description": (
                "Applied Nutrition ISO-XP 2kg nhập khẩu chính hãng từ Vương Quốc Anh (UK), sản xuất từ nguồn sữa bò ăn cỏ tự nhiên (Grass-Fed Cows).\n\n"
                "• Hàm lượng Protein đạt tới gần 90% (23.4g Protein trên mỗi muỗng 25g).\n"
                "• Tiết kiệm vượt trội với 80 lần dùng (80 Servings), chỉ 94 kcal và 0g đường.\n"
                "• Hương vị Cafe Latte thơm lừng như cà phê pha máy, cực kỳ dễ uống mỗi sáng."
            ),
        },
        {
            "name": "Mutant ISO Surge 5lbs (2.27kg)",
            "slug": "mutant-iso-surge-5lbs",
            "brand": "Mutant",
            "category": "Hydrolyzed Whey",
            "price": Decimal("1950000"),
            "old_price": Decimal("2250000"),
            "weight": "5lbs (2.27kg)",
            "servings": "76 Servings",
            "protein_per_serving": "25g",
            "bcaa_per_serving": "5.5g BCAA",
            "calories": "120 kcal",
            "sugar": "1g",
            "flavor": "Triple Chocolate",
            "origin": "USA",
            "stock": 5,  # Low stock (<= 5) for Dashboard alert demonstration
            "theme_color": "#eab308",
            "theme_secondary": "#b91c1c",
            "container_type": "tub",
            "colored_lid": False,
            "label_title": "ISO SURGE",
            "label_subtitle": "WHEY ISOLATE & HYDROLYZED PROTEIN",
            "macro_badge_main": "25G PROTEIN | 100% AUTHENTIC",
            "macro_badge_sub": "5.5G BCAA • GOURMET TRIPLE CHOCOLATE",
            "description": (
                "Mutant ISO Surge 5lbs kết hợp hai nguồn đạm cao cấp nhất: Whey Protein Isolate và Whey Protein Hydrolyzed.\n\n"
                "• 25g Protein + 5.5g BCAAs tốc độ hấp thu cực nhanh, nuôi dưỡng cơ bắp tức thì.\n"
                "• Nổi tiếng toàn cầu nhờ bảng vị Gourmet thơm ngon bậc nhất, đặc biệt là vị Triple Chocolate đậm đà.\n"
                "• Bổ sung Enzyme tiêu hóa Lactase và Protease giúp hấp thu tối đa 100% dưỡng chất."
            ),
        },
        {
            "name": "BioTechUSA Hydro Whey Zero 1.8kg",
            "slug": "biotechusa-hydro-whey-zero-1-8kg",
            "brand": "BioTechUSA",
            "category": "Hydrolyzed Whey",
            "price": Decimal("1990000"),
            "old_price": Decimal("2300000"),
            "weight": "1.8kg (4lbs)",
            "servings": "82 Servings",
            "protein_per_serving": "18g",
            "bcaa_per_serving": "4g BCAA",
            "calories": "80 kcal",
            "sugar": "0g",
            "flavor": "Strawberry",
            "origin": "USA",
            "stock": 19,
            "theme_color": "#06b6d4",
            "theme_secondary": "#0284c7",
            "container_type": "tub",
            "colored_lid": True,
            "label_title": "HYDRO WHEY ZERO",
            "label_subtitle": "HYDROLYZED WHEY PROTEIN ISOLATE",
            "macro_badge_main": "82 SERVINGS | 100% AUTHENTIC",
            "macro_badge_sub": "ZERO LACTOSE • ZERO GLUTEN • ZERO SUGAR",
            "description": (
                "BioTechUSA Hydro Whey Zero 1.8kg có hàm lượng đạm thủy phân (Hydrolyzed) cực cao cùng 82 lần dùng siêu tiết kiệm.\n\n"
                "• Hoàn toàn không chứa đường (0g Sugar), không Lactose, không Gluten và không dầu cọ.\n"
                "• Mỗi muỗng 22g chỉ chứa 80 kcal với 18g Protein siêu sạch, lý tưởng cho giai đoạn Cutting siết cơ nét.\n"
                "• Bổ sung thêm L-Arginine giúp tăng cường lưu thông máu và bơm cơ (Pump)."
            ),
        },
        {
            "name": "Labrada Muscle Mass Gainer 12lbs (5.4kg)",
            "slug": "labrada-muscle-mass-gainer-12lbs",
            "brand": "Labrada",
            "category": "Mass Gainer (Tăng cân)",
            "price": Decimal("2190000"),
            "old_price": Decimal("2550000"),
            "weight": "12lbs (5.4kg)",
            "servings": "16 Servings",
            "protein_per_serving": "52g",
            "bcaa_per_serving": "17g BCAA",
            "calories": "1265 kcal",
            "sugar": "15g",
            "flavor": "Chocolate Ice Cream",
            "origin": "USA",
            "stock": 16,
            "theme_color": "#D33F49",
            "theme_secondary": "#7f1d1d",
            "container_type": "bag",
            "colored_lid": True,
            "label_title": "MUSCLE MASS",
            "label_subtitle": "HIGH CALORIE WEIGHT GAINER • 12LBS",
            "macro_badge_main": "52G PROTEIN | 1265 KCAL",
            "macro_badge_sub": "17G BCAA • CREATINE MONOHYDRATE • 100% AUTHENTIC",
            "description": (
                "Labrada Muscle Mass Gainer 12lbs (5.4kg) là dòng sữa tăng cân tăng cơ huyền thoại dành cho người gầy khó hấp thu (Hardgainers).\n\n"
                "• Cung cấp 1265 Calories và tới 52g Protein chất lượng cao trong mỗi khẩu phần chuẩn.\n"
                "• Chứa 17g BCAAs cùng Creatine Monohydrate giúp tăng sức mạnh và kích thước cơ bắp nhanh chóng.\n"
                "• Không chứa Dextrose, Sucrose hay Corn Syrup Solids — hỗ trợ tăng cân nạc hạn chế tích mỡ thừa."
            ),
        },
        {
            "name": "Cellucor C4 Original Pre-Workout (60 Servings)",
            "slug": "cellucor-c4-original-pre-workout-60-servings",
            "brand": "Cellucor",
            "category": "Pre-Workout & Creatine",
            "price": Decimal("950000"),
            "old_price": Decimal("1150000"),
            "weight": "390g",
            "servings": "60 Servings",
            "protein_per_serving": "0g",
            "bcaa_per_serving": "1.6g Beta-Alanine",
            "calories": "5 kcal",
            "sugar": "0g",
            "flavor": "Icy Blue Razz",
            "origin": "USA",
            "stock": 30,
            "theme_color": "#eab308",
            "theme_secondary": "#0284c7",
            "container_type": "compact",
            "colored_lid": True,
            "label_title": "C4 ORIGINAL",
            "label_subtitle": "EXPLOSIVE ENERGY PRE-WORKOUT",
            "macro_badge_main": "60 SERVINGS | 100% AUTHENTIC",
            "macro_badge_sub": "1.6G CARNOSYN BETA-ALANINE • 150MG CAFFEINE",
            "description": (
                "Cellucor C4 Original Pre-Workout (bản lớn 60 Servings) là dòng tăng sức mạnh và sự tỉnh táo trước tập bán chạy số 1 tại Mỹ.\n\n"
                "• 1.6g CarnoSyn Beta-Alanine tăng sức bền cơ bắp, đẩy lùi cảm giác mỏi cơ.\n"
                "• 1g Creatine Nitrate (NO3-T) kết hợp 1g Arginine AKG giúp bơm máu căng phồng cơ bắp (Muscle Pump).\n"
                "• 150mg Caffeine khan cùng N-Acetyl-L-Tyrosine giúp tập trung cao độ, bùng nổ mức tạ kỷ lục."
            ),
        },
        {
            "name": "OstroVit Creatine Monohydrate 500g",
            "slug": "ostrovit-creatine-monohydrate-500g",
            "brand": "OstroVit",
            "category": "Pre-Workout & Creatine",
            "price": Decimal("640000"),
            "old_price": Decimal("850000"),
            "weight": "500g",
            "servings": "166 Servings",
            "protein_per_serving": "0g",
            "bcaa_per_serving": "3g Creatine",
            "calories": "0 kcal",
            "sugar": "0g",
            "flavor": "Unflavored",
            "origin": "Poland",
            "stock": 42,
            "theme_color": "#10b981",
            "theme_secondary": "#047857",
            "container_type": "compact",
            "colored_lid": True,
            "label_title": "CREATINE",
            "label_subtitle": "SUPREME PURE MONOHYDRATE 500G",
            "macro_badge_main": "3G CREATINE | 166 SERVINGS",
            "macro_badge_sub": "MICRONIZED 200 MESH • ZERO CALORIES • POLAND",
            "description": (
                "OstroVit Creatine Monohydrate 500g (166 lần dùng) nhập khẩu Ba Lan (Poland) với độ mịn Micronized 200 Mesh siêu tinh khiết.\n\n"
                "• Tăng tái tạo năng lượng ATP tức thời, giúp nâng mức tạ nặng hơn và tăng số reps trong mỗi hiệp tập.\n"
                "• Giữ nước nội bào cơ bắp giúp cơ dày, căng tròn và phục hồi nhanh hơn.\n"
                "• Vị Unflavored (Không mùi vị) dễ dàng pha chung với Whey Protein hoặc Pre-Workout mỗi ngày."
            ),
        },
    ]

    valid_product_slugs = [p['slug'] for p in products_data]
    created_products = []

    for idx, spec in enumerate(products_data, start=1):
        img_rel_path = generate_studio_product_image(spec, settings.MEDIA_ROOT)
        cat_obj = cat_map[spec['category']]

        prod, _ = Product.objects.update_or_create(
            slug=spec['slug'],
            defaults={
                'category': cat_obj,
                'name': spec['name'],
                'brand': spec['brand'],
                'image': img_rel_path,
                'description': spec['description'],
                'price': spec['price'],
                'old_price': spec['old_price'],
                'weight': spec['weight'],
                'servings': spec['servings'],
                'protein_per_serving': spec['protein_per_serving'],
                'bcaa_per_serving': spec['bcaa_per_serving'],
                'calories': spec['calories'],
                'sugar': spec['sugar'],
                'flavor': spec['flavor'],
                'origin': spec['origin'],
                'free_gift': 'Tặng Bình Lắc Shaker + Freeship',
                'stock': spec['stock'],
                'available': True,
            }
        )
        created_products.append(prod)
        print(
            f"[{idx:02d}/10] {prod.name} | Brand: {prod.brand} | "
            f"Giá: {int(prod.price):,}đ (Gốc: {int(prod.old_price):,}đ, -{prod.discount_percent}%) | "
            f"Ảnh: media/{img_rel_path}"
        )

    # 3. Clean up obsolete old sample products & categories safely
    # Reassign any old OrderItems to our new flagship products first so Order history stays intact
    r1_prod = created_products[0]
    for item in OrderItem.objects.exclude(product__slug__in=valid_product_slugs):
        item.product = r1_prod
        item.price = r1_prod.price
        item.save()

    deleted_prods, _ = Product.objects.exclude(slug__in=valid_product_slugs).delete()
    deleted_cats, _ = Category.objects.exclude(slug__in=valid_cat_slugs).delete()
    print(f"[*] Đã dọn dẹp sản phẩm/danh mục mẫu cũ bị trùng (Xóa {deleted_prods} bản ghi cũ).")

    # 4. Seed authentic 5-star customer reviews for every product
    sample_reviews_map = {
        "rule-1-r1-protein-5lbs": [
            ("Nguyễn Hoàng Nam (PT Gym Quận 1)", 5, "Rule 1 vị Chocolate Fudge cực kỳ dễ uống, lắc 5 giây tan sạch không vón cục. Uống 2 tháng lên cơ nạc rõ rệt mà không hề bị nổi mụn hay đầy bụng!"),
            ("Trần Minh Quân", 5, "Hàng chính hãng có tem cào xác thực đầy đủ, shop tặng kèm bình lắc Shaker chống rò nước rất xịn. Sẽ ủng hộ WheyStore dài dài."),
        ],
        "on-gold-standard-100-whey-5lbs": [
            ("Lê Tuấn Kiệt", 5, "Đúng chuẩn huyền thoại ON Gold Standard, vị Double Rich Chocolate thơm dịu, không bị ngọt gắt. Phục hồi cơ sau ngày tập chân cực tốt."),
            ("Phạm Quốc Bảo", 5, "Mua tại WheyStore yên tâm tuyệt đối về nguồn gốc USA, giao hàng nhanh trong 2 tiếng."),
        ],
        "dymatize-iso-100-hydrolyzed-5lbs": [
            ("Vũ Đức Anh (Men's Physique)", 5, "Đang trong giai đoạn siết cơ chuẩn bị thi đấu nên chỉ tin dùng ISO 100. Vị Gourmet Vanilla thơm như kem, uống vào nhẹ bụng hấp thu ngay lập tức!"),
        ],
        "bpi-sports-iso-hd-5lbs": [
            ("Đặng Gia Huy", 5, "Giá quá hời cho một hũ 100% Isolate 5lbs của Mỹ! Vị Cookies & Cream rất cuốn, 25g Protein mà 0g đường."),
        ],
        "applied-nutrition-iso-xp-2kg": [
            ("Hoàng Thảo Vy", 5, "Mình là nữ tập Gym rất mê vị Cafe Latte của ISO-XP. Pha với đá uống mỗi sáng vừa tỉnh táo vừa đủ 23.4g đạm sạch mà chỉ có 94 kcal!"),
        ],
        "mutant-iso-surge-5lbs": [
            ("Bùi Trọng Nghĩa", 5, "Ai hảo socola chắc chắn phải thử vị Triple Chocolate của Mutant ISO Surge, ngon đỉnh nóc! Vừa Isolate vừa Hydrolyzed giá lại quá tốt."),
        ],
        "biotechusa-hydro-whey-zero-1-8kg": [
            ("Ngô Thanh Tùng", 5, "1 hũ dùng được tận 82 lần, tính ra mỗi lần dùng cực rẻ cho dòng Hydrolyzed không đường không Lactose. Vị dâu tây rất thanh mát."),
        ],
        "labrada-muscle-mass-gainer-12lbs": [
            ("Phan Văn Khải", 5, "Mình tạng người gầy kinh niên 54kg, uống hết 1 bịch Labrada Muscle Mass kết hợp tập 4 buổi/tuần đã lên được 59kg cơ bắp săn chắc!"),
        ],
        "cellucor-c4-original-pre-workout-60-servings": [
            ("Đinh Công Thành", 5, "Làm 1 muỗng C4 vị Icy Blue Razz trước tập 20 phút vào phòng tạ tỉnh như sáo, bơm cơ căng đét, đẩy ngực vượt PR luôn!"),
        ],
        "ostrovit-creatine-monohydrate-500g": [
            ("Lương Thế Vinh", 5, "Hũ 500g dùng được hơn 5 tháng, bột mịn pha chung với Whey rất tiện. Tập khỏe hơn hẳn sau 2 tuần dùng đều đặn."),
        ],
    }

    for prod in created_products:
        Review.objects.filter(product=prod).delete()
        for user_name, rating, comment in sample_reviews_map.get(prod.slug, []):
            Review.objects.create(
                product=prod,
                user_name=user_name,
                rating=rating,
                comment=comment,
                verified_purchase=True,
            )

    # 5. Ensure Coupons exist
    Coupon.objects.update_or_create(
        code='GYMBRO10',
        defaults={'discount_percent': 10, 'active': True}
    )
    Coupon.objects.update_or_create(
        code='WHEYVIP20',
        defaults={'discount_percent': 20, 'active': True}
    )

    print("=" * 72)
    print(f"HOÀN TẤT! Tổng danh mục: {Category.objects.count()} | Tổng sản phẩm: {Product.objects.count()}")
    print("=" * 72)


if __name__ == '__main__':
    run_seed()
