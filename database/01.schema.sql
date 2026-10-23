-- =====================================================================
-- Exam-management schema (MySQL 8.0+)
-- Entities: SinhVien, MonThi, PhongMay (+ software), KhungGio
-- Extra link tables (LichThi, DangKyThi) make the data usable/queryable.
-- =====================================================================
DROP DATABASE IF EXISTS quan_ly_thi;
CREATE DATABASE quan_ly_thi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE quan_ly_thi;
 
-- ---------- 1. SinhVien ----------
CREATE TABLE sinh_vien (
    ma_sv       VARCHAR(12)  NOT NULL,
    ho_ten      VARCHAR(100) NOT NULL,
    ngay_sinh   DATE         NOT NULL,
    gioi_tinh   ENUM('Nam','Nu') NOT NULL,
    email       VARCHAR(120) NOT NULL,
    so_dien_thoai VARCHAR(15),
    lop         VARCHAR(20)  NOT NULL,
    khoa        VARCHAR(80)  NOT NULL,
    khoa_hoc    SMALLINT     NOT NULL,              
    PRIMARY KEY (ma_sv),
    UNIQUE KEY uq_sv_email (email),
    KEY idx_sv_lop (lop),
    CONSTRAINT chk_sv_khoa_hoc CHECK (khoa_hoc BETWEEN 2000 AND 2100)
) ENGINE=InnoDB;

ALTER TABLE quan_ly_thi.sinh_vien MODIFY COLUMN gioi_tinh ENUM('Nam','Nu') NOT NULL;
-- 2. PhanMem (software catalogue) --
CREATE TABLE phan_mem (
    ma_pm       INT AUTO_INCREMENT PRIMARY KEY,
    ten_pm      VARCHAR(80) NOT NULL,
    phien_ban   VARCHAR(30),
    UNIQUE KEY uq_pm (ten_pm, phien_ban)
) ENGINE=InnoDB;
 
-- 3. PhongMay (lab room + hardware config) --
CREATE TABLE phong_may (
    ma_phong    VARCHAR(10) NOT NULL,
    ten_phong   VARCHAR(50) NOT NULL,
    toa_nha     VARCHAR(10) NOT NULL,
    tang        TINYINT     NOT NULL,
    suc_chua    SMALLINT    NOT NULL,               -- number of machines
    he_dieu_hanh VARCHAR(40) NOT NULL,
    tinh_trang  ENUM('Hoạt động','Bảo trì') NOT NULL DEFAULT 'Hoạt động',
    PRIMARY KEY (ma_phong),
    CONSTRAINT chk_pm_suc_chua CHECK (suc_chua > 0)
) ENGINE=InnoDB;
 
-- M:N room <-> software
CREATE TABLE phong_may_phan_mem (
    ma_phong VARCHAR(10) NOT NULL,
    ma_pm    INT         NOT NULL,
    PRIMARY KEY (ma_phong, ma_pm),
    CONSTRAINT fk_pmpm_phong FOREIGN KEY (ma_phong) REFERENCES phong_may(ma_phong) ON DELETE CASCADE,
    CONSTRAINT fk_pmpm_pm    FOREIGN KEY (ma_pm)    REFERENCES phan_mem(ma_pm)    ON DELETE CASCADE
) ENGINE=InnoDB;
 
-- ---------- 4. MonThi ----------
CREATE TABLE mon_thi (
    ma_mon      VARCHAR(10) NOT NULL,
    ten_mon     VARCHAR(120) NOT NULL,
    so_tin_chi  TINYINT     NOT NULL,
    thoi_luong_phut SMALLINT NOT NULL,
    hinh_thuc   ENUM('Trên máy','Trắc nghiệm trên máy','Thực hành') NOT NULL DEFAULT 'Trên máy',
    PRIMARY KEY (ma_mon),
    CONSTRAINT chk_mt_tc CHECK (so_tin_chi BETWEEN 1 AND 6),
    CONSTRAINT chk_mt_tl CHECK (thoi_luong_phut BETWEEN 15 AND 240)
) ENGINE=InnoDB;
 
-- Software each exam requires
CREATE TABLE mon_thi_phan_mem (
    ma_mon VARCHAR(10) NOT NULL,
    ma_pm  INT         NOT NULL,
    PRIMARY KEY (ma_mon, ma_pm),
    CONSTRAINT fk_mtpm_mon FOREIGN KEY (ma_mon) REFERENCES mon_thi(ma_mon) ON DELETE CASCADE,
    CONSTRAINT fk_mtpm_pm  FOREIGN KEY (ma_pm)  REFERENCES phan_mem(ma_pm) ON DELETE CASCADE
) ENGINE=InnoDB;
 
-- ---------- 5. KhungGio (time slot) ----------
CREATE TABLE khung_gio (
    ma_khung    INT AUTO_INCREMENT PRIMARY KEY,
    ngay_thi    DATE NOT NULL,
    ca_thi      TINYINT NOT NULL,                   -- 1..4
    gio_bat_dau TIME NOT NULL,
    gio_ket_thuc TIME NOT NULL,
    UNIQUE KEY uq_khung (ngay_thi, ca_thi),
    CONSTRAINT chk_kg_time CHECK (gio_ket_thuc > gio_bat_dau)
) ENGINE=InnoDB;
 
-- ---------- 6. LichThi (one exam session = subject + room + slot) ----------
CREATE TABLE lich_thi (
    ma_lich   INT AUTO_INCREMENT PRIMARY KEY,
    ma_mon    VARCHAR(10) NOT NULL,
    ma_phong  VARCHAR(10) NOT NULL,
    ma_khung  INT         NOT NULL,
    UNIQUE KEY uq_phong_khung (ma_phong, ma_khung),  -- a room hosts one session per slot
    KEY idx_lich_mon (ma_mon),
    CONSTRAINT fk_lt_mon   FOREIGN KEY (ma_mon)   REFERENCES mon_thi(ma_mon),
    CONSTRAINT fk_lt_phong FOREIGN KEY (ma_phong) REFERENCES phong_may(ma_phong),
    CONSTRAINT fk_lt_khung FOREIGN KEY (ma_khung) REFERENCES khung_gio(ma_khung)
) ENGINE=InnoDB;
 
-- ---------- 7. DangKyThi (student seated in a session) ----------
CREATE TABLE dang_ky_thi (
    ma_sv    VARCHAR(12) NOT NULL,
    ma_lich  INT         NOT NULL,
    so_may   SMALLINT    NOT NULL,
    diem     DECIMAL(4,2) NULL,
    PRIMARY KEY (ma_sv, ma_lich),
    UNIQUE KEY uq_lich_may (ma_lich, so_may),        -- one student per machine
    CONSTRAINT fk_dk_sv   FOREIGN KEY (ma_sv)   REFERENCES sinh_vien(ma_sv) ON DELETE CASCADE,
    CONSTRAINT fk_dk_lich FOREIGN KEY (ma_lich) REFERENCES lich_thi(ma_lich) ON DELETE CASCADE,
    CONSTRAINT chk_dk_diem CHECK (diem IS NULL OR diem BETWEEN 0 AND 10)
) ENGINE=InnoDB;

