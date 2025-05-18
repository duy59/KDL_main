# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify
import pandas as pd
import sys
import json
import numpy as np

# Set encoding for stdout
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from datetime import datetime
from flask import Flask, render_template, request, jsonify

# Thêm đường dẫn đến thư viện ADOMD.NET
sys.path.append('C:\\Program Files\\Microsoft.NET\\ADOMD.NET\\160')

# Import pyadomd sau khi thêm đường dẫn
from pyadomd import Pyadomd

app = Flask(__name__)


def connect_to_olap():
    """Kết nối đến OLAP server"""
    try:
        # Thay đổi thông số kết nối cho phù hợp với môi trường của bạn
        # Sử dụng thông tin kết nối mà bạn đã thử thành công
        connection_string = 'Provider=LAPTOP-DUYBEOS;Data Source=localhost;Catalog=btl_dw_db;'
        return connection_string
    except Exception as e:
        print(f"Lỗi kết nối: {str(e)}")
        return None


def execute_mdx_query(mdx_query):
    """Thực thi truy vấn MDX và trả về DataFrame"""
    try:
        # Lấy chuỗi kết nối
        conn_str = connect_to_olap()
        if not conn_str:
            raise Exception("Không thể kết nối đến OLAP server")

        # Thực thi truy vấn MDX bằng pyadomd
        with Pyadomd(conn_str) as conn:
            with conn.cursor().execute(mdx_query) as cur:
                # Lấy danh sách tên cột từ metadata
                columns = [col.name for col in cur.description]
                # Lấy tất cả dữ liệu từ cursor
                data = cur.fetchall()

                # Chuyển đổi dữ liệu thành DataFrame
                df = pd.DataFrame(data, columns=columns)
                
                # In ra thông tin về dữ liệu để debug
                print(f"Raw data columns: {columns}")
                print(f"Raw data shape: {df.shape}")
                if not df.empty:
                    print(f"Raw data sample: \n{df.head()}")
                
                # Chuyển đổi các giá trị số sang kiểu số
                for col in df.columns:
                    if col in ['Fact Sales Count', 'Quantity', 'Total Amount']:
                        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                return df

    except Exception as e:
        print(f"Exception in execute_mdx_query: {str(e)}")
        raise Exception(f"Lỗi khi thực thi truy vấn MDX: {str(e)}")


def generate_mdx_query(params):
    """Tạo truy vấn MDX dựa trên các tham số từ giao diện người dùng"""
    # Xử lý các tham số
    customer_filter = params.get('customer_filter', 'all')
    time_filter = params.get('time_filter', 'all')
    item_filter = params.get('item_filter', 'all')
    year = params.get('year', 'all')
    quarter = params.get('quarter', 'all')
    month = params.get('month', 'all')
    customer_search = params.get('customer_search', '')
    item_search = params.get('item_search', '')
    
    # In ra các tham số đầu vào để debug
    print(f"\nTham số truy vấn: time_filter={time_filter}, year={year}, quarter={quarter}, month={month}")

    # Xây dựng các phần của truy vấn MDX
    select_clause = "SELECT\n"
    from_clause = "\nFROM [3D_Sales_TimeItemCustomer]\n"
    where_clause = ""
    where_conditions = []

    # Xử lý COLUMNS (Measures)
    select_clause += "  {[Measures].[Fact Sales Count], [Measures].[Quantity], [Measures].[Total Amount]} ON COLUMNS,\n"

    # Xử lý ROWS dựa trên các bộ lọc
    rows = []

    # Xử lý bộ lọc Customer
    if customer_filter == 'all':
        # Không thêm vào ROWS, sẽ tổng hợp tất cả khách hàng
        pass
    elif customer_filter == 'state':
        rows.append("[Dim Customer].[State Name].[State Name].MEMBERS")
    elif customer_filter == 'city':
        rows.append("[Dim Customer].[City Name].[City Name].MEMBERS")
    elif customer_filter == 'individual' and customer_search:
        # Tìm kiếm khách hàng cụ thể
        customer_filter_condition = f"FILTER([Dim Customer].[Customer Name].[Customer Name].MEMBERS, INSTR([Dim Customer].[Customer Name].CurrentMember.Name, \"{customer_search}\") > 0)"
        rows.append(customer_filter_condition)
        print(f"Tìm kiếm theo tên khách hàng: {customer_filter_condition}")
    elif customer_filter == 'individual':
        rows.append("[Dim Customer].[Customer Name].[Customer Name].MEMBERS")

    # Xử lý bộ lọc Item
    if item_filter == 'all':
        # Không thêm vào ROWS, sẽ tổng hợp tất cả sản phẩm
        pass
    elif item_filter == 'individual' and item_search:
        # Tìm kiếm sản phẩm cụ thể theo Item Desc hoặc Item Key
        # Sử dụng chức năng tìm kiếm theo Item Desc để đơn giản hóa
        # Vì MDX không cho phép UNION giữa các phân cấp khác nhau
        
        # Kiểm tra xem item_search có phải là mã sản phẩm (ITEM) không
        if item_search.upper().startswith('ITEM'):
            # Nếu là mã sản phẩm, tìm theo Item Key
            item_filter_condition = f"FILTER([Dim Item].[Item Key].[Item Key].MEMBERS, [Dim Item].[Item Key].CurrentMember.Name = \"{item_search}\")"
            rows.append(item_filter_condition)
            print(f"Tìm kiếm theo Item Key: {item_filter_condition}")
        else:
            # Nếu không, tìm theo Item Desc
            item_filter_condition = f"FILTER([Dim Item].[Item Desc].[Item Desc].MEMBERS, INSTR([Dim Item].[Item Desc].CurrentMember.Name, \"{item_search}\") > 0)"
            rows.append(item_filter_condition)
            print(f"Tìm kiếm theo Item Desc: {item_filter_condition}")
        
    elif item_filter == 'individual':
        rows.append("[Dim Item].[Item Desc].[Item Desc].MEMBERS")

    # Xử lý bộ lọc Time
    if time_filter == 'all':
        # Không thêm vào ROWS, sẽ tổng hợp tất cả thời gian
        pass
    elif time_filter == 'year':
        if year != 'all':
            # Thêm trực tiếp vào ROWS thay vì WHERE
            rows.append(f"[Dim Time].[Time Year].[Time Year].&[{year}]")
        else:
            rows.append("[Dim Time].[Time Year].[Time Year].MEMBERS")
    elif time_filter == 'quarter':
        # Chuyển đổi Q1, Q2, Q3, Q4 thành 1, 2, 3, 4
        quarter_num = quarter.replace('Q', '') if quarter != 'all' else 'all'
        
        if year != 'all' and quarter != 'all':
            # Sử dụng FILTER thay vì tham chiếu trực tiếp
            rows.append(f"FILTER([Dim Time].[Time Quarter].[Time Quarter].MEMBERS, [Dim Time].[Time Quarter].CurrentMember.Name = \"{quarter_num}\")")
            # Thêm điều kiện năm vào WHERE
            where_conditions.append(f"[Dim Time].[Time Year].&[{year}]")
            print(f"Lọc theo năm {year} và quý {quarter_num}")
        elif year != 'all':
            # Lọc theo năm
            rows.append("[Dim Time].[Time Quarter].[Time Quarter].MEMBERS")
            where_conditions.append(f"[Dim Time].[Time Year].&[{year}]")
            print(f"Lọc theo năm {year} cho tất cả các quý")
        elif quarter != 'all':
            # Lọc theo quý
            rows.append(f"FILTER([Dim Time].[Time Quarter].[Time Quarter].MEMBERS, [Dim Time].[Time Quarter].CurrentMember.Name = \"{quarter_num}\")")
            print(f"Lọc theo quý {quarter_num} cho tất cả các năm")
        else:
            rows.append("[Dim Time].[Time Quarter].[Time Quarter].MEMBERS")
    elif time_filter == 'month':
        if year != 'all' and month != 'all':
            # Sử dụng FILTER thay vì tham chiếu trực tiếp
            rows.append(f"FILTER([Dim Time].[Time Month].[Time Month].MEMBERS, [Dim Time].[Time Month].CurrentMember.Name = \"{month}\")")
            where_conditions.append(f"[Dim Time].[Time Year].&[{year}]")
            print(f"Lọc theo năm {year} và tháng {month}")
        elif year != 'all':
            # Lọc theo năm
            rows.append("[Dim Time].[Time Month].[Time Month].MEMBERS")
            where_conditions.append(f"[Dim Time].[Time Year].&[{year}]")
            print(f"Lọc theo năm {year} cho tất cả các tháng")
        elif month != 'all':
            # Lọc theo tháng
            rows.append(f"FILTER([Dim Time].[Time Month].[Time Month].MEMBERS, [Dim Time].[Time Month].CurrentMember.Name = \"{month}\")")
            print(f"Lọc theo tháng {month} cho tất cả các năm")
        else:
            rows.append("[Dim Time].[Time Month].[Time Month].MEMBERS")

    # Nếu không có bộ lọc nào được chọn cho ROWS, sử dụng mặc định
    if not rows:
        # Nếu không có bộ lọc nào được áp dụng, hiển thị tất cả dữ liệu tổng hợp
        select_clause += "  {} ON ROWS"
    else:
        # Kết hợp các bộ lọc với CROSSJOIN nếu có nhiều hơn 1
        if len(rows) == 1:
            select_clause += f"  {rows[0]} ON ROWS"
        else:
            crossjoin = f"CROSSJOIN({rows[0]}"
            for i in range(1, len(rows)):
                crossjoin += f", {rows[i]}"
            crossjoin += ")"
            select_clause += f"  {crossjoin} ON ROWS"

    # Thêm WHERE clause nếu có điều kiện
    if where_conditions:
        where_clause = "\nWHERE ("
        if len(where_conditions) == 1:
            where_clause += where_conditions[0]
        else:
            where_clause += ", ".join(where_conditions)
        where_clause += ")"

    # Tạo truy vấn MDX hoàn chỉnh
    mdx_query = select_clause + from_clause + where_clause
    return mdx_query


@app.route('/')
def index():
    """Render trang chủ"""
    return render_template('index.html')


@app.route('/execute', methods=['POST'])
def execute_mdx():
    """Thực thi truy vấn MDX và trả về kết quả"""
    try:
        # Lấy truy vấn MDX từ request
        mdx_query = request.form['mdx_query']

        if not mdx_query.strip():
            return jsonify({"error": "Truy vấn MDX không được để trống", "success": False}), 400

        start_time = datetime.now()

        # Thực thi truy vấn
        df = execute_mdx_query(mdx_query)

        # Tính thời gian thực thi
        execution_time = (datetime.now() - start_time).total_seconds()

        # Trả về kết quả dưới dạng HTML table
        table_html = df.to_html(classes='data-table', index=False)

        # Chuẩn bị metadata để hiển thị
        metadata = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "execution_time": f"{execution_time:.2f} giây",
            "columns": df.columns.tolist()
        }

        return jsonify({
            "table": table_html,
            "metadata": metadata,
            "success": True
        })

    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/generate_report', methods=['POST'])
def generate_report():
    """Tạo báo cáo dựa trên các tham số từ giao diện người dùng"""
    try:
        # Lấy các tham số từ request
        params = request.form.to_dict()
        
        # Tạo truy vấn MDX
        mdx_query = generate_mdx_query(params)
        print(f"Generated MDX Query: {mdx_query}")
        
        # Thực thi truy vấn
        df = execute_mdx_query(mdx_query)
        
        # Xử lý dữ liệu cho bảng
        # Nếu không có dữ liệu, trả về thông báo lỗi
        if df.empty:
            return jsonify({"error": "Không có dữ liệu phù hợp với các bộ lọc", "success": False}), 404
        
        # Loại bỏ các hàng có giá trị NaN trong các cột số lượng/giá trị
        # Xác định các cột chứa giá trị số lượng hoặc giá trị
        numeric_columns = [col for col in df.columns if any(measure in col for measure in ['[Measures].[Quantity]', '[Measures].[Sales Amount]', '[Measures].[Unit Price]'])]
        
        # Loại bỏ cột [Measures].[Fact Sales Count] nếu có
        fact_sales_count_cols = [col for col in df.columns if '[Measures].[Fact Sales Count]' in col]
        if fact_sales_count_cols:
            df = df.drop(columns=fact_sales_count_cols)
        
        if numeric_columns:
            # Loại bỏ các hàng có giá trị NaN trong tất cả các cột số
            df = df.dropna(subset=numeric_columns, how='all')
            
            # Nếu sau khi lọc không còn dữ liệu, trả về thông báo
            if df.empty:
                return jsonify({"error": "Không có dữ liệu phù hợp với các bộ lọc sau khi loại bỏ các hàng không có dữ liệu", "success": False}), 404
            
            # Làm tròn các giá trị số đến 2 chữ số thập phân
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: round(x, 2) if pd.notnull(x) else x)
        
        # Đổi tên các cột sang tiếng Việt
        column_mapping = {}
        for col in df.columns:
            if '[Dim Customer].[Customer Name].[Customer Name].[MEMBER_CAPTION]' in col:
                column_mapping[col] = 'Tên khách hàng'
            elif '[Dim Customer].[City Name].[City Name].[MEMBER_CAPTION]' in col:
                column_mapping[col] = 'Thành phố'
            elif '[Dim Customer].[State Name].[State Name].[MEMBER_CAPTION]' in col:
                column_mapping[col] = 'Bang'
            elif '[Dim Item].[Item Desc].[Item Desc].[MEMBER_CAPTION]' in col:
                column_mapping[col] = 'Tên sản phẩm'
            elif '[Dim Time].[Time Year].[Time Year].[MEMBER_CAPTION]' in col:
                column_mapping[col] = 'Năm'
            elif '[Dim Time].[Time Quarter].[Time Quarter].[MEMBER_CAPTION]' in col:
                column_mapping[col] = 'Quý'
            elif '[Dim Time].[Time Month].[Time Month].[MEMBER_CAPTION]' in col:
                column_mapping[col] = 'Tháng'
            elif '[Measures].[Quantity]' in col:
                column_mapping[col] = 'Số lượng'
            elif '[Measures].[Sales Amount]' in col:
                column_mapping[col] = 'Doanh thu'
            elif '[Measures].[Unit Price]' in col:
                column_mapping[col] = 'Đơn giá'
            elif '[Measures].[Total Amount]' in col:
                column_mapping[col] = 'Tổng doanh thu'
        
        # Đổi tên các cột
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        # Tạo HTML table
        table_html = df.to_html(classes='data-table', index=False)
        
        return jsonify({
            "table_html": table_html,
            "success": True
        })
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


def generate_inventory_mdx_query(params):
    """Tạo truy vấn MDX cho báo cáo tồn kho dựa trên các tham số từ giao diện người dùng"""
    # Lấy các tham số
    time_filter = params.get('time_filter', 'all')
    item_filter = params.get('item_filter', 'all')
    store_filter = params.get('store_filter', 'all')
    year = params.get('year', 'all')
    quarter = params.get('quarter', 'all')
    month = params.get('month', 'all')
    item_search = params.get('item_search', '')
    store_search = params.get('store_search', '')
    
    # In ra các tham số đầu vào để debug
    print(f"\nTham số truy vấn tồn kho: time_filter={time_filter}, year={year}, quarter={quarter}, month={month}")

    # Xây dựng các phần của truy vấn MDX
    select_clause = "SELECT\n"
    from_clause = "\nFROM [3D_Inventory_TimeItemStore]\n"
    where_clause = ""
    where_conditions = []
    
    # Xử lý COLUMNS (Measures)
    select_clause += "  {[Measures].[Quantity On Hand]} ON COLUMNS,\n"
    
    # Xử lý ROWS dựa trên các bộ lọc
    rows = []
    
    # Xử lý bộ lọc Store
    if store_filter == 'all':
        # Không thêm vào ROWS, sẽ tổng hợp tất cả cửa hàng
        pass
    elif store_filter == 'state':
        rows.append("[Dim Store].[State Name].[State Name].MEMBERS")
    elif store_filter == 'city':
        rows.append("[Dim Store].[City Name].[City Name].MEMBERS")
    elif store_filter == 'individual' and store_search:
        # Kiểm tra xem chuỗi tìm kiếm có phải là mã cửa hàng (STORE) không
        if store_search.upper().startswith('STORE') or store_search.isdigit():
            # Nếu là mã cửa hàng, tìm theo Store Key
            store_filter_condition = f"FILTER([Dim Store].[Store Key].[Store Key].MEMBERS, INSTR([Dim Store].[Store Key].CurrentMember.Name, \"{store_search}\") > 0)"
            rows.append(store_filter_condition)
            print(f"Tìm kiếm theo Store Key: {store_filter_condition}")
        elif any(state in store_search.upper() for state in ['CA', 'WA', 'OR', 'TX', 'NY', 'FL']):
            # Nếu chuỗi tìm kiếm có vẻ là mã bang, tìm theo State Name
            store_filter_condition = f"FILTER([Dim Store].[State Name].[State Name].MEMBERS, INSTR([Dim Store].[State Name].CurrentMember.Name, \"{store_search}\") > 0)"
            rows.append(store_filter_condition)
            print(f"Tìm kiếm theo State Name: {store_filter_condition}")
        else:
            # Trong các trường hợp khác, tìm theo City Name
            store_filter_condition = f"FILTER([Dim Store].[City Name].[City Name].MEMBERS, INSTR([Dim Store].[City Name].CurrentMember.Name, \"{store_search}\") > 0)"
            rows.append(store_filter_condition)
            print(f"Tìm kiếm theo City Name: {store_filter_condition}")
    elif store_filter == 'individual':
        rows.append("[Dim Store].[Store Key].[Store Key].MEMBERS")
    
    # Xử lý bộ lọc Item
    if item_filter == 'all':
        # Không thêm vào ROWS, sẽ tổng hợp tất cả sản phẩm
        pass
    elif item_filter == 'individual' and item_search:
        # Tìm kiếm sản phẩm cụ thể
        item_filter_condition = f"FILTER([Dim Item].[Item Desc].[Item Desc].MEMBERS, INSTR([Dim Item].[Item Desc].CurrentMember.Name, \"{item_search}\") > 0)"
        rows.append(item_filter_condition)
    elif item_filter == 'individual':
        rows.append("[Dim Item].[Item Desc].[Item Desc].MEMBERS")
    
    # Xử lý bộ lọc Time
    if time_filter == 'all':
        # Không thêm vào ROWS, sẽ tổng hợp tất cả thời gian
        pass
    elif time_filter == 'year':
        if year != 'all':
            # Thêm trực tiếp vào ROWS thay vì WHERE
            rows.append(f"[Dim Time].[Time Year].[Time Year].&[{year}]")
        else:
            rows.append("[Dim Time].[Time Year].[Time Year].MEMBERS")
    elif time_filter == 'quarter':
        # Chuyển đổi Q1, Q2, Q3, Q4 thành 1, 2, 3, 4
        quarter_num = quarter.replace('Q', '') if quarter != 'all' else 'all'
        
        if year != 'all' and quarter != 'all':
            # Sử dụng FILTER thay vì tham chiếu trực tiếp
            rows.append(f"FILTER([Dim Time].[Time Quarter].[Time Quarter].MEMBERS, [Dim Time].[Time Quarter].CurrentMember.Name = \"{quarter_num}\")")
            # Thêm điều kiện năm vào WHERE
            where_conditions.append(f"[Dim Time].[Time Year].&[{year}]")
            print(f"Lọc theo năm {year} và quý {quarter_num}")
        elif year != 'all':
            # Lọc theo năm
            rows.append("[Dim Time].[Time Quarter].[Time Quarter].MEMBERS")
            where_conditions.append(f"[Dim Time].[Time Year].&[{year}]")
            print(f"Lọc theo năm {year} cho tất cả các quý")
        elif quarter != 'all':
            # Lọc theo quý
            rows.append(f"FILTER([Dim Time].[Time Quarter].[Time Quarter].MEMBERS, [Dim Time].[Time Quarter].CurrentMember.Name = \"{quarter_num}\")")
            print(f"Lọc theo quý {quarter_num} cho tất cả các năm")
        else:
            rows.append("[Dim Time].[Time Quarter].[Time Quarter].MEMBERS")
    elif time_filter == 'month':
        if year != 'all' and month != 'all':
            # Sử dụng FILTER thay vì tham chiếu trực tiếp
            rows.append(f"FILTER([Dim Time].[Time Month].[Time Month].MEMBERS, [Dim Time].[Time Month].CurrentMember.Name = \"{month}\")")
            where_conditions.append(f"[Dim Time].[Time Year].&[{year}]")
            print(f"Lọc theo năm {year} và tháng {month}")
        elif year != 'all':
            # Lọc theo năm
            rows.append("[Dim Time].[Time Month].[Time Month].MEMBERS")
            where_conditions.append(f"[Dim Time].[Time Year].&[{year}]")
            print(f"Lọc theo năm {year} cho tất cả các tháng")
        elif month != 'all':
            # Lọc theo tháng
            rows.append(f"FILTER([Dim Time].[Time Month].[Time Month].MEMBERS, [Dim Time].[Time Month].CurrentMember.Name = \"{month}\")")
            print(f"Lọc theo tháng {month} cho tất cả các năm")
        else:
            rows.append("[Dim Time].[Time Month].[Time Month].MEMBERS")
    
    # Nếu không có bộ lọc nào được chọn cho ROWS, sử dụng mặc định
    if not rows:
        # Nếu không có bộ lọc nào được áp dụng, hiển thị tất cả dữ liệu tổng hợp
        select_clause += "  {} ON ROWS"
    else:
        # Kết hợp các bộ lọc với CROSSJOIN nếu có nhiều hơn 1
        if len(rows) == 1:
            select_clause += f"  {rows[0]} ON ROWS"
        else:
            crossjoin = f"CROSSJOIN({rows[0]}"
            for i in range(1, len(rows)):
                crossjoin += f", {rows[i]}"
            crossjoin += ")"
            select_clause += f"  {crossjoin} ON ROWS"
    
    # Tạo where_clause từ where_conditions
    if where_conditions:
        if len(where_conditions) == 1:
            where_clause = f"WHERE ({where_conditions[0]})"
        else:
            # Nếu có nhiều điều kiện, kết hợp chúng bằng toán tử AND
            where_clause = f"WHERE ({') AND ('.join(where_conditions)})"
    
    # Kết hợp các phần của truy vấn MDX
    mdx_query = select_clause
    if where_clause:
        mdx_query += from_clause + where_clause
    else:
        mdx_query += from_clause
    
    # In ra truy vấn MDX để debug
    print(f"Generated Inventory MDX Query:\n{mdx_query}")
    
    return mdx_query


@app.route('/generate_inventory_report', methods=['POST'])
def generate_inventory_report():
    """Tạo báo cáo tồn kho dựa trên các tham số từ giao diện người dùng"""
    try:
        # Lấy các tham số từ request
        params = request.form.to_dict()
        
        # Tạo truy vấn MDX
        mdx_query = generate_inventory_mdx_query(params)
        print(f"Generated Inventory MDX Query: {mdx_query}")
        
        # Thực thi truy vấn
        df = execute_mdx_query(mdx_query)
        
        # Xử lý dữ liệu cho bảng
        # Nếu không có dữ liệu, trả về thông báo lỗi
        if df.empty:
            return jsonify({"error": "Không có dữ liệu phù hợp với các bộ lọc", "success": False}), 404
        
        # Đổi tên các cột sang tiếng Việt
        column_mapping = {}
        for col in df.columns:
            if '[Dim Store].[Store Key].[Store Key].[MEMBER_CAPTION]' in col:
                column_mapping[col] = 'Mã cửa hàng'
            elif '[Dim Store].[City Name].[City Name].[MEMBER_CAPTION]' in col:
                column_mapping[col] = 'Thành phố'
            elif '[Dim Store].[State Name].[State Name].[MEMBER_CAPTION]' in col:
                column_mapping[col] = 'Bang'
            elif '[Dim Item].[Item Desc].[Item Desc].[MEMBER_CAPTION]' in col:
                column_mapping[col] = 'Tên sản phẩm'
            elif '[Dim Time].[Time Year].[Time Year].[MEMBER_CAPTION]' in col:
                column_mapping[col] = 'Năm'
            elif '[Dim Time].[Time Quarter].[Time Quarter].[MEMBER_CAPTION]' in col:
                column_mapping[col] = 'Quý'
            elif '[Dim Time].[Time Month].[Time Month].[MEMBER_CAPTION]' in col:
                column_mapping[col] = 'Tháng'
            elif '[Measures].[Quantity On Hand]' in col:
                column_mapping[col] = 'Số lượng tồn kho'
        
        # Đổi tên các cột
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        # Loại bỏ các hàng có giá trị NaN trong cột Số lượng tồn kho
        if 'Số lượng tồn kho' in df.columns:
            # Lọc bỏ các hàng có giá trị NaN
            df = df.dropna(subset=['Số lượng tồn kho'])
            
            # Nếu sau khi lọc không còn dữ liệu, trả về thông báo
            if df.empty:
                return jsonify({"error": "Không có dữ liệu tồn kho phù hợp với các bộ lọc", "success": False}), 404
            
            # Làm tròn các giá trị số đến 2 chữ số thập phân
            df['Số lượng tồn kho'] = df['Số lượng tồn kho'].round(2)
        
        # Tạo HTML table
        table_html = df.to_html(classes='data-table', index=False)
        
        return jsonify({
            "table_html": table_html,
            "success": True
        })
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
