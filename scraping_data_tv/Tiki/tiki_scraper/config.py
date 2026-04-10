"""Config for Tiki scraper."""

# Price range (VND)
PRICE_MIN = 50_000
PRICE_MAX = 50_000_000

# Rate limiting
LISTING_DELAY = (1.0, 2.0)  # random delay giua cac listing pages
DETAIL_DELAY = (0.3, 0.8)  # random delay giua cac detail requests (per worker)
BATCH_SLEEP_EVERY = 100  # sleep them sau moi N detail requests (toan bo workers)
BATCH_SLEEP_SECONDS = 2
SESSION_ROTATE_EVERY = 500  # tao session moi moi N requests
BLOCK_WAIT_SECONDS = 300  # doi 5 phut neu bi 429/403
DEFAULT_WORKERS = 1  # so workers mac dinh (an toan)

# Scraping
LISTING_LIMIT = 40  # san pham moi page (toi da 100, dung 40 an toan hon)
MAX_RETRIES = 3
CHECKPOINT_EVERY = 100  # save checkpoint moi N products

# Minimum features length
MIN_FEATURES_LENGTH = 50  # chars

# Sub-categories de scrape (tu 02_get_subcategories.py)
# Format: (sub_category_id, name, estimated_count)
# Chon ~50 sub-categories da dang, tong ~100K+ san pham
# Loai bo: Sach (316, 320), Thoi trang (da co 41K tu Kaggle)
SCRAPE_CATEGORIES = [
    # === DIEN TU / CONG NGHE ===
    (8129, "Linh Kien May Tinh - Phu Kien May Tinh", 12475),
    (8214, "Phu Kien Dien Thoai va May Tinh Bang", 79004),
    (28670, "Phu kien may tinh va Laptop", 4960),
    (12884, "Thiet Bi Van Phong - Ngoai Vi", 3542),
    (2663, "Thiet Bi Mang", 1447),
    (8215, "Thiet Bi Am Thanh va Phu Kien", 2508),
    (8039, "Thiet Bi Deo Thong Minh", 1038),
    (28432, "Thiet Bi Thong Minh va Linh Kien", 774),
    (8060, "Thiet Bi Luu Tru", 327),
    (8093, "PC - May Tinh Bo", 48),
    (8085, "Laptop", 21),  # it nhung gia tri cao

    # === DIEN TU - DIEN LANH ===
    (5015, "Tivi", 161),
    (3862, "May giat", 238),
    (3865, "May lanh - May dieu hoa", 309),
    (2328, "Tu lanh", 295),
    (3866, "May nuoc nong", 214),
    (3864, "May rua chen", 190),
    (26568, "Am thanh & Phu kien Tivi", 286),

    # === NHA CUA - DOI SONG ===
    (2150, "Noi that", 19569),
    (1951, "Dung cu nha bep", 14486),
    (1954, "Do dung phong an", 8185),
    (1973, "Trang tri nha cua", 9908),
    (1974, "Sua chua nha cua", 19486),
    (2015, "Den & thiet bi chieu sang", 5724),
    (2223, "Ngoai troi & san vuon", 5967),
    (1966, "Do dung va thiet bi nha tam", 6750),
    (8313, "Do dung phong ngu", 2299),

    # === DIEN GIA DUNG (phan dung) ===
    (1884, "Do dung nha bep", 7220),
    (1946, "Thiet bi gia dinh", 4772),

    # === O TO - XE MAY ===
    (24832, "Phu kien - Cham soc xe", 10120),
    (8431, "Xe dap", 342),

    # === SUC KHOE - LAM DEP ===
    (1582, "Cham soc da mat", 4318),
    (1594, "Cham soc ca nhan", 1343),
    (1592, "Cham soc co the", 1030),
    (1591, "Cham soc toc va da dau", 961),
    (1595, "Nuoc hoa", 714),
    (2306, "Dung cu lam dep", 2670),

    # === DO CHOI - ME VA BE ===
    (5250, "Do choi", 6492),
    (11601, "Do dung cho be", 2832),
    (7741, "Van phong pham", 13740),

    # === THE THAO ===
    (8168, "The thao - Da ngoai", 263),

    # === PHU KIEN THOI TRANG (bo sung cho Kaggle) ===
    (975, "Phu kien thoi trang nu", 5797),
    (27550, "Phu kien thoi trang nam", 2911),
    (8370, "Mat kinh", 3749),

    # === LAM DEP - SUC KHOE (them 2026-04-10) ===
    (1584, "Trang diem", 1223),
    (5873, "San pham thien nhien & Khac", 1275),
    (2322, "Thuc pham chuc nang", 2924),
    (2307, "May Massage & Thiet bi cham soc suc khoe", 3370),

    # === BACH HOA ===
    # === BACH HOA (them 2026-04-10) ===
    (53582, "Ruou, bia va nuoc len men", 849),
    (53562, "Sua va cac San pham tu sua", 493),
    (68576, "Ngu coc va mut", 141),
    (24024, "Do Uong Khong Con", 106),

    (4421, "Do An Vat", 1691),
    (15074, "Thuc pham Dong hop va Kho", 2789),
    (4422, "Gia Vi va Che Bien", 1554),
    (22998, "Do uong", 2741),
    (5451, "Cham soc thu cung", 2796),
]

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://tiki.vn",
}
