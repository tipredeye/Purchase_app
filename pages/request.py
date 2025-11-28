import streamlit as st
import pandas as pd
from datetime import date
from gsheet_utils import load_sheet, save_sheet

st.title("📝 แจ้งรายการขอสั่งซื้อ")

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------
# ดึงสินค้าจาก Item_Data (ต้องมีคอลัมน์ No. และ Description)
df_item = load_sheet("Item_Data")

# ดึงข้อมูล PR_PO (เก็บทั้ง Request / PR / PO)
df_prpo = load_sheet("PR_PO")

# ---------------------------------------------------------
# ฟังก์ชัน gen เลข Running Request_ID แบบ RQXXXX
# ---------------------------------------------------------
def generate_new_request_id(df: pd.DataFrame) -> str:
    """
    อ่าน Request_ID ใน df แล้ว gen เลขถัดไป เช่น RQ0001, RQ0002 ...
    ถ้ายังไม่มี RQ เลยจะเริ่มจาก RQ0001
    """
    if df.empty or "Request_ID" not in df.columns:
        return "RQ0001"

    ids = df["Request_ID"].dropna().astype(str)
    nums = []
    for val in ids:
        if val.startswith("RQ"):
            digits = "".join(ch for ch in val if ch.isdigit())
            if digits:
                nums.append(int(digits))

    next_num = max(nums) + 1 if nums else 1
    return f"RQ{next_num:04d}"


# ---------------------------------------------------------
# FORM แจ้งรายการขอสั่งซื้อ
# ---------------------------------------------------------
st.subheader("เพิ่มคำขอสั่งซื้อใหม่ (บันทึกลง PR_PO)")

with st.form("request_form", clear_on_submit=True):

    today = date.today()

    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Request Date", today.strftime("%Y-%m-%d"), disabled=True)
    with c2:
        st.text_input("Status (เริ่มต้น)", "ขอสั่งซื้อ", disabled=True)

    st.markdown("### เลือก / ค้นหาสินค้า")

    if df_item.empty or "No." not in df_item.columns or "Description" not in df_item.columns:
        st.error("ไม่พบข้อมูลสินค้าใน Sheet: Item_Data (ต้องมีคอลัมน์ 'No.' และ 'Description')")
        selected_item_no = None
        selected_item_desc = None
    else:
        item_options = [
            f"{row['No.']} - {row['Description']}"
            for _, row in df_item.iterrows()
        ]
        item_options.insert(0, "-- เลือก / พิมพ์ค้นหาสินค้า --")

        chosen_item = st.selectbox(
            "สินค้า",
            options=item_options,
            help="พิมพ์เพื่อค้นหา แล้วเลือกจากรายการที่ขึ้นมาได้"
        )

        selected_item_no = None
        selected_item_desc = None
        if chosen_item != "-- เลือก / พิมพ์ค้นหาสินค้า --":
            parts = chosen_item.split(" - ", 1)
            selected_item_no = parts[0]
            selected_item_desc = parts[1] if len(parts) > 1 else ""

    quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
    back_order = st.text_input("Back_Order / หมายเหตุ", "")

    submitted = st.form_submit_button("บันทึกคำขอสั่งซื้อ")

# ---------------------------------------------------------
# HANDLE SUBMIT
# ---------------------------------------------------------
if submitted:
    if not selected_item_no:
        st.error("กรุณาเลือกสินค้าจากช่อง 'สินค้า' ก่อนบันทึก")
        st.stop()

    new_request_id = generate_new_request_id(df_prpo)

    # เตรียม row ใหม่ให้ตรงกับโครง PR_PO ปัจจุบัน
    # ถ้าคอลัมน์บางตัวใน Sheet ใช้ชื่อแตกต่าง ให้แก้ตรง key ให้ตรง header จริง
    new_row = {
        "Request_Date": today.strftime("%Y-%m-%d"),
        "Request_ID": new_request_id,
        "PO_ID": "",                 # ยังไม่เปิด PO
        "PR_ID": "",                 # ยังไม่เปิด PR
        "Date": today.strftime("%Y-%m-%d"),  # หรือจะเว้นว่างก็ได้
        "Status": "ขอสั่งซื้อ",
        "Item_No": selected_item_no,
        "Description": selected_item_desc,
        "Quantity": quantity,
        "Back_Order": back_order,
        "Comment": "",
        "Qty_to_Receive": quantity,   # เริ่มต้น = จำนวนที่สั่ง
        "Quantity_Received": 0,          # ยังไม่รับเข้า
        "Outstanding_Quantity": quantity,    # outstanding เท่ากับ qty ตอนเริ่ม
        "Expected_Receipt_Date": "",          # ถ้ามี ETA ค่อยอัปเดตทีหลัง
        "Vendor_No.": "",
        "Vendor_Name": "",
    }

    # ป้องกันกรณี df_prpo ไม่มีคอลัมน์ครบ (เช่น Sheet เพิ่งสร้างใหม่)
    for col in df_prpo.columns:
        if col not in new_row:
            new_row[col] = ""

    df_prpo = df_prpo.append(new_row, ignore_index=True)
    save_sheet("PR_PO", df_prpo)

    st.success(f"บันทึกคำขอสั่งซื้อเรียบร้อย ✅ (Request_ID: {new_request_id})")
