import streamlit as st
import pandas as pd
from datetime import date
from gsheet_utils import load_sheet, save_sheet


st.title("📝 แจ้งขอสั่งซื้อ (Create Request)")

# ---------------------------------------------------------
# โหลดข้อมูลจาก Google Sheet
# ---------------------------------------------------------
df_item = load_sheet("Item_Data")
df_req = load_sheet("Request")
df_enum = load_sheet("Enum_Data") if "Enum_Data" in st.secrets else pd.DataFrame()

# ---------------------------------------------------------
# Priority Options (ถ้ามีใน Enum_Data)
# ---------------------------------------------------------
if not df_enum.empty and "Priority" in df_enum.columns:
    priority_options = df_enum["Priority"].dropna().unique().tolist()
else:
    priority_options = ["ปกติ", "เร่งด่วน", "ด่วนมาก"]

# ---------------------------------------------------------
# Helper: Wildcard Search
# ---------------------------------------------------------
def search_items_with_wildcard(df: pd.DataFrame, keyword: str, limit: int = 20):
    if "*" in keyword:
        pattern = re.escape(keyword).replace("\\*", ".*")
        mask = df["Description"].str.contains(pattern, case=False, regex=True)
    else:
        mask = df["Description"].str.contains(keyword, case=False)
    return df[mask].head(limit)

# ---------------------------------------------------------
# Generate Request_ID ใหม่
# ---------------------------------------------------------
def generate_new_request_id(df):
    if df.empty or "Request_ID" not in df.columns:
        return "REQ-0001"

    ids = df["Request_ID"].dropna().astype(str)
    nums = [int(x.split("-")[1]) for x in ids if x.startswith("REQ-")]
    new_num = max(nums) + 1 if nums else 1
    return f"REQ-{new_num:04d}"

# ---------------------------------------------------------
# 📝 FORM แจ้งขอสั่งซื้อ
# ---------------------------------------------------------
st.subheader("เพิ่มคำขอสั่งซื้อใหม่")

with st.form("request_form", clear_on_submit=True):

    today = date.today()
    col1, col2 = st.columns(2)

    with col1:
        st.text_input("Request Date", today.strftime("%Y-%m-%d"), disabled=True)

    with col2:
        st.text_input("Status (เริ่มต้น)", "ขอสั่งซื้อ", disabled=True)

    # --- เลือกสินค้า ---
    st.markdown("### เลือกสินค้า (Dropdown หรือค้นหา)")

    colA, colB = st.columns(2)

    # Dropdown
    with colA:
        dropdown_opt = ["(ไม่เลือก)"] + [
            f"{row['No.']} - {row['Description']}" for _, row in df_item.iterrows()
        ]
        dropdown_selected = st.selectbox("เลือกสินค้า", dropdown_opt)

    # ค้นหา wildcard
    with colB:
        search_text = st.text_input("ค้นหา (รองรับ wildcard * )", "")

    selected_item_no = None
    selected_item_desc = None

    # A) ถ้าเลือก dropdown
    if dropdown_selected != "(ไม่เลือก)":
        parts = dropdown_selected.split(" - ")
        selected_item_no = parts[0]
        selected_item_desc = " - ".join(parts[1:])

    # B) ถ้าค้นหาเอง
    elif search_text:
        match = search_items_with_wildcard(df_item, search_text)
        if not match.empty:
            idxs = match.index.tolist()
            labels = [
                f"{match.loc[i,'No.']} - {match.loc[i,'Description']}"
                for i in idxs
            ]
            chosen = st.selectbox("เลือกรายการที่ค้นพบ", idxs,
                                  format_func=lambda i: labels[idxs.index(i)])
            selected_item_no = match.loc[chosen, "No."]
            selected_item_desc = match.loc[chosen, "Description"]
        else:
            st.warning("ไม่พบข้อมูลสินค้า")

    # จำนวน
    quantity = st.number_input("Quantity", min_value=1, value=1)

    # Back order
    back_order = st.text_input("Back order / หมายเหตุ", "")

    # Submit button
    submitted = st.form_submit_button("บันทึกคำขอ")

# ---------------------------------------------------------
# เมื่อกดปุ่ม Submit
# ---------------------------------------------------------
if submitted:
    if not selected_item_no:
        st.error("กรุณาเลือกหรือค้นหาสินค้าให้ถูกต้องก่อนบันทึก")
        st.stop()

    new_id = generate_new_request_id(df_req)
    lead_time = 0  # เริ่มนับวันเปิดรายการ

    new_row = {
        "Request_ID": new_id,
        "Request_Date": today.strftime("%Y-%m-%d"),
        "Status": "ขอสั่งซื้อ",
        "Item_No": selected_item_no,
        "Description": selected_item_desc,
        "Quantity": quantity,
        "Lead_Time_Status": str(lead_time),
        "Back_order": back_order
    }

    df_req = df_req.append(new_row, ignore_index=True)
    save_sheet("Request", df_req)

    st.success(f"บันทึกคำขอสั่งซื้อสำเร็จ ✔ (Request_ID: {new_id})")

