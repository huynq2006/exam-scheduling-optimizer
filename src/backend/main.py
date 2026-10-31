import pymysql
import os
from db_helper import get_master_connection, get_slave_connection

if __name__ == "__main__":
    try:
        master_conn = get_master_connection()
        print("✅ Kết nối Master (cổng 13306) thành công!")
        master_conn.close()

        slave_conn = get_slave_connection()
        print("✅ Kết nối Slave (cổng 13307) thành công!")
        slave_conn.close()
    except Exception as e:
        print("❌ Kết nối thất bại:", e)
