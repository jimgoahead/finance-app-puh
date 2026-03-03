import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import json # 💡 เพิ่มตัวช่วยจัดการกุญแจบน Cloud

# ==========================================
# ส่วนตั้งค่าการเชื่อมต่อ Google Sheets (รองรับ Cloud & Local)
# ==========================================
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def init_connection():
    # ตรวจสอบว่ามีข้อมูลกุญแจซ่อนอยู่ในระบบ Cloud ไหม
    if "google_credentials" in st.secrets:
        # ถ้ารันบน Cloud ให้ดึงกุญแจจาก Streamlit Secrets
        creds_dict = json.loads(st.secrets["google_credentials"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        # ถ้ารันบนคอมบ้าน ให้ใช้ไฟล์ .json ปกติ
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        
    client = gspread.authorize(creds)
    return client

client = init_connection()
SHEET_NAME = "Finance App" 
sheet = client.open(SHEET_NAME).sheet1

def load_data():
    data = sheet.get_all_records()
    if data:
        return pd.DataFrame(data)
    else:
        return pd.DataFrame(columns=['ลำดับ', 'วันที่', 'รายการ', 'รายรับ', 'รายจ่าย', 'ช่องทาง', 'หมายเหตุ'])

# ==========================================
# การตั้งค่าหน้าเว็บและสีสัน
# ==========================================
st.set_page_config(page_title="ระบบจัดการรายรับ-รายจ่าย", layout="centered")

st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        height: 50px;
        font-weight: bold;
        font-size: 18px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("💸 แอปรายรับ-รายจ่าย ประจำวัน")

df = load_data()

# ==========================================
# ส่วนที่ 1: ฟอร์มสำหรับกรอกข้อมูล
# ==========================================
st.markdown("### 📝 บันทึกรายการใหม่")

type_ = st.radio("🔄 ประเภทรายการ", ["รายจ่าย 🔴", "รายรับ 🟢"], horizontal=True)

with st.form("entry_form", clear_on_submit=True):
    date = st.date_input("📅 วันที่")
    
    if "รายจ่าย" in type_:
        category_options = [
            "🍜 ค่าอาหาร/เครื่องดื่ม", 
            "🛍️ ช้อปปิ้ง/ของใช้", 
            "⚡ ค่าน้ำ/ค่าไฟ", 
            "📱 ค่า Net/Streaming", 
            "🧺 ค่าซักผ้า",          
            "🐷 เงินเก็บส่วนกลาง", 
            "🏫 ค่าเรียนลูก", 
            "🎌 เงินเก็บค่าเที่ยวญี่ปุ่น", 
            "🚗 เดินทาง/เติมน้ำมัน", 
            "📝 อื่นๆ"
        ]
    else:
        category_options = [
            "💼 เงินเดือน", 
            "👫 ค่าส่วนกลางจากปุ๊", 
            "🎁 โบนัส/เงินพิเศษ", 
            "💸 คืนเงิน/Cashback", 
            "📈 ดอกเบี้ย/ปันผล", 
            "📝 อื่นๆ"
        ]
        
    category = st.selectbox("🏷️ หมวดหมู่", category_options)
    
    amount = st.number_input("💰 จำนวนเงิน (บาท)", min_value=0.0, format="%.2f", step=100.0)
    
    if amount > 0:
        st.markdown(f"<span style='color:#4CAF50; font-size:18px;'>✨ ยอดเงินที่ระบุ: <b>{amount:,.2f}</b> บาท</span>", unsafe_allow_html=True)
    
    channel_options = ["💳 Credit Card", "🦅 KTB", "🟢 K-BANK", "🟣 SCB", "💵 เงินสด", "📝 อื่นๆ"]
    channel = st.radio("🏦 ช่องทาง", channel_options, horizontal=True)
    
    note = st.text_input("📝 หมายเหตุ (ถ้ามี)")

    submitted = st.form_submit_button("บันทึกข้อมูลเลย!")
    
    if submitted:
        if amount <= 0:
            st.warning("⚠️ เจ้านายอย่าลืมใส่จำนวนเงินให้ถูกต้องนะคะ!")
        else:
            all_values = sheet.get_all_values()
            next_id = len(all_values) if len(all_values) > 1 else 1
            
            income_amt = amount if "รายรับ" in type_ else ""
            expense_amt = amount if "รายจ่าย" in type_ else ""
            
            date_str = date.strftime("%Y-%m-%d")
            
            new_row = [next_id, date_str, category, income_amt, expense_amt, channel, note]
            sheet.append_row(new_row)
            
            st.success(f"✨ เจนนี่บันทึกยอด {amount:,.2f} บาท สำเร็จแล้วค่ะ!")
            st.rerun()

st.markdown("---")

# ==========================================
# ส่วนที่ 2: Dashboard วิเคราะห์ข้อมูล
# ==========================================
st.markdown("### 📊 Dashboard วิเคราะห์ข้อมูล")

if not df.empty:
    df['รายรับ'] = pd.to_numeric(df['รายรับ'].replace('', 0, regex=True))
    df['รายจ่าย'] = pd.to_numeric(df['รายจ่าย'].replace('', 0, regex=True))
    df['วันที่'] = pd.to_datetime(df['วันที่'])
    df['เดือน-ปี'] = df['วันที่'].dt.strftime('%Y-%m')
    
    months_list = ["ดูทั้งหมด"] + sorted(df['เดือน-ปี'].unique().tolist(), reverse=True)
    selected_month = st.selectbox("📅 เลือกเดือนที่ต้องการดูข้อมูล:", months_list)
    
    if selected_month != "ดูทั้งหมด":
        filtered_df = df[df['เดือน-ปี'] == selected_month]
    else:
        filtered_df = df

    total_income = filtered_df['รายรับ'].sum()
    total_expense = filtered_df['รายจ่าย'].sum()
    balance = total_income - total_expense

    col1, col2 = st.columns(2)
    col1.success(f"**รายรับรวม:**\n### ฿ {total_income:,.2f}")
    col2.error(f"**รายจ่ายรวม:**\n### ฿ {total_expense:,.2f}")
    st.info(f"**ยอดคงเหลือ:**\n## ฿ {balance:,.2f}")

    st.markdown("#### 🏆 วิเคราะห์หมวดหมู่การใช้จ่าย")
    
    expense_df = filtered_df[filtered_df['รายจ่าย'] > 0]
    
    if not expense_df.empty:
        cat_expense = expense_df.groupby('รายการ', as_index=False)['รายจ่าย'].sum().sort_values(by='รายจ่าย', ascending=False)
        
        top_cat = cat_expense.iloc[0]['รายการ']
        top_amt = cat_expense.iloc[0]['รายจ่าย']
        st.warning(f"🥇 **จ่ายหนักสุดในหมวด:** {top_cat} (฿ {top_amt:,.2f})")
        
        fig = px.pie(
            cat_expense, 
            values='รายจ่าย', 
            names='รายการ', 
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_traces(textposition='inside', textinfo='percent+label', insidetextorientation='horizontal')
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("ยังไม่มีรายจ่ายในเดือนนี้ค่ะ")

    with st.expander("เปิดดูประวัติรายการทั้งหมด"):
        st.dataframe(filtered_df[['วันที่', 'รายการ', 'รายรับ', 'รายจ่าย', 'ช่องทาง', 'หมายเหตุ']].sort_values(by='วันที่', ascending=False), use_container_width=True)
else:
    st.info("ยังไม่มีข้อมูลเลยค่ะ เจ้านายลองบันทึกรายการแรกดูนะคะ!")