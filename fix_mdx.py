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
            # Thêm trực tiếp vào ROWS
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
            # Lọc theo năm và tháng
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
