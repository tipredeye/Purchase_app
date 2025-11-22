# gsheet_utils.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ใส่ Spreadsheet ID ของ Google Sheet ที่ใช้เป็น DB
SPREADSHEET_ID = "1PJAsYCGARfKITdB0ITZUpr0F-vaImuXI431iQjy1YZY"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def get_gsheet_client():
    """สร้าง gspread client จาก service account ที่เก็บใน st.secrets"""
    creds_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client


def load_sheet(sheet_name: str) -> pd.DataFrame:
    """อ่านข้อมูลทั้ง Sheet มาเป็น DataFrame"""
    client = get_gsheet_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(sheet_name)
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    return df


def save_sheet(sheet_name: str, df: pd.DataFrame):
    """
    เขียน DataFrame กลับไปที่ Google Sheet ทั้งหน้า
    (จะ clear แล้วเขียน Header + ข้อมูลใหม่ทั้งหมด)
    """
    client = get_gsheet_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(sheet_name)

    # แปลง NaN -> "" ป้องกัน error เวลา update
    df_to_save = df.copy()
    df_to_save = df_to_save.fillna("")

    rows = [df_to_save.columns.tolist()] + df_to_save.astype(str).values.tolist()

    ws.clear()
    ws.update(rows)
