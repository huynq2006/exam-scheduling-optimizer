-- =====================================================================
-- 02_views_triggers.sql  (chạy SAU 01_schema.sql, chỉ trên MASTER)
--   1) v_vi_pham          : "Kiểm tra hợp lệ và xung đột" (use case được <<include>>)
--   2) v_lich_thi_cong_bo : "Sinh viên chỉ xem lịch đã công bố"
--   3) Trigger khóa       : chỉ phương án ở trạng thái NHAP mới được sửa
--
-- Lưu ý replication: dùng binlog_format=ROW (mặc định MySQL 8) để slave chỉ áp dụng
-- các dòng đã đổi, không chạy lại trigger. Nếu binlog đang bật và tài khoản không có SUPER,
-- cần SET GLOBAL log_bin_trust_function_creators = 1 trước khi tạo trigger.
-- =====================================================================
USE quan_ly_thi;

-- ---------- 1. Vi phạm ràng buộc cứng (rỗng = hợp lệ) ----------
CREATE OR REPLACE VIEW v_vi_pham AS
SELECT lt.ma_pa, lt.ma_lich, 'VUOT_SUC_CHUA' AS loai,
       CONCAT(COUNT(*), ' SV > ', pm.suc_chua, ' may') AS chi_tiet
  FROM lich_thi lt
  JOIN phong_may pm ON pm.ma_phong = lt.ma_phong
  JOIN dang_ky_thi dk ON dk.ma_lich = lt.ma_lich
 GROUP BY lt.ma_pa, lt.ma_lich, pm.suc_chua
HAVING COUNT(*) > pm.suc_chua
UNION ALL
SELECT lt.ma_pa, lt.ma_lich, 'THIEU_PHAN_MEM', p.ten_pm
  FROM lich_thi lt
  JOIN mon_thi_phan_mem r ON r.ma_mon = lt.ma_mon
  JOIN phan_mem p ON p.ma_pm = r.ma_pm
  LEFT JOIN phong_may_phan_mem i ON i.ma_phong = lt.ma_phong AND i.ma_pm = r.ma_pm
 WHERE i.ma_pm IS NULL
UNION ALL
SELECT lt.ma_pa, lt.ma_lich, 'PHONG_BAO_TRI', lt.ma_phong
  FROM lich_thi lt
  JOIN phong_may pm ON pm.ma_phong = lt.ma_phong
 WHERE pm.tinh_trang <> 'Working'
UNION ALL
SELECT lt.ma_pa, MIN(lt.ma_lich), 'SV_TRUNG_KHUNG_GIO', dk.ma_sv
  FROM dang_ky_thi dk
  JOIN lich_thi lt ON lt.ma_lich = dk.ma_lich
 GROUP BY lt.ma_pa, dk.ma_sv, lt.ma_khung
HAVING COUNT(*) > 1
UNION ALL
SELECT lt.ma_pa, dk.ma_lich, 'SO_MAY_NGOAI_PHONG', CONCAT(dk.ma_sv, ' may ', dk.so_may)
  FROM dang_ky_thi dk
  JOIN lich_thi lt ON lt.ma_lich = dk.ma_lich
  JOIN phong_may pm ON pm.ma_phong = lt.ma_phong
 WHERE dk.so_may > pm.suc_chua;

-- ---------- 2. Lịch đã công bố (sinh viên / giám thị chỉ đọc view này) ----------
CREATE OR REPLACE VIEW v_lich_thi_cong_bo AS
SELECT lt.ma_lich, lt.ma_pa, lt.ma_mon, lt.ma_phong, lt.ma_khung
  FROM lich_thi lt
  JOIN phuong_an p ON p.ma_pa = lt.ma_pa
 WHERE p.trang_thai = 'DA_CONG_BO';

-- ---------- 3. Trigger khóa phương án không ở trạng thái NHAP ----------
-- (Xóa/sửa dây chuyền do FOREIGN KEY ... ON DELETE CASCADE không kích hoạt trigger.)
DROP TRIGGER IF EXISTS trg_lt_bi;
DROP TRIGGER IF EXISTS trg_lt_bu;
DROP TRIGGER IF EXISTS trg_lt_bd;
DROP TRIGGER IF EXISTS trg_dk_bi;
DROP TRIGGER IF EXISTS trg_dk_bu;
DROP TRIGGER IF EXISTS trg_dk_bd;

DELIMITER $$

CREATE TRIGGER trg_lt_bi BEFORE INSERT ON lich_thi FOR EACH ROW
BEGIN
    IF (SELECT trang_thai FROM phuong_an WHERE ma_pa = NEW.ma_pa) <> 'NHAP' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Phuong an da khoa (khong o trang thai NHAP): khong the them ca thi';
    END IF;
END$$

CREATE TRIGGER trg_lt_bu BEFORE UPDATE ON lich_thi FOR EACH ROW
BEGIN
    IF (SELECT trang_thai FROM phuong_an WHERE ma_pa = OLD.ma_pa) <> 'NHAP'
       OR (SELECT trang_thai FROM phuong_an WHERE ma_pa = NEW.ma_pa) <> 'NHAP' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Phuong an da khoa (khong o trang thai NHAP): khong the sua ca thi';
    END IF;
END$$

CREATE TRIGGER trg_lt_bd BEFORE DELETE ON lich_thi FOR EACH ROW
BEGIN
    IF (SELECT trang_thai FROM phuong_an WHERE ma_pa = OLD.ma_pa) <> 'NHAP' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Phuong an da khoa (khong o trang thai NHAP): khong the xoa ca thi';
    END IF;
END$$

CREATE TRIGGER trg_dk_bi BEFORE INSERT ON dang_ky_thi FOR EACH ROW
BEGIN
    IF (SELECT p.trang_thai FROM lich_thi l JOIN phuong_an p ON p.ma_pa = l.ma_pa
         WHERE l.ma_lich = NEW.ma_lich) <> 'NHAP' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Phuong an da khoa (khong o trang thai NHAP): khong the them dang ky thi';
    END IF;
END$$

CREATE TRIGGER trg_dk_bu BEFORE UPDATE ON dang_ky_thi FOR EACH ROW
BEGIN
    IF (SELECT p.trang_thai FROM lich_thi l JOIN phuong_an p ON p.ma_pa = l.ma_pa
         WHERE l.ma_lich = OLD.ma_lich) <> 'NHAP'
       OR (SELECT p.trang_thai FROM lich_thi l JOIN phuong_an p ON p.ma_pa = l.ma_pa
            WHERE l.ma_lich = NEW.ma_lich) <> 'NHAP' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Phuong an da khoa (khong o trang thai NHAP): khong the sua dang ky thi';
    END IF;
END$$

CREATE TRIGGER trg_dk_bd BEFORE DELETE ON dang_ky_thi FOR EACH ROW
BEGIN
    IF (SELECT p.trang_thai FROM lich_thi l JOIN phuong_an p ON p.ma_pa = l.ma_pa
         WHERE l.ma_lich = OLD.ma_lich) <> 'NHAP' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Phuong an da khoa (khong o trang thai NHAP): khong the xoa dang ky thi';
    END IF;
END$$

DELIMITER ;