# pages/1_📊_Dashboard.py
import streamlit as st
from Complete_pur_app.gsheet_utils import load_sheet, save_sheet

st.set_page_config(page_title="Purchase Dashboard", layout="wide")

st.title("📊 Purchase Dashboard")

# โหลดข้อมูล
df_req = load_sheet("Request")
df_prpo = load_sheet("PRPO")

if df_req.empty and df_prpo.empty:
    st.info("ยังไม่มีข้อมูลในระบบเลย ลองไปสร้างคำขอสั่งซื้อหรือ PR/PO ก่อนนะ ✨")
    st.stop()

today = pd.Timestamp.today().normalize()

# ทำ Lead Time (วัน) จาก Request_Date
if not df_req.empty and "Request_Date" in df_req.columns:
    try:
        df_req["Request_Date_parsed"] = pd.to_datetime(df_req["Request_Date"])
        df_req["Lead_Days"] = (today - df_req["Request_Date_parsed"]).dt.days
    except Exception:
        df_req["Lead_Days"] = None

# ================= KPI บนสุด =================
col1, col2, col3, col4 = st.columns(4)

total_requests = len(df_req) if not df_req.empty else 0
pending_statuses = [
    "ขอสั่งซื้อ",
    "ขอเสนอราคา",
    "เปิดใบขอซื้อ(PR)",
    "รออนุมัติโดยHead",
    "รออนุมัติโดยCOO",
]
pending_requests = (
    df_req["Status"].isin(pending_statuses).sum() if not df_req.empty else 0
)

total_po = len(df_prpo) if not df_prpo.empty else 0
received_po = (
    df_prpo["Status"].eq("รับสินค้าเข้าแล้ว").sum() if not df_prpo.empty else 0
)

col1.metric("จำนวนคำขอสั่งซื้อทั้งหมด", total_requests)
col2.metric("คำขอสั่งซื้อที่ยังไม่ปิด", pending_requests)
col3.metric("จำนวน PR/PO ทั้งหมด", total_po)
col4.metric("PO ที่รับสินค้าแล้ว", received_po)

st.markdown("---")

# ================= Chart: Request by Status =================
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("จำนวนคำขอสั่งซื้อตามสถานะ")

    if not df_req.empty:
        status_counts = df_req["Status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        st.bar_chart(
            status_counts.set_index("Status")["Count"],
            height=300,
        )
    else:
        st.caption("ยังไม่มี Request")

with col_right:
    st.subheader("Priority Breakdown")

    if not df_req.empty:
        prio_counts = df_req["Priority"].value_counts().reset_index()
        prio_counts.columns = ["Priority", "Count"]
        st.bar_chart(
            prio_counts.set_index("Priority")["Count"],
            height=300,
        )
    else:
        st.caption("ยังไม่มี Request")

st.markdown("---")

# ================= ตารางรายละเอียดแบบ Filter =================
st.subheader("รายละเอียดคำขอสั่งซื้อ (Filter ได้)")

if not df_req.empty:
    # Filter by Status & Priority
    status_options = ["(ทั้งหมด)"] + sorted(df_req["Status"].dropna().unique().tolist())
    prio_options = ["(ทั้งหมด)"] + sorted(
        df_req["Priority"].dropna().unique().tolist()
    )

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        status_filter = st.selectbox("กรองตาม Status", status_options)
    with f_col2:
        prio_filter = st.selectbox("กรองตาม Priority", prio_options)

    df_view = df_req.copy()
    if status_filter != "(ทั้งหมด)":
        df_view = df_view[df_view["Status"] == status_filter]
    if prio_filter != "(ทั้งหมด)":
        df_view = df_view[df_view["Priority"] == prio_filter]

    st.dataframe(df_view, use_container_width=True, hide_index=True)
else:
    st.caption("ยังไม่มี Request ให้แสดง")

