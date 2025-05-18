import sys
sys.path.append('C:\\Program Files\\Microsoft.NET\\ADOMD.NET\\160')  # Thay đổi nếu cần

from pyadomd import Pyadomd

# Thử kết nối đến OLAP server (thay đổi thông tin kết nối cho phù hợp)
connection_string = 'Provider=MSOLAP;Data Source=localhost;Catalog=btl_dw_db;'
try:
    with Pyadomd(connection_string) as conn:
        print("Kết nối thành công!")
except Exception as e:
    print(f"Lỗi kết nối: {str(e)}")
