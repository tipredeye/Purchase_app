# pages/2_📄_PR_PO.py
import streamlit as st
import pandas as pd
from gsheet_utils import load_sheet, save_sheet
import re

# ------------------------------------------------------------
# Helper: wildcard search
# ------------------------------------------------------------
def search_items_with_wildcard(df: pd.DataFrame, keyword: str, columns: list[str]) -> pd.DataFrame:
    """ค้นหาจากหลายคอลัมน์ใน df โดยใช้ * เป็น wildcard"""
    if not keyword:
        return df

    text_series = df[columns].astype(str).agg(" ".join, axis=1)

    if "*" in keyword:
        pattern = re.escape(keyword).replace("\\*", ".*")
        mask = text_series.str.contains(pattern, flags=re.IGNORECASE, regex=True)
    else:
        mask = text_series.str.contains(keyword, case=False, na=False)

    return df[mask]


st.set_page_config(page_title="รายการสั่งซื้อทั้งหมด", layout="wide")
st.title("📦 รายการสั่งซื้อทั้งหมด")

# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------
df_req = load_sheet("Request")      # อาจว่างได้
df_prpo = load_sheet("PR_PO")
df_enum = load_sheet("Enum_Data")

# กัน column ที่ต้องใช้ไม่ให้หาย
for col in ["Qty_to_Receive", "Quantity_Received", "Outstanding_Quantity"]:
    if col not in df_prpo.columns:
        df_prpo[col] = 0

# Status options จาก Enum_Data
if not df_enum.empty and "Status" in df_enum.columns:
    status_options_all = df_enum["Status"].dropna().unique().tolist()
else:
    status_options_all = []

# กำหนดชุดสถานะที่อนุญาตแต่ละส่วน
REQUEST_STATUS_LIMIT = ["ขอสั่งซื้อ", "ขอเสนอราคา", "เปิดใบขอซื้อ(PR)"]
PR_STATUS_LIMIT = ["เปิดใบขอซื้อ(PR)", "รออนุมัติโดยHead", "รออนุมัติโดยCOO", "แจ้งขอสั่งซื้อแล้ว(PR)"]
PO_STATUS_LIMIT = [
    "จัดทำใบสั่งซื้อ(PO)",
    "รออนุมัติโดยCFO",
    "รออนุมัติโดยCEO",
    "แจ้งสั่งซื้อแล้ว(PO)",
    "Vendor กำลังดำเนินการ",
    "อยู่ระหว่างการจัดส่ง",
    "รับสินค้าเข้าแล้ว",
]

def get_allowed_status(limit_list):
    # เอาเฉพาะที่มีอยู่จริงใน Enum_Data ถ้าไม่มีเลยใช้ list limit ดิบ ๆ
    from_enum = [s for s in status_options_all if s in limit_list]
    return from_enum if from_enum else limit_list

STATUS_REQ = get_allowed_status(REQUEST_STATUS_LIMIT)
STATUS_PR  = get_allowed_status(PR_STATUS_LIMIT)
STATUS_PO  = get_allowed_status(PO_STATUS_LIMIT)

# ------------------------------------------------------------
# SUMMARY CARDS
# ------------------------------------------------------------
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

st.markdown("### 📌 สรุปจำนวนตามสถานะ (Status)")
status_df = status_counts.reset_index()
status_df.columns = ["Status", "Count"]
st.dataframe(status_df, use_container_width=True, hide_index=True)
st.markdown("---")

# ------------------------------------------------------------
# GLOBAL FILTER
# ------------------------------------------------------------
st.markdown("### 🔍 ตัวกรองกลาง")

if not df_req.empty:
    status_from_req = df_req["Status"].dropna()
else:
    status_from_req = pd.Series([], dtype=str)

if not df_prpo.empty:
    status_from_prpo = df_prpo["Status"].dropna()
else:
    status_from_prpo = pd.Series([], dtype=str)

all_status = sorted(pd.concat([status_from_req, status_from_prpo]).unique().tolist())

status_filter = st.selectbox(
    "กรองตามสถานะ (Status)",
    options=["(ทั้งหมด)"] + all_status,
)

keyword = st.text_input(
    "ค้นหา (รองรับ * เป็น wildcard, ใช้กับเลขที่ / รหัส / รายละเอียด / Vendor)",
    value="",
    placeholder="เช่น *lens*, PQM*, MONDER*, ชื่อ Vendor"
)

def apply_filters(df: pd.DataFrame, status_col: str = "Status"):
    if df.empty:
        return df
    filtered = df.copy()
    if status_filter != "(ทั้งหมด)" and status_col in filtered.columns:
        filtered = filtered[filtered[status_col] == status_filter]

    cols_for_search = [c for c in filtered.columns
                       if c in ["Request_ID", "PO_ID", "PR_ID", "Item_No",
                                "Description", "Vendor_Name", "Back_order", "Back_Order"]]
    if cols_for_search and keyword:
        filtered = search_items_with_wildcard(filtered, keyword, cols_for_search)
    return filtered

# ------------------------------------------------------------
# 1) รายการขอสั่งซื้อ (Request) + แก้สถานะเฉพาะชุดที่อนุญาต
# ------------------------------------------------------------
st.markdown("## 1️⃣ รายการขอสั่งซื้อ (Request)")

if df_req.empty:
    st.info("ยังไม่มีรายการขอสั่งซื้อใน Sheet : Request")
else:
    df_req_view = apply_filters(df_req, status_col="Status").copy()

    # เพิ่ม checkbox เป็นคอลัมน์แรก
    if "เลือก" not in df_req_view.columns:
        df_req_view["เลือก"] = False
    cols_order = ["เลือก"] + [c for c in df_req_view.columns if c != "เลือก"]
    df_req_view = df_req_view[cols_order]

    editable_cols = ["Status", "เลือก"]
    disabled_cols = [c for c in df_req_view.columns if c not in editable_cols]

    edited_req = st.data_editor(
        df_req_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Status",
                options=STATUS_REQ,
                help="เปลี่ยนสถานะได้ถึงแค่ 'เปิดใบขอซื้อ(PR)'"
            ),
            "เลือก": st.column_config.CheckboxColumn("เลือก"),
        },
        disabled=disabled_cols,
        num_rows="fixed",
        key="req_editor",
    )

    col_r1, col_r2 = st.columns([2, 1])
    with col_r1:
        bulk_req_status = st.selectbox(
            "สถานะใหม่สำหรับรายการขอสั่งซื้อที่เลือก",
            options=STATUS_REQ,
            key="bulk_req_status",
        )
    with col_r2:
        do_bulk_req = st.button("เปลี่ยนสถานะ (Request) สำหรับรายการที่เลือก")

    if do_bulk_req:
        selected_idx = edited_req[edited_req["เลือก"] == True].index.tolist()
        if not selected_idx:
            st.error("กรุณาติ๊กเลือกรายการขอสั่งซื้อก่อน")
        else:
            df_req_updated = df_req.copy()
            df_req_updated.loc[selected_idx, "Status"] = bulk_req_status
            save_sheet("Request", df_req_updated)
            st.success(f"อัปเดตสถานะ {len(selected_idx)} รายการ (Request) เป็น '{bulk_req_status}' เรียบร้อย ✅")

st.markdown("---")

# ------------------------------------------------------------
# 2) รายการใบขอซื้อ (PR) + แก้สถานะเฉพาะชุดที่อนุญาต
# ------------------------------------------------------------
st.markdown("## 2️⃣ รายการใบขอซื้อ (PR)")

if df_prpo.empty:
    st.info("ยังไม่มีข้อมูล PR ใน Sheet : PR_PO")
else:
    # PR = มี PR_ID แต่ยังไม่มี PO_ID (ถ้า PO_ID มีแล้วจะไม่แสดงในส่วนนี้)
    df_pr = df_prpo[
        (df_prpo["PR_ID"].astype(str) != "") &
        (df_prpo["PO_ID"].astype(str) == "")
    ].copy()

    if df_pr.empty:
        st.info("ไม่มีรายการ PR ที่ยังไม่เปิด PO")
    else:
        df_pr_view = apply_filters(df_pr, status_col="Status").copy()

        # ซ่อนคอลัมน์ที่ไม่ต้องการโชว์
        hide_cols = ["PO_ID", "Qty_to_Receive", "Quantity_Received", "Outstanding_Quantity"]
        df_pr_view = df_pr_view.drop(columns=[c for c in hide_cols if c in df_pr_view.columns], errors="ignore")

        # เพิ่ม checkbox เป็นคอลัมน์แรก
        if "เลือก" not in df_pr_view.columns:
            df_pr_view["เลือก"] = False
        cols_order = ["เลือก"] + [c for c in df_pr_view.columns if c != "เลือก"]
        df_pr_view = df_pr_view[cols_order]

        editable_cols = ["Status", "เลือก"]
        disabled_cols = [c for c in df_pr_view.columns if c not in editable_cols]

        edited_pr = st.data_editor(
            df_pr_view,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=STATUS_PR,
                    help="เปลี่ยนสถานะได้ถึงแค่ 'แจ้งขอสั่งซื้อแล้ว(PR)'"
                ),
                "เลือก": st.column_config.CheckboxColumn("เลือก"),
            },
            disabled=disabled_cols,
            num_rows="fixed",
            key="pr_editor",
        )

        col_p1, col_p2 = st.columns([2, 1])
        with col_p1:
            bulk_pr_status = st.selectbox(
                "สถานะใหม่สำหรับรายการ PR ที่เลือก",
                options=STATUS_PR,
                key="bulk_pr_status",
            )
        with col_p2:
            do_bulk_pr = st.button("เปลี่ยนสถานะ (PR) สำหรับรายการที่เลือก")

        if do_bulk_pr:
            selected_idx = edited_pr[edited_pr["เลือก"] == True].index.tolist()
            if not selected_idx:
                st.error("กรุณาติ๊กเลือกรายการ PR ก่อน")
            else:
                df_updated = df_prpo.copy()
                # index ของ df_pr_view ยังอ้างถึง index เดิมของ df_prpo
                df_updated.loc[selected_idx, "Status"] = bulk_pr_status
                save_sheet("PR_PO", df_updated)
                st.success(f"อัปเดตสถานะ {len(selected_idx)} รายการ (PR) เป็น '{bulk_pr_status}' เรียบร้อย ✅")

st.markdown("---")

# ------------------------------------------------------------
# 3) รายการใบสั่งซื้อ (PO) + รับเข้าสินค้า + แก้สถานะตาม limit
# ------------------------------------------------------------
st.markdown("## 3️⃣ รายการใบสั่งซื้อ (PO) และรับเข้าสินค้า")

df_po = df_prpo[df_prpo["PO_ID"].astype(str) != ""].copy() if not df_prpo.empty else pd.DataFrame()

if df_po.empty:
    st.info("ยังไม่มีรายการใบสั่งซื้อ PO ใน Sheet : PR_PO")
    st.stop()

df_po_view = apply_filters(df_po, status_col="Status").copy()

st.markdown("### ✅ รับเข้าสินค้าจากใบสั่งซื้อ และแก้สถานะ")

# เลือก PO_ID สำหรับปุ่มรับเข้าทั้งใบ
po_ids = sorted(df_po["PO_ID"].dropna().astype(str).unique().tolist())
po_bulk = st.selectbox("เลือก PO_ID สำหรับรับเข้าทั้งใบ", ["(ไม่เลือก)"] + po_ids)

# เพิ่ม checkbox เป็นคอลัมน์แรก
if "เลือก" not in df_po_view.columns:
    df_po_view["เลือก"] = False
cols_order = ["เลือก"] + [c for c in df_po_view.columns if c != "เลือก"]
df_po_view = df_po_view[cols_order]

editable_cols = ["Status", "เลือก", "Quantity_Received"]
disabled_cols = [c for c in df_po_view.columns if c not in editable_cols]

edited_po = st.data_editor(
    df_po_view,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Status": st.column_config.SelectboxColumn(
            "Status",
            options=STATUS_PO,
            help="เปลี่ยนสถานะได้ถึง 'รับสินค้าเข้าแล้ว'"
        ),
        "เลือก": st.column_config.CheckboxColumn("เลือก"),
        "Quantity_Received": st.column_config.NumberColumn(
            "Quantity_Received",
            help="ใส่จำนวนที่รับเข้าสินค้าจริง (สะสมได้)"
        ),
    },
    disabled=disabled_cols,
    num_rows="fixed",
    key="po_editor",
)

# ----- รับเข้าทั้งใบ (ตาม PO_ID) -----
if st.button("รับเข้าทั้งหมดของ PO_ID นี้", disabled=(po_bulk == "(ไม่เลือก)")):
    df_new = df_prpo.copy()
    mask = df_new["PO_ID"].astype(str) == po_bulk

    df_new.loc[mask, "Quantity_Received"] = df_new.loc[mask, "Quantity"].astype(float)

    q = df_new["Quantity"].astype(float)
    r = df_new["Quantity_Received"].astype(float).fillna(0)

    df_new["Outstanding_Quantity"] = (q - r).clip(lower=0)
    df_new["Qty_to_Receive"] = (q - r).clip(lower=0)

    # ถ้ามีรับเข้าแล้ว → สถานะ = รับสินค้าเข้าแล้ว
    df_new.loc[df_new["Quantity_Received"] > 0, "Status"] = "รับสินค้าเข้าแล้ว"

    save_sheet("PR_PO", df_new)
    st.success(f"บันทึกการรับเข้าทั้งหมดของ PO_ID {po_bulk} เรียบร้อย")
    st.stop()

# ----- บันทึกรับเข้าสินค้า + สถานะ จากตาราง -----
if st.button("💾 บันทึกการเปลี่ยนแปลง (รับเข้า + สถานะ) จากตาราง"):
    df_new = df_prpo.copy()

    for _, row in edited_po.iterrows():
        po = str(row["PO_ID"])
        item = str(row["Item_No"])
        cond = (df_new["PO_ID"].astype(str) == po) & (df_new["Item_No"].astype(str) == item)

        qty_recv = float(row.get("Quantity_Received", 0) or 0)
        new_status = row.get("Status", "")

        df_new.loc[cond, "Quantity_Received"] = qty_recv

        if new_status in STATUS_PO:
            df_new.loc[cond, "Status"] = new_status

    q = df_new["Quantity"].astype(float)
    r = df_new["Quantity_Received"].astype(float).fillna(0)

    df_new["Outstanding_Quantity"] = (q - r).clip(lower=0)
    df_new["Qty_to_Receive"] = (q - r).clip(lower=0)

    # ถ้ามีรับเข้าแล้ว → บังคับสถานะเป็น รับสินค้าเข้าแล้ว
    df_new.loc[df_new["Quantity_Received"] > 0, "Status"] = "รับสินค้าเข้าแล้ว"

    save_sheet("PR_PO", df_new)
    st.success("อัปเดตข้อมูลรับเข้าและสถานะสำหรับ PO เรียบร้อย ✅")

# ----- Bulk เปลี่ยนสถานะ PO อย่างเดียว -----
st.markdown("### ⚙ Bulk Action เปลี่ยนสถานะใบสั่งซื้อ (PO) ที่เลือก")

col_po1, col_po2 = st.columns([2, 1])
with col_po1:
    bulk_po_status = st.selectbox(
        "สถานะใหม่สำหรับใบสั่งซื้อที่เลือก",
        options=STATUS_PO,
        key="bulk_po_status",
    )
with col_po2:
    do_bulk_po = st.button("เปลี่ยนสถานะ (PO) สำหรับรายการที่เลือก")

if do_bulk_po:
    selected_idx = edited_po[edited_po["เลือก"] == True].index.tolist()
    if not selected_idx:
        st.error("กรุณาติ๊กเลือกใบสั่งซื้อก่อน")
    else:
        df_new = df_prpo.copy()
        df_new.loc[selected_idx, "Status"] = bulk_po_status

        # ถ้ามี Quantity_Received > 0 อยู่แล้ว ให้คง / บังคับเป็น 'รับสินค้าเข้าแล้ว'
        df_new.loc[df_new["Quantity_Received"] > 0, "Status"] = "รับสินค้าเข้าแล้ว"

        save_sheet("PR_PO", df_new)
        st.success(f"อัปเดตสถานะ {len(selected_idx)} รายการ (PO) เป็น '{bulk_po_status}' เรียบร้อย ✅")
