import streamlit as st
import pandas as pd
from datetime import date
from gsheet_utils import load_sheet, save_sheet

st.title("📝 แจ้งขอสั่งซื้อ")

# โหลดข้อมูลประกอบ
df_item = load_sheet("Item_Data")
df_enum = load_sheet("Enum_Data")
df_req = load_sheet("Request")

# --- Priority options ---
if "Priority" in df_enum.columns:
    priority_options = df_enum["Priority"].dropna().unique().tolist()
else:
    priority_options = ["ปกติ", "เร่งด่วน", "ด่วนมาก"]

# --- สร้าง Request ID ---
def generate_new_request_id(df):
    if df.empty or "Request_ID" not in df.columns:
        return "REQ-0001"
    ids = df["Request_ID"].astype(str)
    nums = [int(x.split("-")[1]) for x in ids if x.startswith("REQ-")]
    n = max(nums) + 1 if nums else 1
    return f"REQ-{n:04d}"

# --- ค้นหา wildcard ---
def search_items(df_item, keyword, max_result=20):
    if "*" in keyword:
        import re
        pattern = re.escape(keyword).replace("\\*", ".*")
        mask = df_item["Description"].str.contains(pattern, case=False, regex=True)
    else:
        mask = df_item["Description"].str.contains(keyword, case=False)
    return df_item[mask].head(max_result)

# -------------------------------------------------------------
# FORM START
# -------------------------------------------------------------
with st.form("request_form"):

    today = date.today()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.text_input("Request Date", today.strftime("%Y-%m-%d"), disabled=True)
    with col2:
        priority = st.selectbox("Priority", priority_options)
    with col3:
        st.text_input("Status", "ขอสั่งซื้อ", disabled=True)

    st.markdown("### เลือกสินค้า")

    colA, colB = st.columns(2)

    # Dropdown รายการสินค้า
    with colA:
        dropdown_opt = ["(ไม่เลือก)"] + [
            f"{row['No.']} - {row['Description']}"
            for _, row in df_item.iterrows()
        ]
        dropdown_selected = st.selectbox(
            "เลือกสินค้า",
            dropdown_opt
        )

    # Search box
    with colB:
        search_text = st.text_input("ค้นหาสินค้า (wildcard ใช้ * ได้)")

    selected_item_no = None
    selected_item_desc = None

    # ถ้าเลือกจาก dropdown
    if dropdown_selected != "(ไม่เลือก)":
        parts = dropdown_selected.split(" - ")
        selected_item_no = parts[0]
        selected_item_desc = " - ".join(parts[1:])
    # ถ้าใช้ search
    elif search_text:
        matched = search_items(df_item, search_text)
        if not matched.empty:
            idxs = matched.index.tolist()
            labels = [
                f"{matched.loc[i,'No.']} - {matched.loc[i,'Description']}"
                for i in idxs
            ]
            choose = st.selectbox("เลือกสินค้าที่ค้นพบ", idxs, format_func=lambda i: labels[idxs.index(i)])
            selected_item_no = matched.loc[choose, "No."]
            selected_item_desc = matched.loc[choose, "Description"]
        else:
            st.warning("ไม่พบสินค้า")

    qty = st.number_input("Quantity", min_value=1, step=1)
    back_order = st.text_input("Back order / หมายเหตุ")

    # ---- SUBMIT BUTTON IS HERE (สำคัญมาก) ----
    submitted = st.form_submit_button("บันทึกคำขอสั่งซื้อ")

# -------------------------------------------------------------
# FORM END
# -------------------------------------------------------------

if submitted:
    if not selected_item_no:
        st.error("กรุณาเลือกสินค้า หรือค้นหาให้พบก่อนบันทึก")
    else:
        new_id = generate_new_request_id(df_req)
        new_row = {
            "Request_ID": new_id,
            "Priority": priority,
            "Request_Date": today.strftime("%Y-%m-%d"),
            "Status": "ขอสั่งซื้อ",
            "Item_No": selected_item_no,
            "Description": selected_item_desc,
            "Quantity": qty,
            "Lead_Time_Status": "0",
            "Back_Order": back_order
        }
        df_req = df_req.append(new_row, ignore_index=True)
        save_sheet("Request", df_req)
        st.success(f"บันทึกคำขอสั่งซื้อสำเร็จ ✔ (ID: {new_id})")
