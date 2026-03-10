import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import json 
import re  

# ==========================================
# ส่วนตั้งค่าการเชื่อมต่อ Google Sheets
# ==========================================
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def init_connection():
    if "google_credentials" in st.secrets:
        creds_dict = json.loads(st.secrets["google_credentials"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        
    client = gspread.authorize(creds)
    return client

client = init_connection()
SHEET_NAME = "Finance App Puh" 
sheet = client.open(SHEET_NAME).sheet1

def load_data():
    data = sheet.get_all_records()
    cols = ['ลำดับ', 'วันที่', 'รายการ', 'รายรับ', 'รายจ่าย', 'ช่องทาง', 'หมายเหตุ', 'ประเภทการจ่าย', 'จำนวนงวด', 'งวดปัจจุบัน', 'ID รายการผ่อน', 'เดือนที่จ่ายบิล']
    if data:
        df = pd.DataFrame(data)
        for col in cols:
            if col not in df.columns:
                df[col] = ""
        return df
    else:
        return pd.DataFrame(columns=cols)

# ==========================================
# การตั้งค่าหน้าเว็บและสีสัน
# ==========================================
st.set_page_config(page_title="ระบบจัดการรายรับ-รายจ่าย (Puh)", layout="centered")

st.markdown("""
    <style>
    div[data-testid="stTextInput"] label { display: none; }
    div[data-testid="stTextInput"]:has(input[placeholder*="แตะที่นี่แล้วพูด"]) div[data-baseweb="base-input"] {
        background-color: #e0f7fa !important;
        border: 2px solid #00acc1 !important;
        border-radius: 8px !important;
        padding: 5px !important;
    }
    div[data-testid="stTextInput"]:has(input[placeholder*="แตะที่นี่แล้วพูด"]) input {
        color: #000000 !important; 
        -webkit-text-fill-color: #000000 !important; 
        font-weight: bold !important;
        font-size: 16px !important;
    }
    div[data-testid="stTextInput"]:has(input[placeholder*="แตะที่นี่แล้วพูด"]) input::placeholder {
        color: #9e9e9e !important;
        -webkit-text-fill-color: #9e9e9e !important;
        font-weight: normal !important; 
        opacity: 1 !important;
    }
    div[data-testid="stColumn"]:nth-child(1) div[data-testid="stButton"] button {
        background-color: #4CAF50 !important;
        color: white !important;
        border-color: #4CAF50 !important;
        font-weight: bold !important;
    }
    div[data-testid="stColumn"]:nth-child(2) div[data-testid="stButton"] button {
        background-color: #f44336 !important;
        color: white !important;
        border-color: #f44336 !important;
        font-weight: bold !important;
    }
    button[kind="primary"] {
        background-color: #00BFFF !important; 
        color: white !important;
        border-radius: 8px !important;
        height: 50px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        border: none !important;
    }
    button[kind="primary"]:hover {
        background-color: #009acd !important; 
        border-color: #009acd !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("💸 แอปรายรับ-รายจ่าย ประจำวัน (Puh)")

df = load_data()

# ==========================================
# ส่วนที่ 1: ระบบสั่งงานด้วยเสียง (Voice Magic Input)
# ==========================================
if 'pre_type' not in st.session_state: st.session_state.pre_type = "รายจ่าย 🔴"
if 'pre_cat' not in st.session_state: st.session_state.pre_cat = "🍜 ค่าอาหาร/เครื่องดื่ม"
if 'pre_chan' not in st.session_state: st.session_state.pre_chan = "💵 เงินสด"
if 'pre_amount' not in st.session_state: st.session_state.pre_amount = None
if 'pre_note' not in st.session_state: st.session_state.pre_note = ""
if 'form_reset' not in st.session_state: st.session_state.form_reset = 0

def clear_voice_text():
    if "voice_input_key" in st.session_state:
        st.session_state.voice_input_key = ""
    st.session_state.pre_amount = None
    st.session_state.pre_note = ""
    st.session_state.pre_type = "รายจ่าย 🔴"
    st.session_state.pre_cat = "🍜 ค่าอาหาร/เครื่องดื่ม"
    st.session_state.pre_chan = "💵 เงินสด"
    st.session_state.form_reset += 1 

st.markdown("### 🎙️ สั่งงานด้วยเสียง (Magic Input)")
st.info("💡 **วิธีใช้:** แตะช่องสีฟ้า กดไมค์ที่คีย์บอร์ดมือถือเพื่อพูด แล้วกดปุ่ม ✨ แยกคำ")

voice_input = st.text_input("ข้อความเสียง:", key="voice_input_key", placeholder="แตะที่นี่แล้วพูด... เช่น: ค่าอาหาร 150 บาท จ่ายด้วย Kbank")

col1, col2 = st.columns(2)
with col1:
    process_btn = st.button("✨ แยกคำ", use_container_width=True)
with col2:
    clear_btn = st.button("❌ ล้างคำ", use_container_width=True, on_click=clear_voice_text)

if process_btn and st.session_state.voice_input_key:
    text = st.session_state.voice_input_key.lower()
        
    if "หมายเหตุ" in text:
        parts = text.split("หมายเหตุ", 1)
        st.session_state.pre_note = parts[1].strip()
        text_to_search = parts[0] 
    else:
        st.session_state.pre_note = "" 
        text_to_search = text
        
    amounts = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', text_to_search)
    if amounts: 
        st.session_state.pre_amount = float(amounts[0].replace(',', ''))
    else:
        st.session_state.pre_amount = None
        
    is_income = False
    if any(word in text_to_search for word in ["คืนเงินสำรอง", "บริษัทคืน", "ได้เงินคืนจากบริษัท"]): 
        st.session_state.pre_cat = "💰 เงินคืนสำรองจ่ายจากบริษัท"
        is_income = True
    elif any(word in text_to_search for word in ["คืนเงิน", "cashback"]): 
        st.session_state.pre_cat = "💸 คืนเงิน/Cashback"
        is_income = True
    elif any(word in text_to_search for word in ["โบนัส", "เงินพิเศษ"]): 
        st.session_state.pre_cat = "🎁 โบนัส/เงินพิเศษ"
        is_income = True
    elif "เงินเดือน" in text_to_search: 
        st.session_state.pre_cat = "💼 เงินเดือน"
        is_income = True
    elif any(word in text_to_search for word in ["สำรอง", "บริษัท", "ออกให้ก่อน", "สำรองจ่าย"]): 
        st.session_state.pre_cat = "💰 เงินสำรองจ่ายบริษัท"
    elif any(word in text_to_search for word in ["เดินทาง", "รถ", "น้ำมัน", "ชาร์จ", "เรือ", "bts", "mrt"]): 
        st.session_state.pre_cat = "🚗 เดินทาง"
    elif any(word in text_to_search for word in ["อาหาร", "กิน", "ดื่ม", "ข้าว", "กาแฟ"]): 
        st.session_state.pre_cat = "🍜 ค่าอาหาร/เครื่องดื่ม"
    elif any(word in text_to_search for word in ["ช้อป", "ของใช้", "ซื้อ", "เซเว่น"]): 
        st.session_state.pre_cat = "🛍️ ช้อปปิ้ง/ของใช้"
    elif "ส่วนกลาง" in text_to_search: 
        st.session_state.pre_cat = "🐷 เงินเก็บส่วนกลาง"
    elif any(word in text_to_search for word in ["เรียน", "ลูก"]): 
        st.session_state.pre_cat = "🏫 ค่าเรียนลูก"
    else: 
        st.session_state.pre_cat = "📝 อื่นๆ"
        if "รายรับ" in text: is_income = True

    st.session_state.pre_type = "รายรับ 🟢" if is_income else "รายจ่าย 🔴"

    if any(word in text_to_search for word in ["kbank", "กสิกร", "เคแบงก์"]): st.session_state.pre_chan = "🟢 K-BANK"
    elif any(word in text_to_search for word in ["scb", "ไทยพาณิชย์"]): st.session_state.pre_chan = "🟣 SCB"
    elif any(word in text_to_search for word in ["กรุงเทพ", "bbl", "bangkok"]): st.session_state.pre_chan = "🦅 Bangkok-BANK"
    elif any(word in text_to_search for word in ["บัตร", "เครดิต", "credit"]): st.session_state.pre_chan = "💳 Credit Card"
    else: st.session_state.pre_chan = "💵 เงินสด"
        
    st.session_state.form_reset += 1 
    st.rerun()

st.markdown("---")

# ==========================================
# ส่วนที่ 2: ฟอร์มตรวจสอบและบันทึก
# ==========================================
st.markdown("### 📝 ตรวจสอบและบันทึกรายการ")

default_tourist = False
default_trip_name = "Japan 2026"
default_rate = None

if not df.empty:
    last_record_note = str(df.iloc[-1].get('หมายเหตุ', ''))
    if last_record_note.startswith("#"):
        default_tourist = True
        
        match_trip = re.search(r'^#(.+?)\s+\[', last_record_note)
        if match_trip:
            default_trip_name = match_trip.group(1).strip()
        else:
            default_trip_name = last_record_note.split(' ')[0][1:]
            
        match_rate = re.search(r'@([0-9.]+)]', last_record_note)
        if match_rate:
            try:
                default_rate = float(match_rate.group(1))
            except ValueError:
                default_rate = None

tourist_mode = st.toggle("✈️ โหมดนักท่องเที่ยว (แยกกระเป๋าทริป)", value=default_tourist)

type_index = 0 if st.session_state.pre_type == "รายจ่าย 🔴" else 1
type_ = st.radio("🔄 ประเภทรายการ", ["รายจ่าย 🔴", "รายรับ 🟢"], index=type_index, horizontal=True)

date = st.date_input("📅 วันที่ (วันทำรายการ)")

if tourist_mode:
    trip_name = st.text_input("🏷️ ชื่อทริป (เช่น Japan 2026)", value=default_trip_name)

if "รายจ่าย" in type_:
    category_options = ["🍜 ค่าอาหาร/เครื่องดื่ม", "🚗 เดินทาง", "🛍️ ช้อปปิ้ง/ของใช้", "💰 เงินสำรองจ่ายบริษัท", "🐷 เงินเก็บส่วนกลาง", "🏫 ค่าเรียนลูก", "📝 อื่นๆ"]
else:
    category_options = ["💼 เงินเดือน", "🎁 โบนัส/เงินพิเศษ", "💸 คืนเงิน/Cashback", "💰 เงินคืนสำรองจ่ายจากบริษัท", "📝 อื่นๆ"]
    
try: cat_idx = category_options.index(st.session_state.pre_cat)
except ValueError: cat_idx = 0
category = st.selectbox("🏷️ หมวดหมู่", category_options, index=cat_idx)

channel_options = ["💵 เงินสด", "🟢 K-BANK", "💳 Credit Card", "🟣 SCB", "🦅 Bangkok-BANK", "📝อื่นๆ"]
try: chan_idx = channel_options.index(st.session_state.pre_chan)
except ValueError: chan_idx = 0 
channel = st.radio("🏦 ช่องทาง", channel_options, index=chan_idx, horizontal=True)

payment_type = "จ่ายเต็ม"
installments = 1
if "รายจ่าย" in type_ and channel == "💳 Credit Card":
    st.markdown("💳 **รูปแบบการชำระบัตรเครดิต**")
    col_pay1, col_pay2 = st.columns(2)
    with col_pay1:
        payment_type = st.radio("เลือกรูปแบบ", ["จ่ายเต็ม", "ผ่อนชำระ"], horizontal=True, label_visibility="collapsed")
    with col_pay2:
        if payment_type == "ผ่อนชำระ":
            installments = st.selectbox("จำนวนงวด (เดือน)", [4, 6, 10], label_visibility="collapsed")

if tourist_mode:
    st.markdown("🎌 **ข้อมูลสกุลเงินต่างประเทศ**")
    col_curr, col_rate = st.columns(2)
    with col_curr: curr = st.selectbox("สกุลเงิน", ["JPY (เยน)", "USD (ดอลลาร์)"])
    with col_rate: rate = st.number_input("เรทแลกเปลี่ยน", value=default_rate, format="%.4f", step=0.0100)
    amount_input = st.number_input(f"💰 จำนวนเงิน ({curr.split(' ')[0]})", min_value=0.0, format="%.2f", step=100.0, value=st.session_state.pre_amount, placeholder="0.00", key=f"amt_{st.session_state.form_reset}")
else:
    amount_input = st.number_input("💰 จำนวนเงินทั้งหมด (บาท)", min_value=0.0, format="%.2f", step=100.0, value=st.session_state.pre_amount, placeholder="0.00", key=f"amt_{st.session_state.form_reset}")

note = st.text_input("📝 หมายเหตุ (ถ้ามี)", value=st.session_state.pre_note, placeholder="หมายเหตุ:", key=f"note_{st.session_state.form_reset}")

if st.button("บันทึกข้อมูลลงตาราง", type="primary", use_container_width=True):
    if amount_input is None or amount_input <= 0:
        st.error("⚠️ อย่าลืมใส่จำนวนเงินนะคะ!")
    elif tourist_mode and (rate is None or rate <= 0):
        st.error("⚠️ อย่าลืมใส่เรทแลกเปลี่ยนนะคะ!")
    else:
        if channel != "💳 Credit Card" or "รายรับ" in type_:
            payment_type = "จ่ายเต็ม"
            installments = 1

        if tourist_mode:
            final_thb_amount = amount_input * rate
            final_note = f"#{trip_name} [{curr.split(' ')[0]} {amount_input:,.2f} @{rate}] {note}".strip()
        else:
            final_thb_amount = amount_input
            final_note = note

        all_values = sheet.get_all_values()
        next_id = len(all_values)
        rows_to_append = []

        if payment_type == "ผ่อนชำระ" and channel == "💳 Credit Card" and "รายจ่าย" in type_:
            monthly_amt = final_thb_amount / installments
            inst_id = f"INST-{date.strftime('%Y%m%d')}-{next_id}" 
            for i in range(1, installments + 1):
                f_date = date.strftime("%Y-%m-%d")
                b_month = (pd.to_datetime(date) + pd.DateOffset(months=i)).strftime("%Y-%m")
                rows_to_append.append([
                    next_id + (i-1), f_date, category, "", monthly_amt, channel, final_note, 
                    "ผ่อนชำระ", installments, i, inst_id, b_month
                ])
            st.success(f"✅ บันทึกยอดผ่อนเดือนละ {monthly_amt:,.2f} บาท จำนวน {installments} งวด สำเร็จแล้วค่ะ!")
        elif channel == "💳 Credit Card" and "รายจ่าย" in type_:
            b_month = (pd.to_datetime(date) + pd.DateOffset(months=1)).strftime("%Y-%m")
            rows_to_append.append([
                next_id, date.strftime("%Y-%m-%d"), category, "", final_thb_amount, channel, final_note, 
                "จ่ายเต็ม", 1, 1, "", b_month
            ])
            st.success(f"✅ บันทึกยอด {final_thb_amount:,.2f} บาท (รูดบัตรเต็มจำนวน) สำเร็จแล้วค่ะ!")
        else:
            b_month = pd.to_datetime(date).strftime("%Y-%m")
            income_amt = final_thb_amount if "รายรับ" in type_ else ""
            expense_amt = final_thb_amount if "รายจ่าย" in type_ else ""
            rows_to_append.append([
                next_id, date.strftime("%Y-%m-%d"), category, income_amt, expense_amt, channel, final_note, 
                "จ่ายเต็ม", 1, 1, "", b_month
            ])
            st.success(f"✅ บันทึกยอด {final_thb_amount:,.2f} บาท สำเร็จแล้วค่ะ!")

        sheet.append_rows(rows_to_append)
        
        st.session_state.pre_amount = None
        st.session_state.pre_note = ""
        st.session_state.pre_type = "รายจ่าย 🔴"
        st.session_state.pre_cat = "🍜 ค่าอาหาร/เครื่องดื่ม"
        st.session_state.pre_chan = "💵 เงินสด"
        st.session_state.form_reset += 1 
        if "voice_input_key" in st.session_state: del st.session_state["voice_input_key"]
        
        st.rerun()

st.markdown("---")

# ==========================================
# ส่วนที่ 3: Dashboard & Cashflow Tabs
# ==========================================
st.markdown("### 📊 Dashboard วิเคราะห์ข้อมูล")

# 💡 ลอจิกใหม่: แสดงสวิตช์เฉพาะตอนอยู่โหมดนักท่องเที่ยวเท่านั้น
if tourist_mode:
    show_dashboard = st.toggle("📈 เปิดแสดงผล Dashboard (ประหยัดอินเทอร์เน็ต)", value=False)
else:
    show_dashboard = True # โหมดปกติ บังคับเปิด Dashboard ค้างไว้เลย

if show_dashboard:
    if not df.empty:
        df['รายรับ'] = pd.to_numeric(df['รายรับ'].replace('', 0, regex=True))
        df['รายจ่าย'] = pd.to_numeric(df['รายจ่าย'].replace('', 0, regex=True))
        df['วันที่'] = pd.to_datetime(df['วันที่'])
        df['เดือน-ปี'] = df['วันที่'].dt.strftime('%Y-%m')
        df['เดือนที่จ่ายบิล'] = df['เดือนที่จ่ายบิล'].replace('', pd.NA).fillna(df['เดือน-ปี'])
        
        if tourist_mode:
            df['หมายเหตุ'] = df['หมายเหตุ'].fillna('')
            st.markdown("#### ✈️ สรุปค่าใช้จ่ายแยกตามทริป")
            trip_search = st.text_input("พิมพ์ชื่อทริปที่ต้องการดู:", value=default_trip_name)
            f_df = df[df['หมายเหตุ'].str.contains(f"#{trip_search}", na=False)]
            
            if not f_df.empty:
                st.error(f"**รายจ่ายรวมทริป:**\n## ฿ {f_df['รายจ่าย'].sum():,.2f}")
                
                st.markdown("##### 🍩 สัดส่วนค่าใช้จ่ายในทริปนี้")
                cat_expense = f_df[f_df['รายจ่าย'] > 0].groupby('รายการ', as_index=False)['รายจ่าย'].sum()
                fig_pie = px.pie(cat_expense, values='รายจ่าย', names='รายการ', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label', insidetextorientation='horizontal')
                fig_pie.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_pie, use_container_width=True)

                st.markdown("##### 📈 ยอดใช้จ่ายรายวัน")
                exp_only = f_df[f_df['รายจ่าย'] > 0].copy()
                if not exp_only.empty:
                    exp_only['วันที่_format'] = exp_only['วันที่'].dt.strftime('%Y-%m-%d')
                    daily_expense = exp_only.groupby('วันที่_format', as_index=False)['รายจ่าย'].sum()
                    
                    fig_line = px.line(daily_expense, x='วันที่_format', y='รายจ่าย', markers=True, text='รายจ่าย')
                    fig_line.update_traces(textposition="top center", texttemplate='%{text:,.0f}')
                    fig_line.update_layout(margin=dict(t=10, b=10, l=10, r=10), xaxis_title="วันที่", yaxis_title="ยอดเงิน (บาท)")
                    st.plotly_chart(fig_line, use_container_width=True)
                
                with st.expander("เปิดดูรายการทั้งหมดของทริปนี้"):
                    st.dataframe(f_df[['วันที่', 'รายการ', 'รายจ่าย', 'ช่องทาง', 'หมายเหตุ']].sort_values(by='วันที่', ascending=False), use_container_width=True)
            else:
                st.info("ยังไม่มีข้อมูลบันทึกสำหรับทริปนี้ค่ะ")
        else:
            months_list = ["ดูทั้งหมด"] + sorted(df['เดือน-ปี'].unique().tolist(), reverse=True)
            current_m_str = pd.Timestamp.today().strftime('%Y-%m')
            try: default_index = months_list.index(current_m_str)
            except ValueError: default_index = 0 if len(months_list) == 1 else 1 
                
            sel_m = st.selectbox("📅 เลือกเดือนที่ต้องการดูข้อมูล:", months_list, index=default_index)
            
            f_df = df if sel_m == "ดูทั้งหมด" else df[df['เดือน-ปี'] == sel_m]
            total_income = f_df['รายรับ'].sum()
            total_expense = f_df['รายจ่าย'].sum()
            balance = total_income - total_expense
            
            tab1, tab2 = st.tabs(["📊 Dashboard หลัก", "💵 Cashflow (เงินสดจริง)"])

            with tab1:
                col1, col2 = st.columns(2)
                col1.success(f"**รายรับรวม:**\n### ฿ {total_income:,.2f}")
                col2.error(f"**รายจ่ายรวม:**\n### ฿ {total_expense:,.2f}")
                st.info(f"**ยอดคงเหลือ (ทางบัญชี):**\n## ฿ {balance:,.2f}")
                
                cc_expense_this_m = f_df[f_df['ช่องทาง'] == '💳 Credit Card']['รายจ่าย'].sum()
                st.markdown(f"""
                <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-left: 5px solid #64748b; padding: 15px; border-radius: 10px; margin-top: 10px; margin-bottom: 20px;">
                    <p style="margin:0; color: #475569; font-size: 16px;">💳 ยอดใช้จ่ายผ่านบัตรเครดิต (รูดก่อหนี้ในเดือนนี้)</p>
                    <h3 style="margin:0; color: #0f172a;">฿ {cc_expense_this_m:,.2f}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                advance_company = f_df[f_df['รายการ'] == '💰 เงินสำรองจ่ายบริษัท']['รายจ่าย'].sum()
                refund_company = f_df[f_df['รายการ'] == '💰 เงินคืนสำรองจ่ายจากบริษัท']['รายรับ'].sum()
                remain_advance = advance_company - refund_company

                st.markdown(f"""
                <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-left: 5px solid #64748b; padding: 15px; border-radius: 10px; margin-top: 10px; margin-bottom: 20px;">
                    <p style="margin:0; color: #475569; font-size: 16px;">🏢 เงินสำรองจ่ายบริษัท</p>
                    <h3 style="margin:0; color: #0f172a;">ยอดสำรองจ่าย: ฿ {advance_company:,.2f}</h3>
                    <h3 style="margin:0; color: #0f172a;">ยอดคืนเงิน: ฿ {refund_company:,.2f}</h3>
                    <h3 style="margin:0; color: #b91c1c;">ยอดค้างจ่ายจากบริษัท: ฿ {remain_advance:,.2f}</h3>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("#### 🏆 วิเคราะห์หมวดหมู่การใช้จ่าย")
                expense_df = f_df[f_df['รายจ่าย'] > 0]
                if not expense_df.empty:
                    cat_expense = expense_df.groupby('รายการ', as_index=False)['รายจ่าย'].sum().sort_values(by='รายจ่าย', ascending=False)
                    top_cat = cat_expense.iloc[0]['รายการ']
                    top_amt = cat_expense.iloc[0]['รายจ่าย']
                    st.warning(f"🥇 **จ่ายหนักสุดในหมวด:** {top_cat} (฿ {top_amt:,.2f})")
                    fig = px.pie(cat_expense, values='รายจ่าย', names='รายการ', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig.update_traces(textposition='inside', textinfo='percent+label', insidetextorientation='horizontal')
                    fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.write("ยังไม่มีรายจ่ายในเดือนนี้ค่ะ")
                with st.expander("เปิดดูประวัติรายการทั้งหมด"):
                    cols_to_show = ['วันที่', 'รายการ', 'รายรับ', 'รายจ่าย', 'ช่องทาง', 'หมายเหตุ']
                    st.dataframe(f_df[cols_to_show].sort_values(by='วันที่', ascending=False), use_container_width=True)

            with tab2:
                if sel_m != "ดูทั้งหมด":
                    true_cash = balance + cc_expense_this_m
                    actual_cc_bill_df = df[(df['เดือนที่จ่ายบิล'] == sel_m) & (df['ช่องทาง'] == '💳 Credit Card')]
                    cc_full_bill = actual_cc_bill_df[actual_cc_bill_df['ประเภทการจ่าย'] == 'จ่ายเต็ม']['รายจ่าย'].sum()
                    cc_inst_bill = actual_cc_bill_df[actual_cc_bill_df['ประเภทการจ่าย'] == 'ผ่อนชำระ']['รายจ่าย'].sum()
                    actual_cc_bill = cc_full_bill + cc_inst_bill
                    real_cashflow = true_cash - actual_cc_bill
                    st.markdown(f"#### 💵 กระแสเงินสดสุทธิ (Cashflow) ประจำเดือน {sel_m}")
                    st.info(f"**💰 เงินสดที่แท้จริงในมือ (ก่อนจ่ายบัตร):**\n## ฿ {true_cash:,.2f}\n*(ยอดคงเหลือทางบัญชี ฿{balance:,.2f} + เงินสดที่ยังไม่ออกเพราะรูดบัตร ฿{cc_expense_this_m:,.2f})*")
                    st.markdown(f"""
                    <div style="background-color: #fff1f2; border: 1px solid #fda4af; border-left: 5px solid #e11d48; padding: 15px; border-radius: 10px; margin-bottom: 15px; margin-top: 15px;">
                        <p style="margin:0; color: #881337; font-size: 16px;">💳 ลบยอดบัตรเครดิตที่ต้องชำระรอบบิลนี้</p>
                        <h2 style="margin:0; color: #9f1239;">- ฿ {actual_cc_bill:,.2f}</h2>
                        <p style="margin:0; color: #881337; font-size: 14px;">(ยอดรูดเต็มรอบก่อน ฿ {cc_full_bill:,.2f} + ยอดผ่อนรอบนี้ ฿ {cc_inst_bill:,.2f})</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.success(f"**✨ Cashflow เงินสดคงเหลือจริงๆ:**\n## ฿ {real_cashflow:,.2f}")
                    if not actual_cc_bill_df.empty:
                        with st.expander("🧾 ดูรายละเอียดบิลบัตรเครดิตที่เรียกเก็บเดือนนี้"):
                            st.dataframe(actual_cc_bill_df[['วันที่', 'รายการ', 'รายจ่าย', 'ประเภทการจ่าย', 'งวดปัจจุบัน', 'หมายเหตุ']].sort_values(by='วันที่'), use_container_width=True)
                else: st.warning("⚠️ กรุณาเลือกเดือนที่ต้องการดู Cashflow ค่ะ")
    else:
        st.info("ยังไม่มีข้อมูลเลยค่ะ ลองบันทึกรายการแรกดูนะคะ!")
else:
    st.caption("ℹ️ Dashboard ถูกซ่อนไว้เพื่อความรวดเร็วและประหยัดอินเทอร์เน็ตค่ะ")
