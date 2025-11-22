# pages/3_📋_Requests.py
import streamlit as st
import pandas as pd
from datetime import date
from gsheet_utils import load_sheet , save_sheet

st.set_page_config(page_title="คำขอสั่งซื้อ", layout="wide")
st.title("📋 รายการขอสั่งซื้อ & แจ้งขอสั่งซื้อ")

# ---------- Helper ฟังก์ชัน ----------
def search_items_with_wildcard(df_item: pd.DataFrame, query: str, limit: int = 20):
    """
    ค้นหา Description ใน Item Data ด้วย wildcard '*'
    - '*' จะถูกแทนเป็น '.*' (regex)
    - ไม่ใส่ '*' จะค้นหาแบบ contains ธรรมดา (case-insensitive)
    """
    if not query:
        return df_item.iloc[0:0]  # empty

    desc_series = df_item["Description"].astype(str)

    # มี wildcard
    if "*" in query:
        import re

        pattern = re.escape(query).replace("\\*", ".*")
        regex = re.compile(pattern, re.IGNORECASE)
        mask = desc_series.str.contains(regex)
    else:
        mask = desc_series.str.contains(query, case=False, na=False)

    result = df_item[mask].copy()
    if limit:
        result = result.head(limit)
    return result


def generate_new_request_id(df_req: pd.DataFrame) -> str:
    """สร้าง Request_ID ใหม่แบบง่าย ๆ: REQ-0001, REQ-0002, ..."""
    if df_req.empty or "Request_ID" not in df_req.columns:
        return "REQ-0001"

    existing_ids = df_req["Request_ID"].astype(str)
    nums = []
    for x in existing_ids:
        if x.startswith("REQ-"):
            try:
                nums.append(int(x.split("-")[1]))
            except Exception:
                continue
    next_num = max(nums) + 1 if nums else 1
    return f"REQ-{next_num:04d}"


# ---------- โหลดข้อมูลจาก Google Sheet ----------
df_req = load_sheet("Request")
df_item = load_sheet("Item Data")
df_enum = load_sheet("Enum Data")

# ดึง Priority enum
priority_options = (
    df_enum["Priority"].dropna().unique().tolist()
    if "Priority" in df_enum.columns
    else []
)
if not priority_options:
    priority_options = ["ปกติ", "เร่งด่วน", "ด่วนที่สุด"]

# ดึง Status enum เฉพาะฝั่ง Request ตามที่กำหนด
REQUEST_STATUS_OPTIONS = [
    "ขอสั่งซื้อ",
    "ขอเสนอราคา",
    "เปิดใบขอซื้อ(PR)",
    "รออนุมัติโดยHead",
    "รออนุมัติโดยCOO",
    "แจ้งขอสั่งซื้อแล้ว(PR)",
]

# ---------- ส่วนฟอร์ม "แจ้งขอสั่งซื้อ" ----------
st.subheader("📝 แจ้งขอสั่งซื้อ (Create Request)")

with st.form("new_request_form", clear_on_submit=True):
    today = date.today()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Request Date", value=today.strftime("%Y-%m-%d"), disabled=True)
    with c2:
        priority = st.selectbox("Priority", priority_options, index=0)
    with c3:
        st.text_input("Status (ตั้งต้น)", value="ขอสั่งซื้อ", disabled=True)

    st.markdown("**ค้นหาสินค้า (Description) — รองรับ * เป็น wildcard**")

    c4, c5 = st.columns([2, 1])
    with c4:
        desc_query = st.text_input(
            "Description (ใส่คำค้น เช่น *Phoropter* หรือ YPC*100)",
            value="",
            placeholder="พิมพ์คำค้นได้เลย เช่น *Visual Chart*",
        )
    with c5:
        quantity = st.number_input("Quantity", min_value=1, step=1, value=1)

    # ค้นหาจาก Item Data
    selected_item_no = None
    selected_item_desc = None

    if desc_query:
        matched = search_items_with_wildcard(df_item, desc_query, limit=20)
        if not matched.empty:
            # เลือกจาก selectbox โดยโชว์ทั้งรหัส + รายละเอียด
            options_idx = matched.index.tolist()
            option_labels = [
                f"{matched.loc[i, 'No.']} - {matched.loc[i, 'Description']}"
                for i in options_idx
            ]
            chosen = st.selectbox("เลือกรายการสินค้า", options=options_idx, format_func=lambda i: option_labels[options_idx.index(i)])
            selected_item_no = str(matched.loc[chosen, "No."])
            selected_item_desc = str(matched.loc[chosen, "Description"])

            st.success(
                f"เลือกสินค้า: {selected_item_no} — {selected_item_desc}"
            )
        else:
            st.warning("ไม่พบสินค้าที่ตรงกับคำค้น")
    else:
        st.info("กรุณาพิมพ์คำค้นในช่อง Description ก่อน เพื่อค้นหาสินค้า")

    back_order = st.text_input("Back order / หมายเหตุเพิ่มเติม", "")

    submitted = st.form_submit_button("บันทึกคำขอสั่งซื้อ")

    if submitted:
        if not selected_item_no or not selected_item_desc:
            st.error("กรุณาค้นหาและเลือกสินค้าให้เรียบร้อยก่อนบันทึกคำขอสั่งซื้อ")
        else:
            new_id = generate_new_request_id(df_req)

            new_row = {
                "Request_ID": new_id,
                "Priority": priority,
                "Request_Date": today.strftime("%Y-%m-%d"),
                "Status": "ขอสั่งซื้อ",
                "Item_No": selected_item_no,
                "Description": selected_item_desc,
                "Quantity": quantity,
                # เริ่มต้นนับ Lead_Time_Status = 0 วัน
                "Lead_Time_Status": "0",
                "Back_order": back_order,
            }

            df_req = df_req.append(new_row, ignore_index=True)
            save_sheet("Request", df_req)

            st.success(f"บันทึกคำขอสั่งซื้อเรียบร้อย (Request_ID: {new_id})")

st.markdown("---")

# ---------- ตาราง "รายการขอสั่งซื้อทั้งหมด" + แก้ไข Status ----------
st.subheader("📂 รายการขอสั่งซื้อทั้งหมด")

if df_req.empty:
    st.info("ยังไม่มีคำขอสั่งซื้อในระบบ")
else:
    # แสดงตาราง + ให้แก้ไขเฉพาะ Status
    df_show = df_req.copy()

    # ทำ Data Editor
    edited_df = st.data_editor(
        df_show,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Status",
                options=REQUEST_STATUS_OPTIONS,
                help="ปรับสถานะคำขอสั่งซื้อได้จากตัวเลือกนี้",
            )
        },
        disabled=[
            "Request_ID",
            "Priority",
            "Request_Date",
            "Item_No",
            "Description",
            "Quantity",
            "Lead_Time_Status",
            "Back_order",
        ],
        num_rows="fixed",
    )

    if st.button("💾 บันทึกการแก้ไขสถานะ"):
        df_req = edited_df.copy()
        save_sheet("Request", df_req)
        st.success("บันทึกการเปลี่ยนแปลงสถานะเรียบร้อยแล้ว ✅")
