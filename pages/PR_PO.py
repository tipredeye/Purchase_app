# pages/2_📄_PR_PO.py
import streamlit as st
from gsheet_utils import load_sheet

st.set_page_config(page_title="PR / PO", layout="wide")
st.title("📄 PR / PO Management")

df_prpo = load_sheet("PRPO")

PRPO_STATUS_OPTIONS = [
    "จัดทำใบสั่งซื้อ(PO)",
    "รออนุมัติโดยCFO",
    "รออนุมัติโดยCEO",
    "แจ้งสั่งซื้อแล้ว(PO)",
    "Vendor กำลังดำเนินการ",
    "อยู่ระหว่างการจัดส่ง",
    "รับสินค้าเข้าแล้ว",
]

if df_prpo.empty:
    st.info("ยังไม่มีข้อมูล PR/PO ในระบบ")
    st.stop()

# Filters แบบง่าย ๆ
st.subheader("🔍 ค้นหา / กรอง PR/PO")

c1, c2, c3 = st.columns(3)
with c1:
    status_filter = st.selectbox(
        "กรองตาม Status",
        options=["(ทั้งหมด)"] + PRPO_STATUS_OPTIONS,
    )
with c2:
    vendor_filter = st.text_input("กรองตาม Vendor Name (contains)", "")
with c3:
    po_filter = st.text_input("ค้นหา PO_ID (contains)", "")

df_view = df_prpo.copy()

if status_filter != "(ทั้งหมด)":
    df_view = df_view[df_view["Status"] == status_filter]

if vendor_filter:
    df_view = df_view[
        df_view["Vendor_Name"].astype(str).str.contains(vendor_filter, case=False)
    ]

if po_filter:
    df_view = df_view[df_view["PO_ID"].astype(str).str.contains(po_filter)]

st.subheader("📦 รายการ PR / PO ทั้งหมด (แก้ไข Status ได้)")

edited_df = st.data_editor(
    df_view,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Status": st.column_config.SelectboxColumn(
            "Status",
            options=PRPO_STATUS_OPTIONS,
            help="ปรับสถานะ PR/PO ได้จากตัวเลือกนี้",
        )
    },
    disabled=[
        col
        for col in df_view.columns
        if col not in ["Status"]
    ],
    num_rows="fixed",
)

if st.button("💾 บันทึกการเปลี่ยนแปลง Status ของ PR/PO"):
    # เอา Status ที่แก้จาก df_view ไป merge กลับ df_prpo ตัวเต็ม
    df_updated = df_prpo.copy()
    # ใช้ PO_ID + Item_No เป็น key (ติ๊บจะเปลี่ยน key ก็ได้)
    key_cols = ["PO_ID", "Item_No"]

    # อัพเดตเฉพาะ Status
    for _, row in edited_df.iterrows():
        cond = (df_updated["PO_ID"] == row["PO_ID"]) & (
            df_updated["Item_No"] == row["Item_No"]
        )
        df_updated.loc[cond, "Status"] = row["Status"]

    save_sheet("PRPO", df_updated)
    st.success("บันทึกการเปลี่ยนแปลงสถานะ PR/PO เรียบร้อย ✅")
