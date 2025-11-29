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

# ---------- SUMMARY CARD ----------
st.markdown("## 📊 สรุปรายการรวม")

total_rows = len(df_prpo)

# แยกกลุ่ม PR (มี PR_ID แต่ยังไม่มี PO_ID)
df_pr = df_prpo[
    (df_prpo["PR_ID"].astype(str) != "") &
    (df_prpo["PO_ID"].astype(str) == "")
]

# แยกกลุ่ม PO (มี PO_ID)
df_po = df_prpo[df_prpo["PO_ID"].astype(str) != ""]

# นับตามสถานะ
status_counts = df_prpo["Status"].value_counts().sort_index()

col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    st.metric("จำนวนรายการทั้งหมดใน PR_PO", total_rows)
with col_s2:
    st.metric("จำนวนใบขอซื้อ (PR)", len(df_pr))
with col_s3:
    st.metric("จำนวนใบสั่งซื้อ (PO)", len(df_po))

# ตารางสรุปจำนวนตามสถานะ
st.markdown("### 📌 สรุปจำนวนตามสถานะ (Status)")
status_df = status_counts.reset_index()
status_df.columns = ["Status", "Count"]
st.dataframe(status_df, use_container_width=True, hide_index=True)
st.markdown("---")
#-----------------------------------------------------------------------

df_enum = load_sheet("Enum_Data")

# ดึงรายการ Status จาก Enum_Data
if not df_enum.empty and "Status" in df_enum.columns:
    status_options = df_enum["Status"].dropna().unique().tolist()
else:
    status_options = []  # กันไว้เผื่อยังไม่ได้เตรียม Enum_Data
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
#---------------------------------------

st.markdown("## 🔄 แก้ไขสถานะใน PR_PO (ทีละรายการ / หลายรายการพร้อมกัน)")

if df_prpo.empty:
    st.info("ยังไม่มีข้อมูลใน PR_PO")
else:
    # ใช้ตัวกรองกลางเดิม (status_filter + keyword) ถ้ามี
    df_prpo_view = apply_filters(df_prpo, status_col="Status")

    if df_prpo_view.empty:
        st.warning("ไม่พบรายการที่ตรงกับตัวกรองปัจจุบัน")
    else:
        st.write("เลือกแถวที่ต้องการ แล้วกดปุ่ม Bulk Action เพื่อเปลี่ยนสถานะทีเดียวหลายรายการได้")

        # เพิ่มคอลัมน์ checkbox 'เลือก' ใช้เลือกแถวสำหรับ bulk
        df_prpo_view = df_prpo_view.copy()
        if "เลือก" not in df_prpo_view.columns:
            df_prpo_view["เลือก"] = False

        editable_cols = ["Status", "เลือก"]
        disabled_cols = [c for c in df_prpo_view.columns if c not in editable_cols]

        edited_prpo = st.data_editor(
            df_prpo_view,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=status_options if status_options else df_prpo_view["Status"].dropna().unique().tolist(),
                    help="แก้สถานะทีละรายการ หรือใช้ Bulk Action ด้านล่าง"
                ),
                "เลือก": st.column_config.CheckboxColumn(
                    "เลือก",
                    help="ติ๊กเพื่อเลือกรายการที่จะเปลี่ยนสถานะแบบ Bulk"
                ),
            },
            disabled=disabled_cols,
            num_rows="fixed",
            key="prpo_status_editor",
        )

        # ---------------- Bulk Action ----------------
        st.markdown("### ⚙ Bulk Action เปลี่ยนสถานะหลายรายการพร้อมกัน")

        col_b1, col_b2 = st.columns([2, 1])

        with col_b1:
            bulk_status = st.selectbox(
                "เลือกสถานะใหม่ที่จะใช้กับทุกรายการที่ติ๊กไว้",
                options=status_options if status_options else df_prpo_view["Status"].dropna().unique().tolist(),
                index=0,
            )

        with col_b2:
            do_bulk = st.button("เปลี่ยนสถานะรายการที่เลือก", type="primary")

        if do_bulk:
            # หาว่ามีรายการไหนถูกติ๊กเลือกบ้าง
            selected_index = edited_prpo[edited_prpo["เลือก"] == True].index.tolist()

            if not selected_index:
                st.error("กรุณาติ๊กรายการที่ต้องการเปลี่ยนสถานะก่อน")
            else:
                df_updated = df_prpo.copy()
                # index ของ edited_prpo = index เดิมของ df_prpo ดังนั้น map กลับได้ตรง ๆ
                df_updated.loc[selected_index, "Status"] = bulk_status

                save_sheet("PR_PO", df_updated)
                st.success(f"เปลี่ยนสถานะ {len(selected_index)} รายการเป็น '{bulk_status}' เรียบร้อยแล้ว ✅")

        st.markdown("---")

# ---------------- 1) รายการขอสั่งซื้อ (จาก Request) ----------------
st.markdown("## 1️⃣ รายการขอสั่งซื้อ (Request)")

st.markdown("## 1️⃣ รายการขอสั่งซื้อ (Request)")

if df_req.empty:
    st.info("ยังไม่มีรายการขอสั่งซื้อใน Sheet : Request")
else:
    df_req_view = apply_filters(df_req, status_col="Status")

    # ฟังก์ชันใส่สีเทาอ่อนทั้งแถวถ้า Status = "เปิดใบขอซื้อ(PR)"
    def highlight_request_row(row):
        if "Status" in row and row["Status"] == "เปิดใบขอซื้อ(PR)":
            return ['background-color: #f0f0f0'] * len(row)
        return [''] * len(row)

    styled_req = df_req_view.style.apply(highlight_request_row, axis=1)

    st.dataframe(
        styled_req,
        use_container_width=True,
        hide_index=True
    )

st.markdown("---")


# ---------------- 2) รายการใบขอซื้อ PR ----------------
st.markdown("## 2️⃣ รายการใบขอซื้อ (PR)")

if df_prpo.empty:
    st.info("ยังไม่มีข้อมูล PR ใน Sheet : PR_PO")
else:
    # PR = มี PR_ID แต่ยังไม่เปิด PO
    df_pr = df_prpo[
        (df_prpo["PR_ID"].astype(str) != "") &
        (df_prpo["PO_ID"].astype(str) == "")
    ].copy()

    if df_pr.empty:
        st.info("ไม่มีรายการ PR ที่ยังไม่เปิด PO")
    else:
        df_pr_view = apply_filters(df_pr, status_col="Status")

        # ซ่อนคอลัมน์
        hide_cols = [
            "PO_ID",
            "Qty_to_Receive",
            "Quantity_Received",
            "Outstanding_Quantity"
        ]

        df_pr_view = df_pr_view.drop(columns=[c for c in hide_cols if c in df_pr_view.columns], errors="ignore")

        st.dataframe(df_pr_view, use_container_width=True, hide_index=True)

st.markdown("---")

#-----------------------------------------------------
st.markdown("## 🔄 แก้ไขสถานะใน PR_PO")

if df_prpo.empty:
    st.info("ยังไม่มีข้อมูลใน Sheet : PR_PO")
else:
    # เอาตาราง PR_PO มาผ่าน filter กลาง (Status + keyword) เหมือนส่วนอื่น
    df_prpo_view = apply_filters(df_prpo, status_col="Status")

    if df_prpo_view.empty:
        st.warning("ไม่พบรายการที่ตรงกับตัวกรองปัจจุบัน")
    else:
        st.write("แก้ไขคอลัมน์ Status ได้โดยตรงจากตารางนี้ (เลือกได้หลายรายการ)")

        # ใช้ index เดิมของ df_prpo เพื่อจะได้ map กลับได้
        df_prpo_view = df_prpo_view.copy()

        # data_editor แก้ได้เฉพาะ Status, คอลัมน์อื่น lock ไว้
        editable_cols = ["Status"]
        disabled_cols = [c for c in df_prpo_view.columns if c not in editable_cols]

        edited_prpo = st.data_editor(
            df_prpo_view,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=status_options if status_options else df_prpo_view["Status"].dropna().unique().tolist(),
                    help="เลือกสถานะจาก Enum_Data หรือค่าเดิมในตาราง"
                )
            },
            disabled=disabled_cols,
            num_rows="fixed",
            key="prpo_status_editor",
        )

        if st.button("รับเข้าทั้งหมดของ PO_ID นี้ (เต็มจำนวน)", disabled=(po_bulk == "(ไม่เลือก)")):
            df_prpo_all = df_prpo.copy()
            mask = df_prpo_all["PO_ID"].astype(str) == po_bulk

            # รับเข้าทั้งจำนวน = Quantity
            df_prpo_all.loc[mask, "Quantity_Recei"] = df_prpo_all.loc[mask, "Quantity"].astype(float)

            # คำนวณ Outstanding และ Qty_to_Receive
            q = df_prpo_all["Quantity"].astype(float)
            r = df_prpo_all["Quantity_Recei"].astype(float).fillna(0)
            df_prpo_all["Outstanding_Q"] = (q - r).clip(lower=0)
            df_prpo_all["Qty_to_Receive"] = (q - r).clip(lower=0)

            # 🔹 ถ้ามีการรับเข้าแล้ว (Quantity_Recei > 0) → สถานะ = รับสินค้าเข้าแล้ว
            received_mask = df_prpo_all["Quantity_Recei"].astype(float) > 0
            df_prpo_all.loc[received_mask, "Status"] = "รับสินค้าเข้าแล้ว"

            save_sheet("PR_PO", df_prpo_all)
            st.success(f"อัปเดตการรับเข้าทั้งหมดของ PO_ID = {po_bulk} เรียบร้อยแล้ว")
            st.stop()

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
if st.button("รับเข้าทั้งหมดของ PO_ID นี้", disabled=(po_bulk == "(ไม่เลือก)")):
    df_new = df_prpo.copy()
    mask = df_new["PO_ID"].astype(str) == po_bulk

    # รับเข้าทั้งหมด = เท่ากับ Quantity
    df_new.loc[mask, "Quantity_Received"] = df_new.loc[mask, "Quantity"].astype(float)

    q = df_new["Quantity"].astype(float)
    r = df_new["Quantity_Received"].astype(float).fillna(0)

    # คำนวณ
    df_new["Outstanding_Quantity"] = (q - r).clip(lower=0)
    df_new["Qty_to_Receive"] = (q - r).clip(lower=0)

    # ถ้ามีรับเข้าแล้ว → เปลี่ยน Status
    df_new.loc[df_new["Quantity_Received"] > 0, "Status"] = "รับสินค้าเข้าแล้ว"

    save_sheet("PR_PO", df_new)
    st.success(f"บันทึกการรับเข้าทั้งหมดของ PO_ID {po_bulk} เรียบร้อย")
    st.stop()


# ---------- ปุ่มบันทึกจากตารางที่แก้ (รับเข้าเป็นราย row) ----------
if st.button("💾 บันทึกรับเข้าสินค้าตามตารางนี้"):
    df_new = df_prpo.copy()

    for _, row in edited_po_view.iterrows():
        po = str(row["PO_ID"])
        item = str(row["Item_No"])
        cond = (df_new["PO_ID"].astype(str) == po) & \
               (df_new["Item_No"].astype(str) == item)

        qty_recv = float(row.get("Quantity_Received", 0) or 0)
        df_new.loc[cond, "Quantity_Received"] = qty_recv

    q = df_new["Quantity"].astype(float)
    r = df_new["Quantity_Received"].astype(float).fillna(0)

    df_new["Outstanding_Quantity"] = (q - r).clip(lower=0)
    df_new["Qty_to_Receive"] = (q - r).clip(lower=0)

    # Auto update status
    df_new.loc[df_new["Quantity_Received"] > 0, "Status"] = "รับสินค้าเข้าแล้ว"

    save_sheet("PR_PO", df_new)
    st.success("อัปเดตข้อมูลรับเข้าเรียบร้อย พร้อมปรับสถานะเป็น 'รับสินค้าเข้าแล้ว'")
#----------------------------------------------

def highlight_request(row):
    if row["Status"] == "เปิดใบขอซื้อ(PR)":
        return ["background-color: #ececec"] * len(row)
    return [""] * len(row)

st.dataframe(
    df_req_view.style.apply(highlight_request, axis=1),
    use_container_width=True,
    hide_index=True
)
