# Session Handoff — Tiki Scraper

File nay giup bat dau session moi voi Claude Code ma khong mat ngu canh.
Cap nhat moi khi ket thuc 1 session lam viec.

---

## Trang thai hien tai (2026-04-07)

**Dang lam:** Giai doan 1 — Thu thap du lieu tieng Viet tu Tiki VN
**Branch:** `feature/tiki-scraper`

### Da hoan thanh:
- [x] Step 1: Test Tiki API v2 — thanh cong, khong bi anti-bot
- [x] Step 2: Scan 122 sub-categories (~585K SP kha dung)
- [x] Step 3: Build scraper (models + config + scraper + CLI)
- [x] Step 4: Test full category Smartphone (103 SP) — OK
- [x] Concurrent workers (ThreadPoolExecutor): 3 workers = 2.7 SP/s (tang 3.4x)
- [x] Resume/checkpoint: test OK (30 SP -> dung -> tiep 73 SP = 103 SP)

### Chua lam:
- [ ] Step 5: Scale — cao 100K+ SP tren may thue (47 categories, ~6-10 gio voi 3-5 workers)
- [ ] Step 6: Merge Kaggle 41K (thoi trang) + Tiki scraper ~60K (dien tu, gia dung)
- [ ] Cac giai doan tiep theo trong Project_Development_Plan.md (GD2: training, GD3: scraping realtime, GD4: chatbot)

---

## Prompt dau tien cho session moi

Copy va paste prompt nay khi bat dau session moi:

```
Doc cac file sau de nap ngu canh:

1. "scraping_data_tv/Tiki/SESSION_HANDOFF.md" — trang thai hien tai
2. "scraping_data_tv/Tiki/plan_scraping_tiki.md" — plan chi tiet Tiki scraper
3. "segment4/mo_ta_du_an/Project_Development_Plan.md" — ke hoach tong the du an

Sau do cho toi biet ban da nam duoc gi va buoc tiep theo la gi.
```

### Khi nao can doc them:
- Neu lam viec voi **search_key pipeline** (segment4): doc them `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md`
- Neu lam viec voi **scraper code**: doc them `scraping_data_tv/Tiki/tiki_scraper/scraper.py`
- Neu can **huong dan chay tren may thue**: doc `scraping_data_tv/Tiki/HUONG_DAN_CAO_DU_LIEU.md`
- Neu can **ket qua test chi tiet**: doc `scraping_data_tv/Tiki/step1/step1_notes.md`

---

## Files quan trong

| File | Muc dich |
|------|----------|
| `scraping_data_tv/Tiki/plan_scraping_tiki.md` | Plan Tiki scraper (trang thai, benchmark, cach chay) |
| `scraping_data_tv/Tiki/HUONG_DAN_CAO_DU_LIEU.md` | Huong dan cao tren may thue + resume nhieu buoi |
| `scraping_data_tv/Tiki/run_scraper.py` | CLI: `--test`, `--all`, `--category`, `--workers`, `--max` |
| `scraping_data_tv/Tiki/tiki_scraper/scraper.py` | Pipeline chinh: listing -> filter -> detail -> JSONL |
| `scraping_data_tv/Tiki/tiki_scraper/config.py` | 47 categories, rate limits, delays |
| `scraping_data_tv/Tiki/step1/step1_notes.md` | Ket qua test API + benchmark |
| `segment4/mo_ta_du_an/Project_Development_Plan.md` | Ke hoach tong the 5 giai doan (8 thang) |
| `segment4/mo_ta_du_an/DOCUMENTATION_SEARCHKEY.md` | Tai lieu search_key pipeline (tieng Anh) |
| `CLAUDE.md` | Quy tac code, workflow, debugging |

---

## Lenh chay nhanh

```bash
cd tech2ai

# Test nhanh
uv run scraping_data_tv/Tiki/run_scraper.py --test

# Cao 1 category
uv run scraping_data_tv/Tiki/run_scraper.py --category 1795 --workers 3

# Cao tat ca (tren may thue)
uv run scraping_data_tv/Tiki/run_scraper.py --all --workers 5

# Dem tong SP da cao
uv run python -c "from pathlib import Path; files=list(Path('scraping_data_tv/Tiki/Tiki_dataset_scrape').glob('*.jsonl')); total=sum(sum(1 for _ in open(f,encoding='utf-8')) for f in files); print(f'Tong: {total:,} SP tu {len(files)} files')"
```

---

*Cap nhat file nay moi khi ket thuc session lam viec.*
