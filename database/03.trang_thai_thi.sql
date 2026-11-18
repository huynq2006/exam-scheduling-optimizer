-- =====================================================================
-- 03.trang_thai_thi.sql  (chạy SAU 01.schema.sql, trên MASTER)
--
-- Trạng thái dự thi của sinh viên. Đây là dữ liệu NGHIỆP VỤ, tách hẳn khỏi
-- lịch thi: sinh viên bị cấm thi KHÔNG bị xoá khỏi phòng thi hay ca thi,
-- chỉ được đánh dấu. Phòng Đào tạo vẫn cần đủ danh sách để đối chiếu giấy tờ.
--
-- Hai mức:
--   CHUA_NOP_HOC_PHI : cấm thi tạm thời (nộp học phí là thi được)  -> vàng
--   CAM_THI          : cấm thi hẳn (kỷ luật, đánh trượt môn, ...)  -> đỏ
--
-- Phạm vi: ma_mon = NULL  -> áp dụng cho toàn bộ học phần của sinh viên
--          ma_mon = 'INT101' -> chỉ học phần đó
-- =====================================================================
USE quan_ly_thi;

CREATE TABLE IF NOT EXISTS trang_thai_thi (
    ma_tt       INT AUTO_INCREMENT PRIMARY KEY,
    ma_sv       VARCHAR(12)  NOT NULL,
    ma_mon      VARCHAR(10)  NULL,
    trang_thai  ENUM('CHUA_NOP_HOC_PHI','CAM_THI') NOT NULL,
    ly_do       VARCHAR(255) NULL,
    nguon       ENUM('IMPORT_CSV','THU_CONG') NOT NULL DEFAULT 'THU_CONG',
    cap_nhat_luc DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- MySQL cho phép nhiều NULL trong UNIQUE, nên phải quy NULL về một khoá
    -- tường minh thì mới chặn được 2 dòng "cấm toàn bộ" cho cùng một sinh viên.
    ma_mon_key  VARCHAR(10) AS (IFNULL(ma_mon, '*')) STORED,

    UNIQUE KEY uq_tt_sv_mon (ma_sv, ma_mon_key),
    KEY idx_tt_trang_thai (trang_thai),
    KEY idx_tt_mon (ma_mon),

    -- ma_mon phải RESTRICT, không CASCADE: MySQL cấm CASCADE trên cột mà một
    -- stored generated column (ma_mon_key) phụ thuộc vào. Xoá học phần còn
    -- vướng trạng thái thi thì báo lỗi rõ ràng, đúng ý hơn là xoá dây chuyền.
    CONSTRAINT fk_tt_sv  FOREIGN KEY (ma_sv)  REFERENCES sinh_vien(ma_sv) ON DELETE CASCADE,
    CONSTRAINT fk_tt_mon FOREIGN KEY (ma_mon) REFERENCES mon_thi(ma_mon)  ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ---------- Nhật ký từng lần import CSV ----------
-- Giữ lại để trả lời được câu "danh sách cấm thi này do ai nạp, nạp lúc nào,
-- từ file nào" khi có khiếu nại của sinh viên.
CREATE TABLE IF NOT EXISTS dot_import_cam_thi (
    ma_dot      INT AUTO_INCREMENT PRIMARY KEY,
    ten_file    VARCHAR(255) NOT NULL,
    tong_dong   INT          NOT NULL DEFAULT 0,
    so_thanh_cong INT        NOT NULL DEFAULT 0,
    so_loi      INT          NOT NULL DEFAULT 0,
    nguoi_import VARCHAR(100) NULL,
    ghi_chu     VARCHAR(255) NULL,
    tao_luc     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------- View: trạng thái hiệu lực theo từng ca thi ----------
-- Một sinh viên có thể có cả dòng cấm toàn bộ lẫn dòng cấm riêng một môn.
-- Thứ tự ưu tiên: CAM_THI > CHUA_NOP_HOC_PHI, và phạm vi hẹp (theo môn)
-- thắng phạm vi rộng khi cùng mức.
CREATE OR REPLACE VIEW v_trang_thai_theo_ca AS
SELECT dk.ma_lich,
       dk.ma_sv,
       dk.so_may,
       lt.ma_mon,
       COALESCE(
           MAX(CASE WHEN t.trang_thai = 'CAM_THI' THEN t.trang_thai END),
           MAX(t.trang_thai)
       ) AS trang_thai,
       SUBSTRING_INDEX(
           GROUP_CONCAT(t.ly_do ORDER BY (t.ma_mon IS NOT NULL) DESC, t.cap_nhat_luc DESC SEPARATOR ' | '),
           ' | ', 1
       ) AS ly_do
  FROM dang_ky_thi dk
  JOIN lich_thi lt ON lt.ma_lich = dk.ma_lich
  LEFT JOIN trang_thai_thi t
         ON t.ma_sv = dk.ma_sv
        AND (t.ma_mon IS NULL OR t.ma_mon = lt.ma_mon)
 GROUP BY dk.ma_lich, dk.ma_sv, dk.so_may, lt.ma_mon;
