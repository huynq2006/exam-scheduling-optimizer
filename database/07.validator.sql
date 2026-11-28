-- =====================================================================
-- 07_validate.sql  -  Validator độc lập cho lịch thi (MySQL 8.0+)
-- Kiểm tra dữ liệu ĐÃ GHI trong lich_thi / dang_ky_thi, không phụ thuộc solver.
-- Chỉ kiểm tra MỘT phương án (phuong_an): mặc định là phương án 'DA_CONG_BO' mới nhất,
-- nếu chưa có thì phương án mới nhất. Muốn kiểm tra phương án khác: xem view vv_pa_xet bên dưới.
-- Yêu cầu: đã chạy 01_schema.sql và có bảng dang_ky_mon (đầu vào: SV đăng ký môn nào).
-- Cách dùng:  1) chạy cả file  2) xem bảng tóm tắt (mục 3)  3) dòng LOI -> SELECT * FROM vv_<tên>
-- =====================================================================
USE quan_ly_thi;

CREATE TABLE IF NOT EXISTS dang_ky_mon (
    ma_sv  VARCHAR(12) NOT NULL,
    ma_mon VARCHAR(10) NOT NULL,
    PRIMARY KEY (ma_sv, ma_mon),
    CONSTRAINT fk_dkm_sv  FOREIGN KEY (ma_sv)  REFERENCES sinh_vien(ma_sv) ON DELETE CASCADE,
    CONSTRAINT fk_dkm_mon FOREIGN KEY (ma_mon) REFERENCES mon_thi(ma_mon) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Tham số giới hạn tổng số cán bộ coi thi trong một khung (C7) - chỉnh theo quy chế
SET @sv_moi_cbct = 30;        -- số sinh viên / 1 cán bộ coi thi
SET @cbct_toi_da = 1000000;   -- S_t: số cán bộ tối đa mỗi khung giờ

-- ---------------------------------------------------------------------
-- 0. Phạm vi kiểm tra: một phương án (ma_pa)
--    Đổi sang phương án khác bằng cách thay thân view, ví dụ:  SELECT 7 AS ma_pa
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vv_pa_xet AS
SELECT COALESCE((SELECT MAX(ma_pa) FROM phuong_an WHERE trang_thai = 'DA_CONG_BO'),
                (SELECT MAX(ma_pa) FROM phuong_an)) AS ma_pa;

CREATE OR REPLACE VIEW vv_lich AS
SELECT * FROM lich_thi WHERE ma_pa = (SELECT ma_pa FROM vv_pa_xet);

CREATE OR REPLACE VIEW vv_dk AS
SELECT d.* FROM dang_ky_thi d JOIN vv_lich l ON l.ma_lich = d.ma_lich;

-- ---------------------------------------------------------------------
-- 1. View nền: sĩ số từng buổi thi
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vv_si_so AS
SELECT l.ma_lich, l.ma_mon, l.ma_phong, l.ma_khung, COUNT(d.ma_sv) AS si_so
FROM vv_lich l
LEFT JOIN vv_dk d ON d.ma_lich = l.ma_lich
GROUP BY l.ma_lich, l.ma_mon, l.ma_phong, l.ma_khung;

-- ---------------------------------------------------------------------
-- 2. View vi phạm (mỗi view rỗng = đạt)
-- ---------------------------------------------------------------------
-- C1: SV đăng ký môn nhưng chưa được xếp buổi thi nào của môn đó
CREATE OR REPLACE VIEW vv_c1_chua_xep AS
SELECT m.ma_sv, m.ma_mon
FROM dang_ky_mon m
WHERE NOT EXISTS (SELECT 1 FROM vv_dk d JOIN vv_lich l ON l.ma_lich = d.ma_lich
                  WHERE d.ma_sv = m.ma_sv AND l.ma_mon = m.ma_mon);

-- C1b: SV được xếp thi môn mà không đăng ký
CREATE OR REPLACE VIEW vv_c1b_thi_ngoai_dang_ky AS
SELECT d.ma_sv, l.ma_mon, d.ma_lich
FROM vv_dk d JOIN vv_lich l ON l.ma_lich = d.ma_lich
LEFT JOIN dang_ky_mon m ON m.ma_sv = d.ma_sv AND m.ma_mon = l.ma_mon
WHERE m.ma_sv IS NULL;

-- C1c: SV thi cùng một môn ở nhiều buổi
CREATE OR REPLACE VIEW vv_c1c_thi_trung_mon AS
SELECT d.ma_sv, l.ma_mon, COUNT(*) AS so_buoi
FROM vv_dk d JOIN vv_lich l ON l.ma_lich = d.ma_lich
GROUP BY d.ma_sv, l.ma_mon HAVING COUNT(*) > 1;

-- C1d: buổi thi không có sinh viên nào
CREATE OR REPLACE VIEW vv_c1d_buoi_rong AS
SELECT * FROM vv_si_so WHERE si_so = 0;

-- C2: dùng phòng đang bảo trì
CREATE OR REPLACE VIEW vv_c2_phong_bao_tri AS
SELECT l.ma_lich, l.ma_phong, p.tinh_trang
FROM vv_lich l JOIN phong_may p ON p.ma_phong = l.ma_phong
WHERE p.tinh_trang <> 'Working';

-- C2b: hai buổi cùng phòng + cùng khung (schema đã có UNIQUE nên thường rỗng)
CREATE OR REPLACE VIEW vv_c2b_trung_phong_khung AS
SELECT ma_phong, ma_khung, COUNT(*) AS so_buoi
FROM vv_lich GROUP BY ma_phong, ma_khung HAVING COUNT(*) > 1;

-- C3: sĩ số vượt sức chứa
CREATE OR REPLACE VIEW vv_c3_vuot_suc_chua AS
SELECT s.ma_lich, s.ma_phong, s.si_so, p.suc_chua
FROM vv_si_so s JOIN phong_may p ON p.ma_phong = s.ma_phong
WHERE s.si_so > p.suc_chua;

-- C3b: số máy ngoài khoảng 1..sức chứa
CREATE OR REPLACE VIEW vv_c3b_so_may_sai AS
SELECT d.ma_sv, d.ma_lich, d.so_may, p.suc_chua
FROM vv_dk d
JOIN vv_lich l ON l.ma_lich = d.ma_lich
JOIN phong_may p ON p.ma_phong = l.ma_phong
WHERE d.so_may < 1 OR d.so_may > p.suc_chua;

-- C3c: phòng thiếu phần mềm mà môn thi yêu cầu
CREATE OR REPLACE VIEW vv_c3c_thieu_phan_mem AS
SELECT l.ma_lich, l.ma_mon, l.ma_phong, pm.ten_pm
FROM vv_lich l
JOIN mon_thi_phan_mem mp ON mp.ma_mon = l.ma_mon
JOIN phan_mem pm ON pm.ma_pm = mp.ma_pm
LEFT JOIN phong_may_phan_mem pp ON pp.ma_phong = l.ma_phong AND pp.ma_pm = mp.ma_pm
WHERE pp.ma_pm IS NULL;

-- C4: sinh viên thi hai buổi cùng khung giờ (ràng buộc schema không ép được)
CREATE OR REPLACE VIEW vv_c4_sv_trung_khung AS
SELECT d.ma_sv, l.ma_khung, COUNT(*) AS so_buoi, GROUP_CONCAT(l.ma_mon) AS cac_mon
FROM vv_dk d JOIN vv_lich l ON l.ma_lich = d.ma_lich
GROUP BY d.ma_sv, l.ma_khung HAVING COUNT(*) > 1;

-- C5: mỗi buổi thi có 1-2 giám thị
CREATE OR REPLACE VIEW vv_c5_so_giam_thi AS
SELECT l.ma_lich, COUNT(pc.ma_gt) AS so_giam_thi
FROM vv_lich l
LEFT JOIN phan_cong_giam_thi pc ON pc.ma_lich = l.ma_lich
                               AND pc.ma_pa = l.ma_pa
GROUP BY l.ma_lich
HAVING COUNT(pc.ma_gt) < 1 OR COUNT(pc.ma_gt) > 2;

-- C6: giám thị được phân công ít nhất hai ca khác nhau trong mỗi ngày đã làm việc
CREATE OR REPLACE VIEW vv_c6_giam_thi_du_ca AS
SELECT pc.ma_gt, k.ngay_thi, COUNT(DISTINCT k.ca_thi) AS so_ca
FROM phan_cong_giam_thi pc
JOIN vv_lich l ON l.ma_lich = pc.ma_lich
              AND l.ma_pa = pc.ma_pa
JOIN khung_gio k ON k.ma_khung = pc.ma_khung
GROUP BY pc.ma_gt, k.ngay_thi
HAVING COUNT(DISTINCT k.ca_thi) < 2;

-- ---------------------------------------------------------------------
-- 3. BẢNG TÓM TẮT: mỗi dòng một kiểm tra
-- ---------------------------------------------------------------------
SELECT 'C1  SV chua duoc xep thi'            AS kiem_tra, COUNT(*) AS so_vi_pham,
       IF(COUNT(*) = 0, 'OK', 'LOI') AS ket_qua FROM vv_c1_chua_xep
UNION ALL SELECT 'C1b SV thi mon khong dang ky',        COUNT(*), IF(COUNT(*)=0,'OK','LOI') FROM vv_c1b_thi_ngoai_dang_ky
UNION ALL SELECT 'C1c SV thi cung mon nhieu buoi',      COUNT(*), IF(COUNT(*)=0,'OK','LOI') FROM vv_c1c_thi_trung_mon
UNION ALL SELECT 'C1d Buoi thi khong co SV',            COUNT(*), IF(COUNT(*)=0,'OK','LOI') FROM vv_c1d_buoi_rong
UNION ALL SELECT 'C2  Dung phong bao tri',              COUNT(*), IF(COUNT(*)=0,'OK','LOI') FROM vv_c2_phong_bao_tri
UNION ALL SELECT 'C2b Trung phong + khung gio',         COUNT(*), IF(COUNT(*)=0,'OK','LOI') FROM vv_c2b_trung_phong_khung
UNION ALL SELECT 'C3  Si so vuot suc chua',             COUNT(*), IF(COUNT(*)=0,'OK','LOI') FROM vv_c3_vuot_suc_chua
UNION ALL SELECT 'C3b So may ngoai 1..suc chua',        COUNT(*), IF(COUNT(*)=0,'OK','LOI') FROM vv_c3b_so_may_sai
UNION ALL SELECT 'C3c Phong thieu phan mem',            COUNT(*), IF(COUNT(*)=0,'OK','LOI') FROM vv_c3c_thieu_phan_mem
UNION ALL SELECT 'C4  SV thi 2 buoi cung khung',        COUNT(*), IF(COUNT(*)=0,'OK','LOI') FROM vv_c4_sv_trung_khung
UNION ALL SELECT 'C5  So giam thi moi buoi',             COUNT(*), IF(COUNT(*)=0,'OK','LOI') FROM vv_c5_so_giam_thi
UNION ALL SELECT 'C6  Giam thi du 2 ca/ngay',            COUNT(*), IF(COUNT(*)=0,'OK','LOI') FROM vv_c6_giam_thi_du_ca
UNION ALL SELECT 'C7  Khung vuot so can bo coi thi',    COUNT(*), IF(COUNT(*)=0,'OK','LOI')
FROM (SELECT ma_khung
      FROM vv_si_so
      GROUP BY ma_khung
      HAVING SUM(GREATEST(2, CEIL(si_so / @sv_moi_cbct))) > @cbct_toi_da) c6;

-- ---------------------------------------------------------------------
-- 4. Chi tiết C7 (cần tham số @ nên không tạo view)
-- ---------------------------------------------------------------------
SELECT ma_khung,
       SUM(GREATEST(2, CEIL(si_so / @sv_moi_cbct))) AS can_bo_can,
       @cbct_toi_da AS toi_da
FROM vv_si_so
GROUP BY ma_khung
HAVING can_bo_can > @cbct_toi_da;

-- ---------------------------------------------------------------------
-- 5. CHỈ SỐ CHẤT LƯỢNG (không phải lỗi, dùng để so sánh thuật toán - tầng 2)
--    Z1: khung trống của các phòng đã mở;  Z2: số lần SV bị dồn >1 buổi/ngày (theo SV)
-- ---------------------------------------------------------------------
SELECT
  (SELECT COUNT(*) FROM vv_lich)                                         AS so_buoi_thi,
  (SELECT COUNT(DISTINCT ma_phong) FROM vv_lich)                         AS so_phong_mo,
  (SELECT COUNT(*) FROM khung_gio) * (SELECT COUNT(DISTINCT ma_phong) FROM vv_lich)
      - (SELECT COUNT(*) FROM vv_lich)                                   AS Z1_khung_trong,
  (SELECT COALESCE(SUM(c - 1), 0)
   FROM (SELECT d.ma_sv, k.ngay_thi, COUNT(*) AS c
         FROM vv_dk d
         JOIN vv_lich l ON l.ma_lich = d.ma_lich
         JOIN khung_gio k ON k.ma_khung = l.ma_khung
         GROUP BY d.ma_sv, k.ngay_thi HAVING COUNT(*) > 1) t)            AS Z2_sv_don_ep;