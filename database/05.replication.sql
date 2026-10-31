CREATE USER IF NOT EXISTS 'app_user'@'%' IDENTIFIED BY 'App_Pass@123';
GRANT ALL PRIVILEGES ON quan_ly_thi.* TO 'app_user'@'%';