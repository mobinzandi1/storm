import streamlit as st
import pandas as pd
import plotly.express as px
import os
import base64
from smart_reconciliation_system import SmartReconciliationSystem
from PIL import Image
# این تابع را در بالای فایل app.py (بعد از imports) اضافه کنید

def fix_dataframe_for_streamlit(df):
    """
    آماده‌سازی دیتافریم برای نمایش در Streamlit با اصلاح ستون‌های تکراری
    """
    import pandas as pd
    
    if df is None or df.empty:
        return pd.DataFrame()
        
    # کپی از دیتافریم
    df_fixed = df.copy()
    
    # تبدیل تمام نام‌های ستون به رشته
    columns = [str(col) for col in df_fixed.columns]
    
    # بررسی ستون‌های تکراری
    if len(columns) != len(set(columns)):
        # ایجاد نام‌های ستون یکتا
        new_columns = []
        seen = set()
        for col in columns:
            if col in seen:
                i = 1
                new_col = f"{col}_{i}"
                while new_col in seen:
                    i += 1
                    new_col = f"{col}_{i}"
                new_columns.append(new_col)
                seen.add(new_col)
            else:
                new_columns.append(col)
                seen.add(col)
        
        # اعمال نام‌های جدید
        df_fixed.columns = new_columns
    
    return df_fixed
# تنظیم پیکربندی صفحه با لوگوی WALLEX
st.set_page_config(
    page_title="سیستم مغایرت‌گیری هوشمند ",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="💸"
)

# بارگذاری لوگوی WALLEX
try:
    # بارگذاری لوگو با مسیر نسبی
    logo_path = "assets/wallex_logo.png"
    logo = Image.open(logo_path)
    st.image(logo, width=200)
except Exception as e:
    st.warning(f"خطا در بارگذاری لوگو: {str(e)}")
    # ادامه اجرای برنامه بدون لوگو

# CSS پیشرفته برای رابط کاربری فوق‌العاده زیبا و مدرن با تم WALLEX
st.markdown("""
<style>
    /* تنظیمات عمومی برای تمام متن‌ها - رنگ آبی تیره WALLEX */
    .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp span, .stApp div, .stApp a {
        color: #2c3e50; /* آبی تیره برای کنتراست بالا */
    }
    
    /* فونت وزیر برای متون فارسی */
    @font-face {
        font-family: 'Vazir';
        src: url('https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v27.2.2/dist/Vazir-Regular.woff2') format('woff2');
        font-weight: normal;
        font-style: normal;
    }
    
    @font-face {
        font-family: 'Vazir';
        src: url('https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v27.2.2/dist/Vazir-Bold.woff2') format('woff2');
        font-weight: bold;
        font-style: normal;
    }
    
    * {
        font-family: 'Vazir', sans-serif;
    }
    
    .rtl {
        direction: rtl;
        text-align: right;
    }
    
    /* پس‌زمینه گرادیانی با تم WALLEX و کمی قرمز */
    .stApp {
        background: linear-gradient(135deg, #3498db 0%, #2c3e50 50%, #e74c3c 100%);
        background-size: 400% 400%;
        animation: gradientBG 15s ease infinite;
    }
    
    @keyframes gradientBG {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* هدر اصلی با لوگوی WALLEX و انیمیشن */
    .main-header {
        background: linear-gradient(90deg, #3498db 0%, #2c3e50 100%);
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
        margin-bottom: 2.5rem;
        text-align: center;
        animation: fadeInUp 1s ease-out;
    }
    
    .main-header h1 {
        color: white !important;
        text-shadow: 2px 2px 6px rgba(0, 0, 0, 0.3);
        font-size: 2.5rem;
        font-weight: bold;
    }
    
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* کارت‌ها با افکت‌های سه‌بعدی و هاور پویا */
    .card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1), 0 4px 10px rgba(0, 0, 0, 0.05);
        margin-bottom: 2rem;
        transition: transform 0.4s ease, box-shadow 0.4s ease;
        backdrop-filter: blur(5px);
    }
    
    .card:hover {
        transform: translateY(-6px) rotateX(5deg) rotateY(5deg);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15), 0 6px 15px rgba(0, 0, 0, 0.08);
    }
    
    /* هدر بخش‌ها با خط تزئینی گرادیانی */
    .section-header {
        color: #2c3e50 !important;
        border-right: 6px solid transparent;
        background: linear-gradient(90deg, #3498db, #2c3e50);
        -webkit-background-clip: text;
        background-clip: text;
        padding-right: 14px;
        margin-bottom: 1.5rem;
        padding-top: 8px;
        padding-bottom: 8px;
        font-weight: bold;
        font-size: 1.5rem;
    }
    
    /* دکمه‌های زیبا با گرادیان WALLEX و افکت‌های پویا */
    .stButton>button {
        background: linear-gradient(90deg, #3498db 0%, #2c3e50 100%);
        border: none;
        border-radius: 15px;
        padding: 1rem 2rem;
        font-weight: bold;
        font-size: 1.2rem;
        transition: all 0.4s ease;
        position: relative;
        overflow: hidden;
    }
    
    .stButton>button span {
        color: white !important;
        font-weight: bold;
        position: relative;
        z-index: 2;
    }
    
    .stButton>button:hover {
        transform: scale(1.08);
        box-shadow: 0 8px 25px rgba(52, 152, 219, 0.4);
    }
    
    .stButton>button::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 15px;
        transform: scale(0);
        transition: transform 0.4s ease;
        z-index: 1;
    }
    
    .stButton>button:hover::after {
        transform: scale(1);
    }
    
    /* کارت‌های متریک با افکت‌های سه‌بعدی */
    .metric-card {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 20px;
        padding: 1.5rem;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1), 0 4px 10px rgba(0, 0, 0, 0.05);
        text-align: center;
        transition: transform 0.4s ease;
        backdrop-filter: blur(5px);
    }
    
    .metric-card:hover {
        transform: translateY(-6px) rotateX(5deg);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2c3e50 !important;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    .metric-label {
        color: #7f8c8d !important;
        font-size: 1.1rem;
        font-weight: bold;
    }
    
    /* تب‌ها با انیمیشن پویا */
    .stTabs [data-baseweb="tab-list"] {
        gap: 3px;
        background: rgba(255, 255, 255, 0.8);
        border-radius: 15px;
        padding: 5px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.7);
        border-radius: 12px;
        padding: 14px 28px;
        border: none;
        transition: all 0.3s ease;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(255, 255, 255, 0.9);
        transform: translateY(-2px);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #3498db, #2c3e50);
        color: white !important;
    }
    
    .stTabs [aria-selected="true"] p {
        color: white !important;
        font-weight: bold;
    }
    
    /* دکمه دانلود با استایل منحصربه‌فرد */
    .download-button {
        background: linear-gradient(90deg, #e74c3c 0%, #f1c40f 100%);
        color: white !important;
        border: none;
        border-radius: 20px;
        padding: 0.8rem 1.8rem;
        font-weight: bold;
        font-size: 1.1rem;
        transition: all 0.4s ease;
        position: relative;
        overflow: hidden;
    }
    
    .download-button:hover {
        transform: scale(1.06);
        box-shadow: 0 8px 25px rgba(231, 76, 60, 0.4);
    }
    
    .download-button::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.3);
        border-radius: 20px;
        transform: scale(0);
        transition: transform 0.4s ease;
    }
    
    .download-button:hover::after {
        transform: scale(1);
    }
    
    /* کانتینر آپلودر فایل با انیمیشن ذره‌ای */
    .uploader-container {
        border: 2px dashed #3498db;
        border-radius: 20px;
        padding: 2.5rem;
        text-align: center;
        transition: all 0.4s ease;
        background: rgba(255, 255, 255, 0.9);
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(5px);
    }
    
    .uploader-container:hover {
        border-color: #2c3e50;
        box-shadow: 0 8px 25px rgba(52, 152, 219, 0.2);
    }
    
    .uploader-container::before {
        content: '';
        position: absolute;
        width: 100px;
        height: 100px;
        background: rgba(52, 152, 219, 0.1);
        border-radius: 50%;
        animation: float 6s infinite ease-in-out;
        top: -50px;
        left: -50px;
    }
    
    @keyframes float {
        0% { transform: translate(0, 0); }
        50% { transform: translate(100px, 100px); }
        100% { transform: translate(0, 0); }
    }
    
    [data-testid="stFileUploader"] label, 
    [data-testid="stFileUploader"] p, 
    [data-testid="stFileUploader"] span, 
    [data-testid="stFileUploader"] div {
        color: #2c3e50;
        font-weight: bold;
    }
    
    /* استایل برای کامپوننت‌های Streamlit */
    .stSelectbox label, .stRadio label {
        color: #2c3e50;
        font-weight: bold;
    }
    
    .stSelectbox>div>div {
        background-color: rgba(255, 255, 255, 0.9);
        border-radius: 15px;
        border: 1px solid #e9ecef;
        color: #2c3e50;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
    }
    
    /* استایل برای اسلایدر */
    .stSlider label, .stSlider div {
        color: #2c3e50;
        font-weight: bold;
    }
    
    .stSlider>div>div {
        background-color: #3498db;
    }
    
    /* استایل برای اکسپندر راهنما */
    .help-expander {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 20px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(5px);
    }
    
    /* فوتر با انیمیشن ملایم */
    .footer {
        margin-top: 3.5rem;
        text-align: center;
        padding: 1.5rem;
        background: rgba(255, 255, 255, 0.8);
        border-radius: 20px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        animation: fadeIn 1.5s ease-out;
    }
    
    /* استایل برای وضعیت‌های مختلف با افکت ذره‌ای */
    .success, .warning, .error, .info {
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1.5rem 0;
        position: relative;
        overflow: hidden;
    }
    
    .success {
        background: linear-gradient(90deg, #27ae60 0%, #2ecc71 100%);
    }
    
    .success::after {
        content: '';
        position: absolute;
        width: 10px;
        height: 10px;
        background: rgba(255, 255, 255, 0.5);
        border-radius: 50%;
        animation: confetti 3s infinite ease-out;
        top: -5px;
        left: -5px;
    }
    
    .warning {
        background: linear-gradient(90deg, #f1c40f 0%, #f39c12 100%);
    }
    
    .error {
        background: linear-gradient(90deg, #e74c3c 0%, #c0392b 100%);
    }
    
    .info {
        background: linear-gradient(90deg, #3498db 0%, #2c3e50 100%);
    }
    
    .success h4, .success p, .success li,
    .warning h4, .warning p, .warning li,
    .error h4, .error p, .error li,
    .info h4, .info p, .info li {
        color: white !important;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.2);
        position: relative;
        z-index: 2;
    }
    
    @keyframes confetti {
        0% { transform: translate(0, 0) scale(0); opacity: 0; }
        50% { transform: translate(100px, 100px) scale(1); opacity: 1; }
        100% { transform: translate(200px, 200px) scale(0); opacity: 0; }
    }
    
    /* استایل برای تگ‌های ستون */
    .column-tag {
        display: inline-block;
        background: linear-gradient(45deg, #3498db, #2c3e50);
        color: white !important;
        padding: 8px 16px;
        margin: 5px;
        border-radius: 25px;
        font-size: 1rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transition: all 0.4s ease;
        animation: bounce 0.5s ease-out;
    }
    
    .column-tag:hover {
        transform: translateY(-4px) scale(1.05);
        box-shadow: 0 6px 18px rgba(0,0,0,0.15);
    }
    
    @keyframes bounce {
        0% { transform: scale(0.9); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    
    /* استایل برای آیکون‌های گیت‌وی */
    .gateway-icon {
        background: linear-gradient(90deg, #3498db 0%, #2c3e50 100%);
        color: white !important;
        padding: 8px 18px;
        border-radius: 30px;
        font-weight: bold;
        display: inline-block;
        margin-top: 15px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.1);
        transition: all 0.4s ease;
        animation: rotateIn 0.8s ease-out;
    }
    
    .gateway-icon:hover {
        transform: translateY(-4px) rotate(5deg);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    
    @keyframes rotateIn {
        from { transform: rotate(-10deg) scale(0.9); opacity: 0; }
        to { transform: rotate(0deg) scale(1); opacity: 1; }
    }
    
    /* استایل برای توضیحات تکمیلی */
    .tip-box {
        margin-top: 25px;
        padding: 18px;
        background: rgba(255, 255, 255, 0.9);
        border-right: 6px solid #3498db;
        border-radius: 15px;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(5px);
    }
    
    .tip-box b, .tip-box p, .tip-box li {
        color: #2c3e50 !important;
        font-weight: bold;
    }
    
    /* استایل نوار پیشرفت با انیمیشن ذره‌ای */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #3498db, #2c3e50);
        position: relative;
    }
    
    .stProgress > div > div > div > div::after {
        content: '';
        position: absolute;
        width: 5px;
        height: 5px;
        background: white;
        border-radius: 50%;
        animation: moveDot 2s infinite linear;
        top: 50%;
        left: 0;
    }
    
    @keyframes moveDot {
        0% { left: 0; }
        100% { left: 100%; }
    }
    
    /* استایل برای لیبل‌ها و فرم‌ها */
    label {
        color: #2c3e50;
        font-weight: bold;
        font-size: 1.2rem;
    }
    
    .help-text {
        color: #7f8c8d;
        font-size: 1.1rem;
        margin-top: 8px;
    }
    
    /* استایل برای رادیو باتن‌ها */
    .stRadio label[data-baseweb="radio"] span {
        border-color: #3498db !important;
    }
    
    .stRadio [data-baseweb="radio"][aria-checked="true"] span::before {
        background-color: #3498db !important;
    }
    
    .stRadio [data-baseweb="radio"] span {
        box-shadow: none !important;
    }
    
    /* تنظیم رنگ متن برای منوهای کشویی */
    .stSelectbox div[data-baseweb="select"] span {
        color: #2c3e50 !important;
    }

    .stSelectbox ul li, 
    .stSelectbox [data-baseweb="select"] [aria-selected="true"],
    .stSelectbox [data-baseweb="menu"] [role="option"],
    .css-kiejdm-menu, 
    .css-kiejdm-menu *,
    .css-1n76uvr-option,
    .css-yt9ioa-option {
        color: white !important;
    }
    
    .stSelectbox [data-baseweb="popover"],
    .stSelectbox [data-baseweb="menu"] {
        background: linear-gradient(135deg, #3498db, #2c3e50);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
    }
    
    .stSelectbox [data-baseweb="menu"] [role="option"]:hover {
        background: rgba(255, 255, 255, 0.2) !important;
        color: white !important;
    }
    
    /* تنظیم رنگ متن برای المنت‌های تیره */
    .main-header h1, 
    .gateway-icon, 
    .column-tag, 
    .success h4, .success p, .success li,
    .warning h4, .warning p, .warning li,
    .error h4, .error p, .error li,
    .info h4, .info p, .info li,
    .stButton>button span,
    .download-excel-button span {
        color: white !important;
    }
    
    .download-excel-button, .download-excel-button * {
        color: white !important;
    }
    
    svg text, .plotly-graph-div text {
        fill: #2c3e50 !important;
    }
    
    .dataframe th, .dataframe td {
        color: #2c3e50 !important;
    }
    
    /* استایل برای پیام موفقیت با افکت کنفتی */
    .success-message {
        background: linear-gradient(to right, rgba(39, 174, 96, 0.1), rgba(46, 204, 113, 0.1));
        border-right: 6px solid #27ae60;
        padding: 25px;
        border-radius: 15px;
        margin: 25px 0;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        position: relative;
    }
    
    .success-message::after {
        content: '';
        position: absolute;
        width: 5px;
        height: 5px;
        background: rgba(255, 255, 255, 0.5);
        border-radius: 50%;
        animation: confetti 3s infinite ease-out;
        top: 10px;
        left: 10px;
    }
    
    .success-icon {
        font-size: 60px;
        color: #27ae60;
        margin-bottom: 15px;
        animation: bounce 1s ease-out infinite;
    }
    
    /* لودر زیبا با افکت ذره‌ای */
    .elegant-loader {
        display: inline-block;
        width: 80px;
        height: 80px;
        border: 4px solid rgba(52, 152, 219, 0.3);
        border-radius: 50%;
        border-top-color: #3498db;
        animation: spin 1.5s ease-in-out infinite;
        position: relative;
    }
    
    .elegant-loader::after {
        content: '';
        position: absolute;
        width: 10px;
        height: 10px;
        background: white;
        border-radius: 50%;
        animation: orbit 2s infinite linear;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    @keyframes orbit {
        0% { transform: translate(-50%, -50%) rotate(0deg); }
        100% { transform: translate(-50%, -50%) rotate(360deg); }
    }
</style>
""", unsafe_allow_html=True)

# هدر اصلی با لوگوی WALLEX و انیمیشن
st.markdown('<div class="main-header animated"><h1>سیستم مغایرت‌گیری هوشمند </h1></div>', unsafe_allow_html=True)

# بارگذاری سیستم مغایرت‌گیری
@st.cache_resource
def load_system():
    return SmartReconciliationSystem()

system = load_system()

# بخش بارگذاری فایل‌ها با رابط کاربری زیبا
st.markdown('<div class="card animated"><h2 class="section-header rtl">بارگذاری فایل‌ها</h2>', unsafe_allow_html=True)

st.markdown("""
<div class="rtl info" style="margin-bottom: 25px;">
    <h4>📋 راهنمای بارگذاری فایل‌ها</h4>
    <p>فایل‌های پلتفرم و ارائه‌دهنده را با فرمت‌های CSV، Excel یا JSON بارگذاری کنید. فایل‌ها باید شامل ستون‌های کد رهگیری باشند.</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="uploader-container rtl">
        <div style="text-align: center; margin-bottom: 20px;">
            <span style="font-size: 3rem;" class="fas fa-chart-pie"></span>
        </div>
        <h3 style="text-align: center; color: #2c3e50; margin-bottom: 25px;">فایل پلتفرم</h3>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background: rgba(255, 255, 255, 0.8); padding: 15px; border-radius: 15px; margin-bottom: 15px; text-align: right; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);">
        <p style="color: #2c3e50; font-weight: bold; margin-bottom: 8px;">ساختار پیشنهادی:</p>
        <span style="color: #2c3e50; font-family: monospace; font-size: 1rem;">gateway_tracking_code, amount, date, status, ...</span>
    </div>
    """, unsafe_allow_html=True)
    
    platform_file = st.file_uploader("انتخاب فایل پلتفرم", type=["csv", "xlsx", "json"], key="platform_file")
    
    if platform_file is None:
        st.markdown("""
        <div style="text-align: center; margin-top: 20px;">
            <p style="color: #2c3e50; font-weight: bold;">
                <i class="fas fa-cloud-upload-alt" style="margin-left: 12px;"></i>
                فایل پلتفرم را بارگذاری کنید
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        file_ext = platform_file.name.split('.')[-1].lower()
        file_icon = "📄"
        if file_ext == 'csv':
            file_icon = '<i class="fas fa-table"></i>'
        elif file_ext in ['xlsx', 'xls']:
            file_icon = '<i class="fas fa-file-excel"></i>'
        elif file_ext == 'json':
            file_icon = '<i class="fas fa-file-code"></i>'
            
        st.markdown(f"""
        <div style="background: rgba(39, 174, 96, 0.1); border-radius: 15px; padding: 15px; margin-top: 20px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);">
            <div style="display: flex; align-items: center; justify-content: center;">
                <span style="font-size: 1.8rem; margin-left: 12px;">{file_icon}</span>
                <div>
                    <p style="color: #27ae60; font-weight: bold; margin: 0;">فایل با موفقیت بارگذاری شد</p>
                    <p style="color: #27ae60; font-size: 1rem; margin: 0;">{platform_file.name}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="uploader-container rtl">
        <div style="text-align: center; margin-bottom: 20px;">
            <span style="font-size: 3rem;" class="fas fa-file-alt"></span>
        </div>
        <h3 style="text-align: center; color: #2c3e50; margin-bottom: 25px;">فایل ارائه‌دهنده (Provider)</h3>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background: rgba(255, 255, 255, 0.8); padding: 15px; border-radius: 15px; margin-bottom: 15px; text-align: right; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);">
        <p style="color: #2c3e50; font-weight: bold; margin-bottom: 8px;">ساختار پیشنهادی:</p>
        <span style="color: #2c3e50; font-family: monospace; font-size: 1rem;">tracking_id, amount, reference, timestamp, ...</span>
    </div>
    """, unsafe_allow_html=True)
    
    provider_file = st.file_uploader("انتخاب فایل ارائه‌دهنده", type=["csv", "xlsx", "json"], key="provider_file")
    
    if provider_file is None:
        st.markdown("""
        <div style="text-align: center; margin-top: 20px;">
            <p style="color: #2c3e50; font-weight: bold;">
                <i class="fas fa-cloud-upload-alt" style="margin-left: 12px;"></i>
                فایل ارائه‌دهنده را بارگذاری کنید
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        file_ext = provider_file.name.split('.')[-1].lower()
        file_icon = "📄"
        if file_ext == 'csv':
            file_icon = '<i class="fas fa-table"></i>'
        elif file_ext in ['xlsx', 'xls']:
            file_icon = '<i class="fas fa-file-excel"></i>'
        elif file_ext == 'json':
            file_icon = '<i class="fas fa-file-code"></i>'
            
        st.markdown(f"""
        <div style="background: rgba(39, 174, 96, 0.1); border-radius: 15px; padding: 15px; margin-top: 20px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);">
            <div style="display: flex; align-items: center; justify-content: center;">
                <span style="font-size: 1.8rem; margin-left: 12px;">{file_icon}</span>
                <div>
                    <p style="color: #27ae60; font-weight: bold; margin: 0;">فایل با موفقیت بارگذاری شد</p>
                    <p style="color: #27ae60; font-size: 1rem; margin: 0;">{provider_file.name}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# انتخاب ارائه‌دهنده (Gateway)
st.markdown('<div class="card animated"><h2 class="section-header rtl">انتخاب ارائه‌دهنده (Gateway)</h2>', unsafe_allow_html=True)

# لیست گزینه‌ها
gateway_options = ['Payman', 'jibitcobank', 'ezpay', 'toman', 'vandar', 'jibit']

# دیکشنری ایموجی‌ها
gateway_icons = {
    'Payman': '💳',
    'jibitcobank': '🏫',
    'ezpay': '💸',
    'toman': '🪙',
    'vandar': '$',
    'jibit': '¥'
}

# نمایش گزینه‌ها در selectbox
st.markdown('<p class="rtl" style="font-weight: bold; color: #2c3e50;">ارائه‌دهنده مورد نظر را انتخاب کنید:</p>', unsafe_allow_html=True)
gateway_options_with_icons = [f"{gateway_icons.get(gateway, '💳')} {gateway}" for gateway in gateway_options]
selected_option = st.selectbox("", gateway_options_with_icons, format_func=lambda x: x.split(' ', 1)[1])
selected_gateway = selected_option.split(' ', 1)[1]

# نمایش Gateway انتخاب‌شده با ایموجی
st.markdown(f'<div style="text-align: center;"><span style="font-size: 2rem;">{gateway_icons.get(selected_gateway, "💳")}</span> {selected_gateway}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# تنظیمات مغایرت‌گیری
st.markdown('<div class="card animated"><h2 class="section-header rtl">تنظیمات مغایرت‌گیری</h2>', unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    st.markdown('<p class="rtl" style="font-weight: bold; color: #2c3e50;">نوع مقایسه:</p>', unsafe_allow_html=True)
    comparison_type = st.radio(
        "نوع مقایسه",
        ["تطبیق دقیق", "تطبیق فازی (تشابه)"],
        index=0,
        horizontal=True,
        key="comparison_type",
        label_visibility="collapsed"
    )
    
    if comparison_type == "تطبیق دقیق":
        st.info("کدهای رهگیری باید دقیقاً یکسان باشند.")
    else:
        st.markdown('<p class="rtl" style="font-weight: bold; color: #2c3e50;">آستانه شباهت (%):</p>', unsafe_allow_html=True)
        similarity_threshold = st.slider("آستانه شباهت", 50, 100, 85, key="similarity_slider")
        
        # تنظیم ستون‌ها برای نوار پیشرفت و درصد
        col_progress, col_percent = st.columns([3, 1])
        with col_progress:
            st.progress(similarity_threshold / 100)
        with col_percent:
            st.markdown(
                f'<div style="background: linear-gradient(90deg, #3498db, #2c3e50); color: white; text-align: center; padding: 12px; border-radius: 15px; font-weight: bold; font-size: 1.3rem; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);">{similarity_threshold}%</div>',
                unsafe_allow_html=True
            )
        
        # نمایش راهنمای آستانه
        st.markdown("""
        <div style="display: flex; justify-content: space-between; margin-top: 10px; margin-bottom: 15px;">
            <div style="text-align: right;">
                <span style="color: #2c3e50; font-weight: bold;">50%</span>
                <div style="font-size: 1rem; color: #7f8c8d;">تطابق‌های نادرست</div>
            </div>
            <div style="text-align: center;">
                <span style="color: #2c3e50; font-weight: bold;">75%</span>
                <div style="font-size: 1rem; color: #7f8c8d;">تعادل</div>
            </div>
            <div style="text-align: left;">
                <span style="color: #2c3e50; font-weight: bold;">100%</span>
                <div style="font-size: 1rem; color: #7f8c8d;">دقت بالا</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # پیام‌های هشدار
        if similarity_threshold < 70:
            st.warning("⚠️ هشدار: آستانه کمتر از 70٪ - ممکن است منجر به تطابق‌های نادرست شود.")
        elif similarity_threshold > 95:
            st.error("⚠️ هشدار: آستانه بیشتر از 95٪ - ممکن است رکوردهای مشابه معتبر را نادیده بگیرد.")
        else:
            st.success("✅ آستانه مناسب - آستانه انتخاب شده در محدوده مناسب قرار دارد.")

with col2:
    st.markdown('<p class="rtl" style="font-weight: bold; color: #2c3e50;">ستون‌های کلیدی پلتفرم:</p>', unsafe_allow_html=True)
    
    default_column_list = system.platform_tracking_columns
    selected_columns = st.multiselect(
        "ستون‌های حاوی کد رهگیری",
        options=["gateway_tracking_code", "gateway_identifier", "meta_data_1", "tracking_id", "transaction_id", "reference_code"],
        default=default_column_list,
        format_func=lambda x: f"🔑 {x}"
    )
    
    if selected_columns:
        system.platform_tracking_columns = selected_columns
    
    custom_column = st.text_input("افزودن ستون سفارشی (اختیاری)", placeholder="مثال: custom_code", key="custom_column")
    if custom_column and custom_column not in system.platform_tracking_columns:
        system.platform_tracking_columns.append(custom_column)
    
    st.markdown('<div class="rtl" style="margin-top: 15px; background: rgba(255, 255, 255, 0.9); padding: 15px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);">', unsafe_allow_html=True)
    st.markdown('<p style="font-weight: bold; color: #2c3e50; margin-bottom: 15px;">ستون‌های انتخاب شده:</p>', unsafe_allow_html=True)
    
    column_tags_html = ""
    for col in system.platform_tracking_columns:
        column_tags_html += f'<span class="column-tag">{col}</span> '
    
    if column_tags_html:
        st.markdown(f'<div style="margin-bottom: 15px;">{column_tags_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<p style="color: #e74c3c; animation: shake 0.5s;">هیچ ستونی انتخاب نشده است!</p>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="tip-box rtl">
        <b style="color: #2c3e50;">💡 نکته مهم:</b> 
        <ul style="margin-top: 8px; padding-right: 25px;">
            <li style="color: #7f8c8d;">ستون‌های کلیدی برای تحلیل دقیق‌تر تراکنش‌ها حیاتی‌اند.</li>
            <li style="color: #7f8c8d;">تمام ستون‌های مرتبط را انتخاب کنید تا دقت سیستم افزایش یابد.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# دکمه شروع با افکت‌های بصری فوق‌العاده
st.markdown('<div class="card animated" style="text-align: center;">', unsafe_allow_html=True)
st.markdown('<div class="rtl" style="margin-bottom: 20px; font-weight: bold; color: #2c3e50; font-size: 1.2rem;">برای شروع، دکمه زیر را فشار دهید:</div>', unsafe_allow_html=True)

start_button_col1, start_button_col2, start_button_col3 = st.columns([1, 2, 1])
with start_button_col2:
    start_button = st.button("🚀 شروع فرآیند مغایرت‌گیری", key="start_button")

if platform_file is not None and provider_file is not None:
    st.markdown('<p style="color: #2c3e50; font-weight: bold; text-align: center; margin-top: 15px; font-size: 1.1rem;">✓ فایل‌ها آماده هستند.</p>', unsafe_allow_html=True)
    st.markdown("""
    <div style="margin-top: 20px; width: 100%; height: 6px; background: rgba(255, 255, 255, 0.5); border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
        <div style="width: 100%; height: 100%; background: linear-gradient(90deg, #3498db, #2c3e50); border-radius: 10px; animation: progressWave 3s ease-in-out infinite;">
        </div>
    </div>
    <style>
    @keyframes progressWave {
        0% { width: 0%; }
        50% { width: 100%; transform: translateX(-50%); }
        100% { width: 0%; transform: translateX(0); }
    }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown('<p style="color: #e74c3c; font-weight: bold; text-align: center; margin-top: 15px; animation: pulse 1.5s infinite;">⚠️ لطفاً هر دو فایل را بارگذاری کنید</p>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

if start_button and platform_file is not None and provider_file is not None:
    # لودر زیبا با افکت ذره‌ای
    st.markdown("""
    <div class="card" style="text-align: center; padding: 40px; background: rgba(255, 255, 255, 0.9);">
        <div class="rtl" style="margin-bottom: 25px; font-weight: bold; color: #2c3e50; font-size: 1.3rem;">در حال پردازش اطلاعات...</div>
        <div style="display: flex; justify-content: center; margin: 25px 0;">
            <div class="elegant-loader"></div>
        </div>
        <div style="color: #3498db; font-weight: bold; font-size: 1.1rem; margin-top: 15px;">لطفاً کمی صبر کنید</div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.spinner(''):
        import uuid
        import time
        unique_id = str(uuid.uuid4())[:8]
        temp_platform_file = f"temp_platform_{unique_id}{os.path.splitext(platform_file.name)[1]}"
        temp_provider_file = f"temp_provider_{unique_id}{os.path.splitext(provider_file.name)[1]}"
        
        with open(temp_platform_file, "wb") as f:
            f.write(platform_file.getbuffer())
        with open(temp_provider_file, "wb") as f:
            f.write(provider_file.getbuffer())
        
        try:
            time.sleep(0.7)  # تأخیر برای نمایش لودر
            results = system.gateway_specific_reconciliation(temp_platform_file, temp_provider_file, selected_gateway)
            
            if results is None:
                st.markdown("""
                <div class="error rtl">
                    <h4>❌ خطا در پردازش!</h4>
                    <p>هیچ رکوردی برای gateway '{gateway}' یافت نشد. لطفاً فایل‌ها را بررسی کنید.</p>
                    <ul style="list-style-type: disc; margin-right: 25px;">
                        <li>فرمت فایل‌ها را بررسی کنید.</li>
                        <li>ستون gateway را در فایل پلتفرم چک کنید.</li>
                        <li>اطمینان حاصل کنید داده‌های '{gateway}' وجود دارد.</li>
                    </ul>
                </div>
                """.format(gateway=selected_gateway), unsafe_allow_html=True)
            else:
                # پیام موفقیت با افکت کنفتی
                st.markdown("""
                <div class="success-message">
                    <div class="success-icon">✓</div>
                    <h3 style="color: #27ae60; margin-bottom: 15px; font-size: 1.5rem;">عملیات با موفقیت انجام شد</h3>
                    <p style="color: #2c3e50; margin: 0; font-size: 1.1rem;">نتایج تحلیل آماده نمایش است</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown('<div class="card animated"><h2 class="section-header rtl">نتایج تحلیل مغایرت‌گیری</h2>', unsafe_allow_html=True)
                
                st.markdown("""
                <div class="success rtl">
                    <h4>✅ عملیات کامل شد</h4>
                    <p>داده‌ها با دقت بالا مقایسه شدند. نتایج را بررسی کنید.</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                if 'matches' in results and 'non_matches' in results:
                    total_matches = len(results['matches'])
                    total_non_matches = len(results['non_matches'])
                    match_percent = round(total_matches / (total_matches + total_non_matches) * 100, 2) if (total_matches + total_non_matches) > 0 else 0
                    
                    if match_percent >= 90:
                        match_color = "#27ae60"
                    elif match_percent >= 70:
                        match_color = "#f1c40f"
                    else:
                        match_color = "#e74c3c"
                
                with col1:
                    if 'platform_codes' in results:
                        st.markdown(f"""
                        <div class="metric-card animated">
                            <div class="metric-value">{len(results['platform_codes'])}</div>
                            <div class="metric-label">کدهای پلتفرم</div>
                        </div>
                        """, unsafe_allow_html=True)
                
                with col2:
                    if 'filtered_platform' in results:
                        st.markdown(f"""
                        <div class="metric-card animated">
                            <div class="metric-value">{len(results['filtered_platform'])}</div>
                            <div class="metric-label">رکوردهای {selected_gateway}</div>
                        </div>
                        """, unsafe_allow_html=True)
                
                with col3:
                    if 'matches' in results and 'non_matches' in results:
                        st.markdown(f"""
                        <div class="metric-card animated" style="border-right: 6px solid {match_color};">
                            <div class="metric-value" style="color: {match_color} !important;">{match_percent}%</div>
                            <div class="metric-label">تطابق</div>
                        </div>
                        """, unsafe_allow_html=True)
                
                if 'matches' in results and 'non_matches' in results:
                    st.markdown(f"""
<div style="margin-top: 25px; margin-bottom: 30px;">
    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
        <div style="color: #2c3e50;">0%</div>
        <div style="color: #2c3e50;">50%</div>
        <div style="color: #2c3e50;">100%</div>
    </div>
    <div style="width: 100%; height: 15px; background: rgba(255, 255, 255, 0.5); border-radius: 15px; overflow: hidden; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
        <div style="width: {match_percent}%; height: 100%; background: linear-gradient(90deg, {match_color}, {match_color}); border-radius: 15px; animation: slide 2s infinite ease-in-out;"></div>
    </div>
    <div style="text-align: center; margin-top: 10px; font-weight: bold; color: {match_color} !important; font-size: 1.1rem;">
        {match_percent}% تطابق ({total_matches} از {total_matches + total_non_matches})
    </div>
</div>
<style>
    @keyframes slide {{
        0% {{ transform: translateX(0); }}
        50% {{ transform: translateX(20px); }}
        100% {{ transform: translateX(0); }}
    }}
</style>
""", unsafe_allow_html=True)
                
                st.markdown('<h3 class="section-header rtl">نمودارهای تحلیلی</h3>', unsafe_allow_html=True)
                
                if 'matches' in results and 'non_matches' in results:
                    match_count = len(results['matches'])
                    non_match_count = len(results['non_matches'])
                    
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        fig = px.pie(
                            names=["تطابق‌ها", "عدم تطابق‌ها"],
                            values=[match_count, non_match_count],
                            color_discrete_sequence=["#27ae60", "#e74c3c"],
                            hole=0.5,
                            title=f"تحلیل تطابق برای {selected_gateway}"
                        )
                        fig.update_traces(
                            textposition='inside',
                            textinfo='percent+label',
                            marker=dict(line=dict(color='white', width=3)),
                            pull=[0.1, 0]
                        )
                        fig.update_layout(
                            font=dict(family='Vazir', size=16, color="#2c3e50"),
                            legend=dict(orientation="h", y=-0.1, x=0.5, font=dict(color="#2c3e50")),
                            margin=dict(t=60, b=60, l=20, r=20),
                            paper_bgcolor='rgba(255, 255, 255, 0.9)',
                            plot_bgcolor='rgba(255, 255, 255, 0.9)',
                            title_font=dict(color="#2c3e50", size=18)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        bar_fig = px.bar(
                            x=["تطابق‌ها", "عدم تطابق‌ها"],
                            y=[match_count, non_match_count],
                            color=["تطابق‌ها", "عدم تطابق‌ها"],
                            color_discrete_map={"تطابق‌ها": "#27ae60", "عدم تطابق‌ها": "#e74c3c"},
                            title="مقایسه آماری"
                        )
                        bar_fig.update_layout(
                            font=dict(family='Vazir', size=16, color="#2c3e50"),
                            showlegend=False,
                            margin=dict(t=60, b=40, l=40, r=20),
                            paper_bgcolor='rgba(255, 255, 255, 0.9)',
                            plot_bgcolor='rgba(255, 255, 255, 0.9)',
                            title_font=dict(color="#2c3e50", size=18),
                            yaxis=dict(tickfont=dict(color="#2c3e50")),
                            xaxis=dict(tickfont=dict(color="#2c3e50"))
                        )
                        st.plotly_chart(bar_fig, use_container_width=True)
                
                st.markdown('<h3 class="section-header rtl">جداول تعاملی</h3>', unsafe_allow_html=True)
                
                tab_icons = {
                    "رکوردهای": '<i class="fas fa-search"></i>',
                    "کدهای استخراج شده": '<i class="fas fa-key"></i>',
                    "تطابق‌ها": '<i class="fas fa-check-circle"></i>',
                    "عدم تطابق‌ها": '<i class="fas fa-times-circle"></i>'
                }
                
                tab_titles = []
                tab_dataframes = []
                
                if 'filtered_platform' in results:
                    tab_titles.append(f"{tab_icons['رکوردهای']} رکوردهای {selected_gateway}")
                    tab_dataframes.append(results['filtered_platform'])
                
                if 'platform_codes' in results:
                    tab_titles.append(f"{tab_icons['کدهای استخراج شده']} کدهای استخراج شده")
                    tab_dataframes.append(results['platform_codes'])
                
                if 'matches' in results:
                    tab_titles.append(f"{tab_icons['تطابق‌ها']} تطابق‌ها")
                    tab_dataframes.append(results['matches'])
                
                if 'non_matches' in results:
                    tab_titles.append(f"{tab_icons['عدم تطابق‌ها']} عدم تطابق‌ها")
                    tab_dataframes.append(results['non_matches'])
                
                st.markdown("""
                <style>
                .dataframe-container {
                    border-radius: 20px;
                    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
                    padding: 15px;
                    background: rgba(255, 255, 255, 0.9);
                    margin-top: 15px;
                    backdrop-filter: blur(5px);
                }
                .dataframe-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 15px;
                    border-bottom: 2px solid #e9ecef;
                    margin-bottom: 15px;
                    background: linear-gradient(90deg, #3498db, #2c3e50);
                    border-radius: 15px 15px 0 0;
                }
                .dataframe-title {
                    font-weight: bold;
                    color: white;
                }
                .dataframe-count {
                    background: rgba(255, 255, 255, 0.8);
                    color: #2c3e50 !important;
                    border-radius: 25px;
                    padding: 5px 15px;
                    font-weight: bold;
                }
                </style>
                """, unsafe_allow_html=True)
                
                tabs = st.tabs(tab_titles)
                
                for i, tab in enumerate(tabs):
                    with tab:
                        tab_name = tab_titles[i].replace('<i class="fas fa-', '').replace('"></i>', '').split(" ", 1)[1]
                        st.markdown(f"""
                        <div class="dataframe-header rtl">
                            <div class="dataframe-title">{tab_name}</div>
                            <div class="dataframe-count">{len(tab_dataframes[i])} رکورد</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # اصلاح دیتافریم برای نمایش در Streamlit
                        fixed_df = fix_dataframe_for_streamlit(tab_dataframes[i])
                        
                        st.dataframe(
                            fixed_df,
                            use_container_width=True,
                            height=450,
                            column_config={
                                "_index": st.column_config.Column(
                                    label="ردیف",
                                    width="small"
                                )
                            }
                        )
                        
                        # استفاده از دیتافریم اصلاح شده برای CSV
                        csv = fixed_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label=f"دانلود {tab_name}",
                            data=csv,
                            file_name=f"{tab_name.replace(' ', '_')}.csv",
                            mime='text/csv',
                            key=f"download_{i}",
                            help=f"دریافت داده‌های {tab_name} در قالب CSV"
                        )

                
                st.markdown('<h3 class="section-header rtl">گزارش نهایی</h3>', unsafe_allow_html=True)
                
                st.markdown("""
                <div class="card" style="text-align: center; padding: 40px; background: rgba(255, 255, 255, 0.9);">
                    <h4 style="margin-bottom: 25px; color: #2c3e50; font-size: 1.5rem;">گزارش تحلیلی مغایرت‌گیری</h4>
                    <p style="color: #7f8c8d; font-size: 1.1rem;">گزارش کامل را با دکمه زیر دانلود کنید.</p>
                </div>
                """, unsafe_allow_html=True)
                
                output_file = f"reconciliation_report_{selected_gateway}.xlsx"
                system.generate_report(results, output_file)
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    with open(output_file, "rb") as f:
                        file_bytes = f.read()
                        b64 = base64.b64encode(file_bytes).decode()
                        
                        download_button_style = """
                        <style>
                        .download-excel-button {
                            background: linear-gradient(90deg, #e74c3c, #f1c40f);
                            color: white !important;
                            padding: 16px 32px;
                            border-radius: 30px;
                            font-weight: bold;
                            font-size: 1.2rem;
                            box-shadow: 0 8px 25px rgba(241, 196, 15, 0.4);
                            transition: all 0.4s ease;
                            display: inline-block;
                            position: relative;
                            overflow: hidden;
                        }
                        .download-excel-button:hover {
                            transform: scale(1.07);
                            box-shadow: 0 10px 30px rgba(241, 196, 15, 0.5);
                        }
                        .download-excel-button::after {
                            content: '';
                            position: absolute;
                            top: 0;
                            left: 0;
                            width: 100%;
                            height: 100%;
                            background: rgba(255, 255, 255, 0.3);
                            border-radius: 30px;
                            transform: scale(0);
                            transition: transform 0.4s ease;
                        }
                        .download-excel-button:hover::after {
                            transform: scale(1);
                        }
                        </style>
                        """
                        
                        st.markdown(download_button_style, unsafe_allow_html=True)
                        
                        st.download_button(
                            label="📊 دانلود گزارش اکسل",
                            data=file_bytes,
                            file_name=output_file,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_report",
                            help="دریافت گزارش کامل در قالب اکسل"
                        )
                
                st.markdown("""
                <div class="tip-box rtl" style="margin-top: 25px;">
                    <b style="color: #2c3e50;">💡 نکته کاربردی:</b> 
                    <ul style="margin-top: 10px; padding-right: 25px;">
                        <li style="color: #7f8c8d;">گزارش شامل خلاصه، تطابق‌ها، عدم تطابق‌ها و فیلترهای Gateway است.</li>
                        <li style="color: #7f8c8d;">این گزارش را برای تحلیل‌های بعدی در اختیار تیم مالی قرار دهید.</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            
            try:
                os.remove(temp_platform_file)
                os.remove(temp_provider_file)
                os.remove(output_file)
            except Exception as cleanup_error:
                print(f"خطا در پاک کردن فایل‌ها: {str(cleanup_error)}")
                pass
                
        except Exception as e:
            st.markdown(f"""
            <div class="error rtl">
                <h4>❌ خطای غیرمنتظره!</h4>
                <p>{str(e)}</p>
                <h5 style="color: white;">پیشنهادات رفع مشکل:</h5>
                <ul style="list-style-type: disc; margin-right: 25px;">
                    <li>فایل‌ها را مجدداً بررسی کنید.</li>
                    <li>اطمینان حاصل کنید داده‌ها معتبر هستند.</li>
                    <li>با پشتیبانی تماس بگیرید.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            print(f"خطای سیستم: {str(e)}")
            
            try:
                os.remove(temp_platform_file)
                os.remove(temp_provider_file)
            except Exception as cleanup_error:
                print(f"خطا در پاک کردن فایل‌ها پس از خطا: {str(cleanup_error)}")
                pass
                
        st.markdown('</div>', unsafe_allow_html=True)

# راهنمای استفاده با طراحی حرفه‌ای
with st.expander("📖 راهنمای کاربری سیستم"):
    st.markdown("""
    <div class="rtl" style="background: rgba(255, 255, 255, 0.9); padding: 25px; border-radius: 20px; box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);">
    <h3 style="color: #2c3e50; border-bottom: 4px solid #3498db; padding-bottom: 12px; margin-bottom: 25px; font-size: 1.8rem;">راهنمای استفاده از سیستم مغایرت‌گیری WALLEX</h3>
    
    <div style="display: flex; align-items: center; margin-bottom: 30px; animation: slideIn 1s ease-out;">
        <div style="background: linear-gradient(135deg, #3498db, #2c3e50); color: white !important; border-radius: 50%; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; margin-left: 20px; font-weight: bold; font-size: 1.5rem;">1</div>
        <div>
            <h4 style="color: #2c3e50; font-size: 1.4rem;">بارگذاری فایل‌ها</h4>
            <p style="color: #7f8c8d; font-size: 1.1rem;">فایل‌های پلتفرم و ارائه‌دهنده را با فرمت‌های CSV، Excel یا JSON بارگذاری کنید.</p>
            <div style="background: rgba(52, 152, 219, 0.1); padding: 15px; border-radius: 15px; margin-top: 10px;">
                <p style="margin: 0; color: #2c3e50;"><strong style="color: #3498db;">💡 نکته:</strong> فایل‌ها باید دارای هدر باشند.</p>
            </div>
        </div>
    </div>
    
    <div style="display: flex; align-items: center; margin-bottom: 30px; animation: slideIn 1.2s ease-out;">
        <div style="background: linear-gradient(135deg, #3498db, #2c3e50); color: white !important; border-radius: 50%; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; margin-left: 20px; font-weight: bold; font-size: 1.5rem;">2</div>
        <div>
            <h4 style="color: #2c3e50; font-size: 1.4rem;">انتخاب Gateway</h4>
            <p style="color: #7f8c8d; font-size: 1.1rem;">Gateway مورد نظر را برای فیلتر کردن داده‌ها انتخاب کنید.</p>
            <div style="display: flex; flex-wrap: wrap; margin-top: 15px;">
                <span style="background: rgba(255, 255, 255, 0.8); padding: 8px 16px; border-radius: 25px; margin: 5px; font-size: 1rem; color: #2c3e50; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);"><i class="fas fa-credit-card"></i> Payman</span>
                <span style="background: rgba(255, 255, 255, 0.8); padding: 8px 16px; border-radius: 25px; margin: 5px; font-size: 1rem; color: #2c3e50; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);"><i class="fas fa-university"></i> jibitcobank</span>
                <span style="background: rgba(255, 255, 255, 0.8); padding: 8px 16px; border-radius: 25px; margin: 5px; font-size: 1rem; color: #2c3e50; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);"><i class="fas fa-money-bill-wave"></i> ezpay</span>
                <span style="background: rgba(255, 255, 255, 0.8); padding: 8px 16px; border-radius: 25px; margin: 5px; font-size: 1rem; color: #2c3e50; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);"><i class="fas fa-coins"></i> toman</span>
                <span style="background: rgba(255, 255, 255, 0.8); padding: 8px 16px; border-radius: 25px; margin: 5px; font-size: 1rem; color: #2c3e50; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);"><i class="fas fa-dollar-sign"></i> vandar</span>
                <span style="background: rgba(255, 255, 255, 0.8); padding: 8px 16px; border-radius: 25px; margin: 5px; font-size: 1rem; color: #2c3e50; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);"><i class="fas fa-yen-sign"></i> jibit</span>
            </div>
        </div>
    </div>
    
    <div style="display: flex; align-items: center; margin-bottom: 30px; animation: slideIn 1.4s ease-out;">
        <div style="background: linear-gradient(135deg, #3498db, #2c3e50); color: white !important; border-radius: 50%; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; margin-left: 20px; font-weight: bold; font-size: 1.5rem;">3</div>
        <div>
            <h4 style="color: #2c3e50; font-size: 1.4rem;">انتخاب نوع مقایسه</h4>
            <p style="color: #7f8c8d; font-size: 1.1rem;">نوع مقایسه را انتخاب کنید:</p>
            <div style="display: flex; margin-top: 15px;">
                <div style="flex: 1; background: rgba(255, 255, 255, 0.9); padding: 20px; border-radius: 15px; margin-left: 15px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);">
                    <h5 style="margin-top: 0; color: #2c3e50; font-size: 1.2rem;">تطبیق دقیق</h5>
                    <p style="margin-bottom: 0; color: #7f8c8d; font-size: 1rem;">فقط کدهای دقیقاً یکسان تطابق خواهند داشت.</p>
                </div>
                <div style="flex: 1; background: rgba(255, 255, 255, 0.9); padding: 20px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);">
                    <h5 style="margin-top: 0; color: #2c3e50; font-size: 1.2rem;">تطبیق فازی</h5>
                    <p style="margin-bottom: 0; color: #7f8c8d; font-size: 1rem;">با استفاده از آستانه شباهت، کدهای مشابه را تطبیق می‌دهد.</p>
                </div>
            </div>
        </div>
    </div>
    
    <div style="display: flex; align-items: center; margin-bottom: 30px; animation: slideIn 1.6s ease-out;">
        <div style="background: linear-gradient(135deg, #3498db, #2c3e50); color: white !important; border-radius: 50%; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; margin-left: 20px; font-weight: bold; font-size: 1.5rem;">4</div>
        <div>
            <h4 style="color: #2c3e50; font-size: 1.4rem;">تنظیم ستون‌ها</h4>
            <p style="color: #7f8c8d; font-size: 1.1rem;">ستون‌های کلیدی را برای دقت بیشتر در تحلیل انتخاب کنید.</p>
            <div style="background: rgba(52, 152, 219, 0.1); padding: 15px; border-radius: 15px; margin-top: 10px;">
                <p style="margin: 0; color: #2c3e50;"><strong style="color: #3498db;">🔍 نکته:</strong> انتخاب دقیق ستون‌ها باعث افزایش کیفیت تحلیل می‌شود.</p>
            </div>
        </div>
    </div>
    
    <div style="display: flex; align-items: center; margin-bottom: 30px; animation: slideIn 1.8s ease-out;">
        <div style="background: linear-gradient(135deg, #3498db, #2c3e50); color: white !important; border-radius: 50%; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; margin-left: 20px; font-weight: bold; font-size: 1.5rem;">5</div>
        <div>
            <h4 style="color: #2c3e50; font-size: 1.4rem;">شروع مغایرت‌گیری</h4>
            <p style="color: #7f8c8d; font-size: 1.1rem;">دکمه "شروع فرآیند مغایرت‌گیری" را فشار دهید تا عملیات پردازش آغاز شود.</p>
        </div>
    </div>
    
    <div style="display: flex; align-items: center; margin-bottom: 30px; animation: slideIn 2s ease-out;">
        <div style="background: linear-gradient(135deg, #3498db, #2c3e50); color: white !important; border-radius: 50%; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; margin-left: 20px; font-weight: bold; font-size: 1.5rem;">6</div>
        <div>
            <h4 style="color: #2c3e50; font-size: 1.4rem;">بررسی نتایج</h4>
            <p style="color: #7f8c8d; font-size: 1.1rem;">نتایج را با استفاده از نمودارها، جداول و گزارش‌ها بررسی کنید.</p>
            <ul style="list-style-type: none; padding: 0; margin-top: 10px;">
                <li style="display: flex; align-items: center; margin-bottom: 10px;">
                    <span style="background: #27ae60; color: white !important; border-radius: 50%; width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center; margin-left: 15px;"><i class="fas fa-check"></i></span>
                    <span style="color: #2c3e50; font-size: 1.1rem;">آمار خلاصه را بررسی کنید.</span>
                </li>
                <li style="display: flex; align-items: center; margin-bottom: 10px;">
                    <span style="background: #27ae60; color: white !important; border-radius: 50%; width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center; margin-left: 15px;"><i class="fas fa-chart-pie"></i></span>
                    <span style="color: #2c3e50; font-size: 1.1rem;">نمودارهای تحلیلی را مشاهده کنید.</span>
                </li>
                <li style="display: flex; align-items: center; margin-bottom: 10px;">
                    <span style="background: #27ae60; color: white !important; border-radius: 50%; width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center; margin-left: 15px;"><i class="fas fa-table"></i></span>
                    <span style="color: #2c3e50; font-size: 1.1rem;">جداول تعاملی را بررسی کنید.</span>
                </li>
            </ul>
        </div>
    </div>
    
    <div style="display: flex; align-items: center; animation: slideIn 2.2s ease-out;">
        <div style="background: linear-gradient(135deg, #3498db, #2c3e50); color: white !important; border-radius: 50%; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; margin-left: 20px; font-weight: bold; font-size: 1.5rem;">7</div>
        <div>
            <h4 style="color: #2c3e50; font-size: 1.4rem;">دانلود گزارش</h4>
            <p style="color: #7f8c8d; font-size: 1.1rem;">گزارش نهایی را با دکمه "دانلود گزارش اکسل" دریافت و ذخیره کنید.</p>
            <div style="text-align: center; margin-top: 15px;">
                <span style="display: inline-block; background: linear-gradient(90deg, #e74c3c, #f1c40f); color: white !important; padding: 12px 30px; border-radius: 30px; font-weight: bold; font-size: 1.2rem; box-shadow: 0 6px 18px rgba(241, 196, 15, 0.4);"><i class="fas fa-download"></i> دانلود گزارش</span>
            </div>
        </div>
    </div>
    </div>
    <style>
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    </style>
    """, unsafe_allow_html=True)

# افزودن بخش ویژگی‌ها با طراحی فنی و حرفه‌ای
st.markdown('<div class="card animated" style="margin-top: 60px;">', unsafe_allow_html=True)
st.markdown('<h2 class="section-header rtl">فناوری‌های پیشرفته سیستم WALLEX</h2>', unsafe_allow_html=True)

features_col1, features_col2, features_col3 = st.columns(3)

with features_col1:
    st.markdown("""
    <div style="background: rgba(255, 255, 255, 0.9); border-radius: 20px; padding: 25px; height: 100%; box-shadow: 0 8px 25px rgba(0,0,0,0.1); transition: all 0.4s ease; animation: bounce 0.8s ease-out;">
        <div style="text-align: center; margin-bottom: 20px;">
            <span style="font-size: 3rem;" class="fas fa-brain" data-fa-transform="shrink-2"></span>
        </div>
        <h4 style="text-align: center; color: #2c3e50; font-size: 1.4rem;">الگوریتم‌های هوش مصنوعی</h4>
        <p class="rtl" style="color: #7f8c8d; font-size: 1.1rem;">تشخیص الگوهای پیچیده با استفاده از الگوریتم‌های پیشرفته یادگیری ماشین.</p>
    </div>
    """, unsafe_allow_html=True)

with features_col2:
    st.markdown("""
    <div style="background: rgba(255, 255, 255, 0.9); border-radius: 20px; padding: 25px; height: 100%; box-shadow: 0 8px 25px rgba(0,0,0,0.1); transition: all 0.4s ease; animation: bounce 1s ease-out;">
        <div style="text-align: center; margin-bottom: 20px;">
            <span style="font-size: 3rem;" class="fas fa-database" data-fa-transform="shrink-2"></span>
        </div>
        <h4 style="text-align: center; color: #2c3e50; font-size: 1.4rem;">پردازش داده‌های حجیم</h4>
        <p class="rtl" style="color: #7f8c8d; font-size: 1.1rem;">تحلیل و پردازش انبوه داده‌های تراکنشی با کارایی بالا و دقت مطلوب.</p>
    </div>
    """, unsafe_allow_html=True)

with features_col3:
    st.markdown("""
    <div style="background: rgba(255, 255, 255, 0.9); border-radius: 20px; padding: 25px; height: 100%; box-shadow: 0 8px 25px rgba(0,0,0,0.1); transition: all 0.4s ease; animation: bounce 1.2s ease-out;">
        <div style="text-align: center; margin-bottom: 20px;">
            <span style="font-size: 3rem;" class="fas fa-robot" data-fa-transform="shrink-2"></span>
        </div>
        <h4 style="text-align: center; color: #2c3e50; font-size: 1.4rem;">سیستم تصمیم‌گیری خودکار</h4>
        <p class="rtl" style="color: #7f8c8d; font-size: 1.1rem;">شناسایی و طبقه‌بندی هوشمند مغایرت‌ها با استفاده از تکنیک‌های پیشرفته NLP.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# پانویس با طراحی حرفه‌ای و انیمیشن
st.markdown("""
<div class="footer rtl" style="animation: fadeIn 1.5s ease-out;">
    <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255, 255, 255, 0.9); padding: 20px; border-radius: 20px; box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);">
        <div style="color: #2c3e50;">
            <strong style="color: #3498db;">سیستم مغایرت‌گیری هوشمند </strong> - نسخه 3.1
        </div>
        <div>
            <span style="margin: 0 15px; color: #7f8c8d;">
                <span style="color: #2c3e50; font-weight: bold;">قابلیت‌های جدید:</span> 
                تحلیل پیشرفته | الگوریتم‌های هوشمند | پردازش خودکار
            </span>
        </div>
        <div style="color: #2c3e50;">
            به‌روزرسانی: 5 مارس 2025
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
