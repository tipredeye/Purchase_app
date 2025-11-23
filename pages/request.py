# pages/3_📋_Requests.py
import streamlit as st
import pandas as pd
from datetime import date
from gsheet_utils import load_sheet , save_sheet

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

    st.markdown("### เลือกสินค้า (Dropdown) หรือค้นหาแบบพิมพ์")

    colA, colB = st.columns(2)

    # --------------------------
    # A) Dropdown: เลือกสินค้า
    # --------------------------
    with colA:
        item_dropdown = st.selectbox(
            "เลือกสินค้า (จาก Item Data)",
            ["(ไม่เลือกสินค้า)"] + [
                f"{row['No.']} - {row['Description']}"
                for _, row in df_item.iterrows()
            ]
        )

    # --------------------------
    # B) Search Box แบบเดิม
    # --------------------------
    with colB:
        desc_query = st.text_input(
            "ค้นหาสินค้า (รองรับ wildcard เช่น *lens*)",
            value="",
            placeholder="ใส่คำค้น หรือเลือกรายการจากด้านซ้าย"
        )

    # กำหนดค่าจากการเลือก
    selected_item_no = None
    selected_item_desc = None

    # --------------------------
    # Logic A: ถ้าเลือกจาก dropdown
    # --------------------------
    if item_dropdown != "(ไม่เลือกสินค้า)":
        no_part = item_dropdown.split(" - ")[0]
        desc_part = " - ".join(item_dropdown.split(" - ")[1:])
        selected_item_no = no_part
        selected_item_desc = desc_part

    # --------------------------
    # Logic B: ถ้าพิมพ์ค้นหาเอง
    # --------------------------
    elif desc_query:
        matched = search_items_with_wildcard(df_item, desc_query, limit=20)
        if not matched.empty:
            options_idx = matched.index.tolist()
            option_labels = [
                f"{matched.loc[i, 'No.']} - {matched.loc[i, 'Description']}"
                for i in options_idx
            ]
            chosen = st.selectbox(
                "เลือกรายการที่ค้นพบ",
                options=options_idx,
                format_func=lambda i: option_labels[options_idx.index(i)]
            )
            selected_item_no = str(matched.loc[chosen, "No."])
            selected_item_desc = str(matched.loc[chosen, "Description"])
        else:
            st.warning("ไม่พบสินค้าจากคำค้น")

    quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
    back_order = st.text_input("Back order / หมายเหตุเพิ่มเติม", "")

    submitted = st.form_submit_button("บันทึกคำขอสั่งซื้อ")

    if submitted:
        if not selected_item_no or not selected_item_desc:
            st.error("กรุณาเลือกสินค้า หรือค้นหาให้เจอก่อนบันทึก")
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
                "Lead_Time_Status": "0",
                "Back_order": back_order,
            }

            df_req = df_req.append(new_row, ignore_index=True)
            save_sheet("Request", df_req)

            st.success(f"บันทึกคำขอสั่งซื้อเรียบร้อย (Request_ID: {new_id})")


