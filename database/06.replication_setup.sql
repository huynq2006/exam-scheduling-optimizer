-- =====================================================================
-- 06_replication_setup.sql
--   Dựng master -> slave replication cho quan_ly_thi.
--   Chạy SAU khi cả hai container đã lên và master đã nạp schema.
--
--   Chạy trên MASTER: phần 1 (tạo repl_user).
--   Chạy trên SLAVE : phần 2 (trỏ slave về master).
--
--   Lưu ý: binlog_do_db phải là quan_ly_thi (không phải mydatabase),
--   nếu không binlog không ghi thay đổi nào và slave sẽ không bao giờ đồng bộ.
-- =====================================================================

-- ---------- PHẦN 1: chạy trên MASTER ----------
CREATE USER IF NOT EXISTS 'repl_user'@'%' IDENTIFIED WITH mysql_native_password BY 'Repl_Pass@123';
GRANT REPLICATION SLAVE ON *.* TO 'repl_user'@'%';
FLUSH PRIVILEGES;

-- ---------- PHẦN 2: chạy trên SLAVE ----------
-- Thay <FILE> và <POSITION> bằng giá trị từ SHOW MASTER STATUS trên master.
--   CHANGE REPLICATION SOURCE TO
--     SOURCE_HOST='mysql-master',
--     SOURCE_PORT=3306,
--     SOURCE_USER='repl_user',
--     SOURCE_PASSWORD='Repl_Pass@123',
--     SOURCE_LOG_FILE='<FILE>',
--     SOURCE_LOG_POS=<POSITION>,
--     GET_SOURCE_PUBLIC_KEY=1;
--   START REPLICA;
--   SHOW REPLICA STATUS\G
