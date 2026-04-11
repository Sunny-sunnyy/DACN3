# WinMart Categories Report

**Cap nhat:** 2026-04-11
**Trang thai:** CHUA CAO — API da xac nhan, san sang chay scraper
**Tong categories:** 18 (parent-level)
**Tong san pham:** 3,238 SP (storeCode=1535)
**pageSize:** 100
**Category map:** Tat ca -> Bach Hoa
**API:** api-crownx.winmart.vn/it/api/web/v3/item/category
**LUU Y:** API co the bi timeout tu server ngoai VN — da test OK tu WSL nay

---

## Categories (sap xep theo so SP giam dan)

| # | Slug | Name | So SP | Pages | Xong |
|---:|---|---|---:|---:|:---:|
| 1 | `cham-soc-ca-nhan--c11` | Cham soc ca nhan | 514 | 6 | [ ] |
| 2 | `banh-keo--c07` | Banh keo | 467 | 5 | [ ] |
| 3 | `do-uong-giai-khat--c09` | Do uong giai khat | 313 | 4 | [ ] |
| 4 | `sua-cac-loai--c08` | Sua cac loai | 301 | 4 | [ ] |
| 5 | `gia-vi--c35` | Gia vi | 269 | 3 | [ ] |
| 6 | `do-dung-gia-dinh--c25` | Do dung gia dinh | 217 | 3 | [ ] |
| 7 | `mi-thuc-pham-an-lien--c34` | Mi, thuc pham an lien | 215 | 3 | [ ] |
| 8 | `thuc-pham-kho--c06` | Thuc pham kho | 160 | 2 | [ ] |
| 9 | `thuc-pham-che-bien--c04` | Thuc pham che bien | 152 | 2 | [ ] |
| 10 | `rau-cu-trai-cay--c02` | Rau cu trai cay | 147 | 2 | [ ] |
| 11 | `hoa-pham-tay-rua--c10` | Hoa pham tay rua | 119 | 2 | [ ] |
| 12 | `thuc-pham-dong-lanh--c05` | Thuc pham dong lanh | 110 | 2 | [ ] |
| 13 | `van-phong-pham-do-choi--c27` | Van phong pham, do choi | 75 | 1 | [ ] |
| 14 | `thit-hai-san-tuoi--c03` | Thit, hai san tuoi | 54 | 1 | [ ] |
| 15 | `cham-soc-be--c12` | Cham soc be | 48 | 1 | [ ] |
| 16 | `do-uong-co-con--c31` | Do uong co con | 42 | 1 | [ ] |
| 17 | `trung-dau-hu--c33` | Trung, dau hu | 23 | 1 | [ ] |
| 18 | `dien-gia-dung--c26` | Dien gia dung | 12 | 1 | [ ] |

**Tong:** 3,238 SP

---

## Phan nhom theo loai

### Thuc pham (10 categories, 1,862 SP)

| # | Slug | Name | So SP |
|---:|---|---|---:|
| 1 | `banh-keo--c07` | Banh keo | 467 |
| 2 | `sua-cac-loai--c08` | Sua cac loai | 301 |
| 3 | `gia-vi--c35` | Gia vi | 269 |
| 4 | `mi-thuc-pham-an-lien--c34` | Mi, thuc pham an lien | 215 |
| 5 | `thuc-pham-kho--c06` | Thuc pham kho | 160 |
| 6 | `thuc-pham-che-bien--c04` | Thuc pham che bien | 152 |
| 7 | `rau-cu-trai-cay--c02` | Rau cu trai cay | 147 |
| 8 | `thuc-pham-dong-lanh--c05` | Thuc pham dong lanh | 110 |
| 9 | `thit-hai-san-tuoi--c03` | Thit, hai san tuoi | 54 |
| 10 | `trung-dau-hu--c33` | Trung, dau hu | 23 |

### Do uong (2 categories, 355 SP)

| # | Slug | Name | So SP |
|---:|---|---|---:|
| 1 | `do-uong-giai-khat--c09` | Do uong giai khat | 313 |
| 2 | `do-uong-co-con--c31` | Do uong co con | 42 |

### Cham soc ca nhan & Gia dinh (4 categories, 898 SP)

| # | Slug | Name | So SP |
|---:|---|---|---:|
| 1 | `cham-soc-ca-nhan--c11` | Cham soc ca nhan | 514 |
| 2 | `do-dung-gia-dinh--c25` | Do dung gia dinh | 217 |
| 3 | `hoa-pham-tay-rua--c10` | Hoa pham tay rua | 119 |
| 4 | `cham-soc-be--c12` | Cham soc be | 48 |

### Khac (2 categories, 87 SP)

| # | Slug | Name | So SP |
|---:|---|---|---:|
| 1 | `van-phong-pham-do-choi--c27` | Van phong pham, do choi | 75 |
| 2 | `dien-gia-dung--c26` | Dien gia dung | 12 |

---

## Tong ket

| Nhom | Categories | So SP | Trang thai |
|---|---:|---:|:---:|
| Thuc pham | 10 | 1,862 | CHUA CAO |
| Do uong | 2 | 355 | CHUA CAO |
| Cham soc & Gia dinh | 4 | 898 | CHUA CAO |
| Khac | 2 | 87 | CHUA CAO |
| **TONG** | **18** | **3,238** | **CHUA CAO** |

### Ghi chu

- So SP thuc te co the thay doi tuy storeCode (hien dung 1535)
- API co ca `price` (gia goc) va `salePrice` (gia KM) — dung `price` cho dataset
- Data quality: RAT TOT — co brand, 5 cap category hierarchy, description day du
- WinMart dong gop ~3.2K SP cho category "Bach Hoa" trong price prediction dataset

---

*Tao thu cong. Cap nhat: 2026-04-11. San sang chay scraper.*
