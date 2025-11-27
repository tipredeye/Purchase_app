# pages/2_📄_PR_PO.py
import streamlit as st
import pandas as pd
from gsheet_utils import load_sheet, save_sheet
import re

def search_items_with_wildcard(df: pd.DataFrame, keyword: str, columns: list[str]) -> pd.DataFrame:
    """ค้นหาจากหลายคอลัมน์ใน df โดยใช้ * เป็น wildcard"""
    if not keyword:
        return df

    # รวมค่าคอลัมน์เป็น string เดียว
    text_series = df[columns].astype(str).agg(" ".join, axis=1)

    if "*" in keyword:
        pattern = re.escape(keyword).replace("\\*", ".*")
        mask = text_series.str.contains(pattern, flags=re.IGNORECASE, regex=True)
    else:
        mask = text_series.str.contains(keyword, case=False, na=False)

    return df[mask]




st.set_page_config(page_title="รายการสั่งซื้อทั้งหมด", layout="wide")
st.title("📦 รายการสั่งซื้อทั้งหมด")

# ---------------- โหลดข้อมูล ----------------
df_req = load_sheet("Request")
df_prpo = load_sheet("PR_PO")

# กัน column หาย
for col in ["Qty_to_Receive", "Quantity_Received", "Outstanding_Quantity"]:
    if col not in df_prpo.columns:
        df_prpo[col] = 0

# ---------------- Filter ส่วนกลาง (ใช้ร่วมทุก section) ----------------
st.markdown("### 🔍 ตัวกรองกลาง")

all_status = sorted(
    pd.concat([
        df_req["Status"].dropna(),
        df_prpo["Status"].dropna()
    ]).unique().tolist()
) if not df_req.empty or not df_prpo.empty else []

status_filter = st.selectbox(
    "กรองตามสถานะ (Status)",
    options=["(ทั้งหมด)"] + all_status,
)

keyword = st.text_input(
    "ค้นหา (รองรับ * เป็น wildcard, ใช้กับเลขที่ / รหัส / รายละเอียด / Vendor)",
    value="",
    placeholder="เช่น *lens*, PQM*, MONDER*, ชื่อ Vendor"
)

# helper ใช้ filter
def apply_filters(df: pd.DataFrame, status_col: str = "Status"):
    if df.empty:
        return df
    filtered = df.copy()
    if status_filter != "(ทั้งหมด)" and status_col in filtered.columns:
        filtered = filtered[filtered[status_col] == status_filter]
    # ใช้ wildcard search กับชุดคอลัมน์หลัก
    cols_for_search = [c for c in filtered.columns
                       if c in ["Request_ID","PO_ID","PR_ID","Item_No","Description","Vendor_Name","Back_order","Back_Order"]]
    if cols_for_search and keyword:
        filtered = search_items_with_wildcard(filtered, keyword, cols_for_search)
    return filtered

# ---------------- 1) รายการขอสั่งซื้อ (จาก Request) ----------------
st.markdown("## 1️⃣ รายการขอสั่งซื้อ (Request)")

if df_req.empty:
    st.info("ยังไม่มีรายการขอสั่งซื้อใน Sheet : Request")
else:
    df_req_view = apply_filters(df_req, status_col="Status")
    st.dataframe(
        df_req_view,
        use_container_width=True,
        hide_index=True
    )

st.markdown("---")

# ---------------- 2) รายการใบขอซื้อ PR ----------------
st.markdown("## 2️⃣ รายการใบขอซื้อ (PR)")

# สมมติว่า row ที่เป็น PR คือแถวที่มี PR_ID ไม่ว่าง
df_pr = df_prpo[df_prpo["PR_ID"].astype(str) != ""].copy() if not df_prpo.empty else pd.DataFrame()

if df_pr.empty:
    st.info("ยังไม่มีรายการใบขอซื้อ PR ใน Sheet : PR_PO")
else:
    df_pr_view = apply_filters(df_pr, status_col="Status")
    st.dataframe(
        df_pr_view,
        use_container_width=True,
        hide_index=True
    )

st.markdown("---")

# ---------------- 3) รายการใบสั่งซื้อ PO + ทำรับเข้า ----------------
st.markdown("## 3️⃣ รายการใบสั่งซื้อ (PO) และรับเข้าสินค้า")

# สมมติว่า row ที่เป็น PO คือแถวที่มี PO_ID ไม่ว่าง
df_po = df_prpo[df_prpo["PO_ID"].astype(str) != ""].copy() if not df_prpo.empty else pd.DataFrame()

if df_po.empty:
    st.info("ยังไม่มีรายการใบสั่งซื้อ PO ใน Sheet : PR_PO")
    st.stop()

df_po_view = apply_filters(df_po, status_col="Status")

st.markdown("### ✅ รับเข้าสินค้าจากใบสั่งซื้อ (แก้ไข Quantity_Received ได้)")

# แสดง editor ให้แก้เฉพาะ Quantity_Received
editable_cols = ["Quantity_Received"]
disabled_cols = [c for c in df_po_view.columns if c not in editable_cols]

edited_po_view = st.data_editor(
    df_po_view,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Quantity_Received": st.column_config.NumberColumn(
            "Quantity_Received",
            help="ใส่จำนวนที่รับเข้าสินค้าจริง (สะสมได้)"
        )
    },
    disabled=disabled_cols,
    num_rows="fixed",
    key="po_editor",
)

# ---------- ปุ่ม action: รับเข้าทุกรายการใน PO_ID เดียวกัน ----------
st.markdown("#### ⚙ ตัวเลือกการรับเข้าแบบรวดเร็ว")

col_po1, col_po2 = st.columns(2)

with col_po1:
    if not df_po.empty:
        po_ids = sorted(df_po["PO_ID"].dropna().astype(str).unique().tolist())
    else:
        po_ids = []
    po_bulk = st.selectbox("เลือก PO_ID เพื่อรับเข้าทุก Row แบบเต็มจำนวน", ["(ไม่เลือก)"] + po_ids)

    if st.button("รับเข้าทั้งหมดของ PO_ID นี้ (เต็มจำนวน)", disabled=(po_bulk=="(ไม่เลือก)")):
        df_prpo_all = df_prpo.copy()
        mask = df_prpo_all["PO_ID"].astype(str) == po_bulk
        df_prpo_all.loc[mask, "Quantity_Received"] = df_prpo_all.loc[mask, "Quantity"].astype(float)

        # คำนวณ Outstanding และ Qty_to_Receive ใหม่
        q = df_prpo_all["Quantity"].astype(float)
        r = df_prpo_all["Quantity_Received"].astype(float)
        df_prpo_all["Outstanding_Quantity"] = (q - r).clip(lower=0)
        df_prpo_all["Qty_to_Receive"] = (q - r).clip(lower=0)

        save_sheet("PR_PO", df_prpo_all)
        st.success(f"อัปเดตการรับเข้าทั้งหมดของ PO_ID = {po_bulk} เรียบร้อยแล้ว")
        st.stop()

with col_po2:
    st.markdown(
        "💡 ถ้าอยากรับเข้าแค่บางรายการ หรือระบุจำนวนเอง:\n"
        "1. แก้ค่าในคอลัมน์ `Quantity_Received` ในตารางด้านบน\n"
        "2. กดปุ่ม **บันทึกการรับเข้าตามตาราง** ด้านล่าง"
    )

st.markdown("----")

# ---------- ปุ่มบันทึกจากตารางที่แก้ (รับเข้าเป็นราย row) ----------
if st.button("💾 บันทึกการรับเข้าตามตารางด้านบน"):
    # นำค่า Quantity_Received จาก edited_po_view กลับไปใส่ df_prpo ตัวเต็ม
    df_prpo_updated = df_prpo.copy()

    for _, row in edited_po_view.iterrows():
        po_id = str(row["PO_ID"])
        item_no = str(row["Item_No"])
        # match ด้วย PO_ID + Item_No (ปรับ logic key ได้ตามจริง)
        cond = (df_prpo_updated["PO_ID"].astype(str) == po_id) & \
               (df_prpo_updated["Item_No"].astype(str) == item_no)

        df_prpo_updated.loc[cond, "Quantity_Received"] = float(row.get("Quantity_Received", 0))

    # คำนวณ Outstanding_Quantity และ Qty_to_Receive ใหม่
    q = df_prpo_updated["Quantity"].astype(float)
    r = df_prpo_updated["Quantity_Received"].astype(float).fillna(0)
    df_prpo_updated["Outstanding_Quantity"] = (q - r).clip(lower=0)
    df_prpo_updated["Qty_to_Receive"] = (q - r).clip(lower=0)

    save_sheet("PR_PO", df_prpo_updated)
    st.success("บันทึกการรับเข้าและคำนวณ Outstanding / Qty_to_Receive เรียบร้อยแล้ว ✅")

