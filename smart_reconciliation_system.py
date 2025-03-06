import pandas as pd
import numpy as np
import re
import json
import os
from fuzzywuzzy import fuzz, process

# تابع جدید برای تبدیل اعداد بزرگ به رشته
def safe_excel_value(value):
    """
    مقادیر را برای اکسپورت به اکسل ایمن می‌کند.
    اعداد صحیح بسیار بزرگ را به رشته تبدیل می‌کند تا از خطای 'int too big to convert' جلوگیری شود.
    """
    if isinstance(value, (int, np.int64, np.int32)) and (value > 2**31-1 or value < -2**31):
        return str(value)  # تبدیل اعداد بزرگ به رشته
    return value

def simple_normalize(text):
    """یک تابع ساده برای نرمال‌سازی متن فارسی"""
    if not isinstance(text, str):
        text = str(text)
        
    replacements = {
        'ي': 'ی',
        'ك': 'ک',
        'ة': 'ه',
        'آ': 'ا',
        'إ': 'ا',
        'أ': 'ا',
        'ء': '',
        '‌': ' ',  # نیم‌فاصله
        '\u200c': ' '  # نیم‌فاصله با کد یونیکد
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def safe_convert_to_str(value):
    """
    تبدیل ایمن مقادیر به رشته با مدیریت انواع مختلف داده
    """
    if value is None or pd.isna(value):
        return ''
    
    try:
        # برای اعداد بزرگ یا float
        if isinstance(value, (int, np.integer, float, np.floating)):
            # چک کردن محدوده اعداد صحیح
            if isinstance(value, (int, np.integer)) and (value > 2**63-1 or value < -2**63):
                return str(value)
            # برای اعداد اعشاری
            if isinstance(value, (float, np.floating)):
                return f'{value:.6f}'.rstrip('0').rstrip('.') if '.' in f'{value:.6f}' else f'{value:.6f}'
        
        # تبدیل به رشته برای سایر انواع
        return str(value)
    
    except Exception as e:
        print(f"خطا در تبدیل مقدار {value}: {e}")
        return str(value)

# تابع جدید برای اصلاح ستون‌های تکراری
def fix_duplicate_columns(df):
    """
    تابع کمکی برای اصلاح ستون‌های تکراری در دیتافریم
    """
    if df is None or df.empty:
        return df
        
    # ابتدا تمام نام‌های ستون را به رشته تبدیل می‌کنیم
    columns = [str(col) for col in df.columns]
    
    # بررسی ستون‌های تکراری
    if len(columns) != len(set(columns)):
        duplicate_cols = [col for col in columns if columns.count(col) > 1]
        print(f"ستون‌های تکراری یافت شد: {duplicate_cols}")
        
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
        df_fixed = df.copy()
        df_fixed.columns = new_columns
        print("ستون‌های تکراری اصلاح شدند.")
        return df_fixed
    
    return df

class SmartReconciliationSystem:
    def __init__(self):
        # الگوهای جستجوی کد رهگیری - این الگوها باید با توجه به داده‌های واقعی تنظیم شوند
        self.tracking_patterns = [
            r'\b\d{5,30}\b',  # اعداد بلند (احتمالاً کد رهگیری)
            r'[A-Za-z0-9]{10,30}',  # ترکیبی از حروف و اعداد (احتمالاً کد رهگیری)
            r'TR-\d+',  # مثال: TR-12345678
            r'TRK\d+',  # مثال: TRK12345678
            # الگوهای جدید برای UUID
            r'\b[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+\b',  # برای UUID بدون پیشوند
            r'wallex-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+',  # برای UUID با پیشوند wallex
            # اضافه کردن الگوهای دیگر بر اساس نیاز
        ]
        
        # ستون‌های خاص فایل پلتفرم که کدهای رهگیری در آنها می‌تواند باشد
        self.platform_tracking_columns = [
            'gateway_tracking_code',
            'gateway_identifier',
            'meta_data_1'
        ]
    
    def detect_file_type(self, file_path):
        """تشخیص نوع فایل بر اساس پسوند"""
        _, ext = os.path.splitext(file_path)
        return ext.lower()
    
    def read_file(self, file_path):
        """خواندن فایل با توجه به نوع آن"""
        file_type = self.detect_file_type(file_path)
        
        if file_type == '.csv':
            # خواندن فایل CSV
            try:
                # ابتدا با کدینگ UTF-8 تلاش می‌کنیم
                return pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                # اگر موفق نشد، با کدینگ windows-1256 تلاش می‌کنیم (برای فارسی)
                return pd.read_csv(file_path, encoding='windows-1256')
        
        elif file_type == '.xlsx' or file_type == '.xls':
            # خواندن فایل اکسل
            return pd.read_excel(file_path)
        
        elif file_type == '.json':
            # خواندن فایل JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # تبدیل JSON به دیتافریم
            if isinstance(data, list):
                return pd.DataFrame(data)
            else:
                # اگر JSON ساختار پیچیده‌تری دارد، نیاز به پردازش بیشتری است
                # مثلا، جستجو در کل JSON برای استخراج کدهای رهگیری
                return self.extract_from_complex_json(data)
        
        else:
            raise ValueError(f"فرمت فایل {file_type} پشتیبانی نمی‌شود")
    
    def extract_from_complex_json(self, data):
        """استخراج داده‌ها از JSON با ساختار پیچیده"""
        # این تابع باید برای ساختارهای خاص JSON سفارشی‌سازی شود
        # در اینجا یک مثال ساده آورده شده است
        
        flat_data = []
        
        def flatten_json(json_obj, prefix=""):
            """تبدیل JSON تودرتو به ساختار تخت"""
            if isinstance(json_obj, dict):
                for k, v in json_obj.items():
                    key = f"{prefix}.{k}" if prefix else k
                    if isinstance(v, (dict, list)):
                        flatten_json(v, key)
                    else:
                        flat_data.append({key: v})
            elif isinstance(json_obj, list):
                for i, item in enumerate(json_obj):
                    key = f"{prefix}[{i}]"
                    flatten_json(item, key)
        
        flatten_json(data)
        return pd.DataFrame(flat_data)
    
    def extract_potential_tracking_codes(self, df, is_platform=False):
        """استخراج کدهای رهگیری احتمالی از دیتافریم
        
        اگر is_platform=True باشد، فقط ستون‌های خاص پلتفرم بررسی می‌شوند
        """
        tracking_codes = []
        
        # تعیین ستون‌هایی که باید بررسی شوند
        if is_platform:
            # برای فایل پلتفرم، فقط ستون‌های خاص را بررسی می‌کنیم
            columns_to_check = [col for col in self.platform_tracking_columns if col in df.columns]
            print(f"بررسی ستون‌های خاص پلتفرم: {columns_to_check}")
        else:
            # برای سایر فایل‌ها، همه ستون‌ها را بررسی می‌کنیم
            columns_to_check = df.columns
            print(f"بررسی تمام ستون‌ها: {len(columns_to_check)} ستون")
        
        # بررسی ستون‌های انتخاب شده
        for column in columns_to_check:
            print(f"در حال بررسی ستون: {column}")
            # بررسی هر سلول در ستون
            for value in df[column].astype(str):
                if value == 'nan' or value == 'None':
                    continue
                
                # نرمال‌سازی متن (مخصوصاً برای متون فارسی)
                normalized_value = simple_normalize(value) if any('\u0600' <= c <= '\u06FF' for c in value) else value
                
                # جستجوی کدهای رهگیری با استفاده از الگوها
                for pattern in self.tracking_patterns:
                    matches = re.finditer(pattern, normalized_value)
                    for match in matches:
                        tracking_code = match.group()
                        try:
                            row_index = df[df[column].astype(str) == value].index[0]
                            tracking_codes.append({
                                'code': tracking_code,
                                'column': column,
                                'row_index': row_index,
                                'original_text': value
                            })
                            print(f"کد رهگیری یافت شد: {tracking_code} در ستون {column}")
                        except IndexError:
                            print(f"خطا در پیدا کردن ردیف برای مقدار: {value}")
        
        result_df = pd.DataFrame(tracking_codes) if tracking_codes else pd.DataFrame(columns=['code', 'column', 'row_index', 'original_text'])
        return result_df
    
    def extract_codes_from_platform(self, df):
        """استخراج کدهای رهگیری از فایل پلتفرم با روش خاص"""
        return self.extract_potential_tracking_codes(df, is_platform=True)
    
    def extract_codes_from_provider(self, df):
        """استخراج کدهای رهگیری از فایل ارائه‌دهنده"""
        return self.extract_potential_tracking_codes(df, is_platform=False)
    
    # تابع کمکی برای چک کردن وجود کد در متن
    def is_code_in_text(self, code, text):
        """بررسی وجود کد در متن با حفظ حساسیت به حروف بزرگ و کوچک"""
        return str(code) in str(text)
    
    def find_exact_matches(self, codes1, codes2):
        """یافتن کدهای کاملاً یکسان بین دو مجموعه"""
        matches = []
        non_matches_file1 = []
        non_matches_file2 = []
        
        # اگر یکی از دیتافریم‌ها خالی است، همه را غیرمنطبق در نظر می‌گیریم
        if codes1.empty:
            print("هشدار: دیتافریم کدهای فایل اول خالی است!")
            for _, row2 in codes2.iterrows():
                non_matches_file2.append({
                    'file2_code': row2['code'],
                    'file2_column': row2['column'],
                    'file2_row': row2['row_index'],
                    'match_type': 'فقط در فایل 2'
                })
            return pd.DataFrame(), pd.DataFrame(non_matches_file2)
        
        if codes2.empty:
            print("هشدار: دیتافریم کدهای فایل دوم خالی است!")
            for _, row1 in codes1.iterrows():
                non_matches_file1.append({
                    'file1_code': row1['code'],
                    'file1_column': row1['column'],
                    'file1_row': row1['row_index'],
                    'match_type': 'فقط در فایل 1'
                })
            return pd.DataFrame(), pd.DataFrame(non_matches_file1)
        
        # بررسی هر کد از مجموعه اول
        for _, row1 in codes1.iterrows():
            code1 = row1['code']
            found = False
            
            # جستجو در تمام کدهای مجموعه دوم
            for _, row2 in codes2.iterrows():
                code2 = row2['code']
                original_text2 = row2['original_text']
                
                # بررسی تطابق دقیق (با توجه به حساسیت به حروف بزرگ و کوچک) یا وجود در متن
                if code1 == code2 or self.is_code_in_text(code1, original_text2):
                    matches.append({
                        'file1_code': code1,
                        'file1_column': row1['column'],
                        'file1_row': row1['row_index'],
                        'file2_code': code2,
                        'file2_column': row2['column'],
                        'file2_row': row2['row_index'],
                        'file2_text': original_text2[:50] + ('...' if len(original_text2) > 50 else ''),
                        'match_type': 'دقیق' if code1 == code2 else 'درون متن'
                    })
                    found = True
                    break
            
            # اگر تطابقی پیدا نشد
            if not found:
                non_matches_file1.append({
                    'file1_code': code1,
                    'file1_column': row1['column'],
                    'file1_row': row1['row_index'],
                    'match_type': 'فقط در فایل 1'
                })
        
        # بررسی کدهای مجموعه دوم که در مجموعه اول نیستند
        matched_codes2 = [match['file2_code'] for match in matches]
        for _, row2 in codes2.iterrows():
            code2 = row2['code']
            if code2 not in matched_codes2:
                # بررسی آیا این کد در متن کدهای مجموعه اول وجود دارد
                found_in_text = False
                for _, row1 in codes1.iterrows():
                    if self.is_code_in_text(code2, row1['original_text']):
                        found_in_text = True
                        break
                
                if not found_in_text:
                    non_matches_file2.append({
                        'file2_code': code2,
                        'file2_column': row2['column'],
                        'file2_row': row2['row_index'],
                        'match_type': 'فقط در فایل 2'
                    })
        
        # ترکیب مغایرت‌ها
        non_matches = non_matches_file1 + non_matches_file2
        
        # اصلاح ستون‌های تکراری در خروجی
        matches_df = pd.DataFrame(matches) if matches else pd.DataFrame()
        non_matches_df = pd.DataFrame(non_matches) if non_matches else pd.DataFrame()
        
        # چک و اصلاح ستون‌های تکراری
        matches_df = fix_duplicate_columns(matches_df)
        non_matches_df = fix_duplicate_columns(non_matches_df)
        
        return matches_df, non_matches_df
    
    def find_similar_codes(self, codes1, codes2, threshold=85):
        """یافتن کدهای مشابه بین دو مجموعه با استفاده از فاصله ویرایشی و جستجو در متن"""
        matches = []
        non_matches = []
        
        # اگر یکی از دیتافریم‌ها خالی است، همه را غیرمنطبق در نظر می‌گیریم
        if codes1.empty:
            print("هشدار: دیتافریم کدهای فایل اول خالی است!")
            for _, row2 in codes2.iterrows():
                non_matches.append({
                    'file2_code': row2['code'],
                    'file2_column': row2['column'],
                    'file2_row': row2['row_index'],
                    'similarity': 0,
                    'match_type': 'فقط در فایل 2'
                })
            return pd.DataFrame(), pd.DataFrame(non_matches)
        
        if codes2.empty:
            print("هشدار: دیتافریم کدهای فایل دوم خالی است!")
            for _, row1 in codes1.iterrows():
                non_matches.append({
                    'file1_code': row1['code'],
                    'file1_column': row1['column'],
                    'file1_row': row1['row_index'],
                    'similarity': 0,
                    'match_type': 'فقط در فایل 1'
                })
            return pd.DataFrame(), pd.DataFrame(non_matches)
        
        # بررسی هر کد از مجموعه اول
        for _, row1 in codes1.iterrows():
            code1 = row1['code']
            best_match = None
            best_score = 0
            match_type = ""
            
            # جستجوی کد در متن‌های مجموعه دوم
            found_in_text = False
            for _, row2 in codes2.iterrows():
                if self.is_code_in_text(code1, row2['original_text']):
                    best_match = row2
                    best_score = 100  # نمره کامل برای وجود در متن
                    match_type = "درون متن"
                    found_in_text = True
                    break
            
            # اگر در متن پیدا نشد، بررسی شباهت
            if not found_in_text:
                for _, row2 in codes2.iterrows():
                    code2 = row2['code']
                    # محاسبه شباهت با استفاده از فاصله لونشتاین (حساس به حروف بزرگ و کوچک)
                    score = fuzz.ratio(code1, code2)
                    
                    if score > best_score:
                        best_score = score
                        best_match = row2
                        match_type = "فازی"
            
            # اگر شباهت بالاتر از آستانه باشد یا در متن پیدا شده باشد، یک تطابق پیدا شده است
            if (best_score >= threshold or found_in_text) and best_match is not None:
                matches.append({
                    'file1_code': code1,
                    'file1_column': row1['column'],
                    'file1_row': row1['row_index'],
                    'file2_code': best_match['code'],
                    'file2_column': best_match['column'],
                    'file2_row': best_match['row_index'],
                    'file2_text': best_match['original_text'][:50] + ('...' if len(best_match['original_text']) > 50 else ''),
                    'similarity': best_score,
                    'match_type': match_type
                })
            else:
                non_matches.append({
                    'file1_code': code1,
                    'file1_column': row1['column'],
                    'file1_row': row1['row_index'],
                    'similarity': best_score if best_match else 0,
                    'match_type': 'فقط در فایل 1'
                })
        
        # بررسی کدهای مجموعه دوم که در مجموعه اول نیستند
        matched_codes2 = [match['file2_code'] for match in matches if match['match_type'] != "درون متن"]
        for _, row2 in codes2.iterrows():
            code2 = row2['code']
            if code2 not in matched_codes2:
                # بررسی آیا این کد در متن کدهای مجموعه اول وجود دارد
                found_in_text = False
                for _, row1 in codes1.iterrows():
                    if self.is_code_in_text(code2, row1['original_text']):
                        found_in_text = True
                        break
                
                # اگر در هیچ متنی از مجموعه اول پیدا نشد و شباهتش با هیچ کدی بالاتر از آستانه نبود
                if not found_in_text and not any(fuzz.ratio(code2, row1['code']) >= threshold for _, row1 in codes1.iterrows()):
                    non_matches.append({
                        'file2_code': code2,
                        'file2_column': row2['column'],
                        'file2_row': row2['row_index'],
                        'similarity': 0,
                        'match_type': 'فقط در فایل 2'
                    })
        
        # اصلاح ستون‌های تکراری در خروجی
        matches_df = pd.DataFrame(matches) if matches else pd.DataFrame()
        non_matches_df = pd.DataFrame(non_matches) if non_matches else pd.DataFrame()
        
        # چک و اصلاح ستون‌های تکراری
        matches_df = fix_duplicate_columns(matches_df)
        non_matches_df = fix_duplicate_columns(non_matches_df)
        
        return matches_df, non_matches_df
    
    def reconcile_platform_with_provider(self, platform_path, provider_path):
        """مغایرت‌گیری بین فایل پلتفرم و فایل ارائه‌دهنده با تطبیق دقیق و جستجو در متن"""
        # خواندن فایل‌ها
        print(f"در حال خواندن فایل پلتفرم: {platform_path}")
        platform_df = self.read_file(platform_path)
        
        print(f"در حال خواندن فایل ارائه‌دهنده: {provider_path}")
        provider_df = self.read_file(provider_path)
        
        # استخراج کدهای رهگیری
        print("در حال استخراج کدهای رهگیری از فایل پلتفرم...")
        platform_codes = self.extract_codes_from_platform(platform_df)
        
        print("در حال استخراج کدهای رهگیری از فایل ارائه‌دهنده...")
        provider_codes = self.extract_codes_from_provider(provider_df)
        
        # نمایش نمونه‌ای از کدهای استخراج شده برای عیب‌یابی
        if not platform_codes.empty:
            print("\nنمونه کدهای استخراج شده از فایل پلتفرم:")
            for code in platform_codes['code'].head(5).tolist():
                print(f"  - {code}")
        else:
            print("\nهیچ کد رهگیری از فایل پلتفرم استخراج نشد!")
        
        if not provider_codes.empty:
            print("\nنمونه کدهای استخراج شده از فایل ارائه‌دهنده:")
            for code in provider_codes['code'].head(5).tolist():
                print(f"  - {code}")
        else:
            print("\nهیچ کد رهگیری از فایل ارائه‌دهنده استخراج نشد!")
        
        # یافتن تطابق‌ها و عدم تطابق‌های دقیق و درون متن
        print("\nدر حال تطبیق کدهای رهگیری...")
        matches, non_matches = self.find_exact_matches(platform_codes, provider_codes)
        
        # نمایش نتایج
        print(f"\nتعداد کدهای رهگیری یافت شده در فایل پلتفرم: {len(platform_codes)}")
        print(f"تعداد کدهای رهگیری یافت شده در فایل ارائه‌دهنده: {len(provider_codes)}")
        print(f"تعداد تطابق‌ها: {len(matches)}")
        print(f"تعداد عدم تطابق‌ها: {len(non_matches)}")
        
        return {
            'platform': platform_df,
            'provider': provider_df,
            'platform_codes': platform_codes,
            'provider_codes': provider_codes,
            'matches': matches,
            'non_matches': non_matches
        }
    
    def reconcile_platform_with_provider_fuzzy(self, platform_path, provider_path, threshold=85):
        """مغایرت‌گیری بین فایل پلتفرم و فایل ارائه‌دهنده با تطبیق فازی و جستجو در متن"""
        # خواندن فایل‌ها
        print(f"در حال خواندن فایل پلتفرم: {platform_path}")
        platform_df = self.read_file(platform_path)
        
        print(f"در حال خواندن فایل ارائه‌دهنده: {provider_path}")
        provider_df = self.read_file(provider_path)
        
        # استخراج کدهای رهگیری
        print("در حال استخراج کدهای رهگیری از فایل پلتفرم...")
        platform_codes = self.extract_codes_from_platform(platform_df)
        
        print("در حال استخراج کدهای رهگیری از فایل ارائه‌دهنده...")
        provider_codes = self.extract_codes_from_provider(provider_df)
        
        # نمایش نمونه‌ای از کدهای استخراج شده برای عیب‌یابی
        if not platform_codes.empty:
            print("\nنمونه کدهای استخراج شده از فایل پلتفرم:")
            for code in platform_codes['code'].head(5).tolist():
                print(f"  - {code}")
        else:
            print("\nهیچ کد رهگیری از فایل پلتفرم استخراج نشد!")
        
        if not provider_codes.empty:
            print("\nنمونه کدهای استخراج شده از فایل ارائه‌دهنده:")
            for code in provider_codes['code'].head(5).tolist():
                print(f"  - {code}")
        else:
            print("\nهیچ کد رهگیری از فایل ارائه‌دهنده استخراج نشد!")
        
        # یافتن تطابق‌ها و عدم تطابق‌ها
        print(f"\nدر حال تطبیق فازی کدهای رهگیری با آستانه شباهت {threshold}%...")
        matches, non_matches = self.find_similar_codes(platform_codes, provider_codes, threshold)
        
        # نمایش نتایج
        print(f"\nتعداد کدهای رهگیری یافت شده در فایل پلتفرم: {len(platform_codes)}")
        print(f"تعداد کدهای رهگیری یافت شده در فایل ارائه‌دهنده: {len(provider_codes)}")
        print(f"تعداد تطابق‌های فازی و درون متن: {len(matches)}")
        print(f"تعداد عدم تطابق‌ها: {len(non_matches)}")
        
        return {
            'platform': platform_df,
            'provider': provider_df,
            'platform_codes': platform_codes,
            'provider_codes': provider_codes,
            'matches': matches,
            'non_matches': non_matches
        }
    
    def reconcile_files(self, file1_path, file2_path):
        """روش مغایرت‌گیری با تشخیص خودکار فایل پلتفرم"""
        # تشخیص اینکه کدام فایل پلتفرم است
        file1_name = os.path.basename(file1_path).lower()
        file2_name = os.path.basename(file2_path).lower()
        
        if 'platform' in file1_name:
            return self.reconcile_platform_with_provider(file1_path, file2_path)
        elif 'platform' in file2_name:
            return self.reconcile_platform_with_provider(file2_path, file1_path)
        else:
            # اگر نتوانستیم تشخیص دهیم، از روش معمولی استفاده می‌کنیم
            print("هشدار: فایل پلتفرم شناسایی نشد. از روش مغایرت‌گیری عمومی استفاده می‌شود.")
            return self._old_reconcile_files(file1_path, file2_path)
    
    def reconcile_files_fuzzy(self, file1_path, file2_path, threshold=85):
        """روش مغایرت‌گیری فازی با تشخیص خودکار فایل پلتفرم"""
        # تشخیص اینکه کدام فایل پلتفرم است
        file1_name = os.path.basename(file1_path).lower()
        file2_name = os.path.basename(file2_path).lower()
        
        if 'platform' in file1_name:
            return self.reconcile_platform_with_provider_fuzzy(file1_path, file2_path, threshold)
        elif 'platform' in file2_name:
            return self.reconcile_platform_with_provider_fuzzy(file2_path, file1_path, threshold)
        else:
            # اگر نتوانستیم تشخیص دهیم، از روش معمولی استفاده می‌کنیم
            print("هشدار: فایل پلتفرم شناسایی نشد. از روش مغایرت‌گیری فازی عمومی استفاده می‌شود.")
            return self._old_reconcile_files_fuzzy(file1_path, file2_path, threshold)
    
    def _old_reconcile_files(self, file1_path, file2_path):
        """نسخه قدیمی تابع مغایرت‌گیری برای حفظ سازگاری"""
        # خواندن فایل‌ها
        print(f"در حال خواندن فایل اول: {file1_path}")
        df1 = self.read_file(file1_path)
        
        print(f"در حال خواندن فایل دوم: {file2_path}")
        df2 = self.read_file(file2_path)
        
        # استخراج کدهای رهگیری
        print("در حال استخراج کدهای رهگیری از فایل اول...")
        codes1 = self.extract_potential_tracking_codes(df1)
        
        print("در حال استخراج کدهای رهگیری از فایل دوم...")
        codes2 = self.extract_potential_tracking_codes(df2)
        
       # نمایش نمونه‌ای از کدهای استخراج شده برای عیب‌یابی
        if not codes1.empty:
            print("\nنمونه کدهای استخراج شده از فایل اول:")
            for code in codes1['code'].head(5).tolist():
                print(f"  - {code}")
        
        if not codes2.empty:
            print("\nنمونه کدهای استخراج شده از فایل دوم:")
            for code in codes2['code'].head(5).tolist():
                print(f"  - {code}")
        
        # یافتن تطابق‌ها و عدم تطابق‌های دقیق
        print("\nدر حال تطبیق دقیق کدهای رهگیری...")
        matches, non_matches = self.find_exact_matches(codes1, codes2)
        
        # نمایش نتایج
        print(f"\nتعداد کدهای رهگیری یافت شده در فایل اول: {len(codes1)}")
        print(f"تعداد کدهای رهگیری یافت شده در فایل دوم: {len(codes2)}")
        print(f"تعداد تطابق‌های دقیق: {len(matches)}")
        print(f"تعداد عدم تطابق‌ها: {len(non_matches)}")
        
        return {
            'file1': df1,
            'file2': df2,
            'codes1': codes1,
            'codes2': codes2,
            'matches': matches,
            'non_matches': non_matches
        }
    
    def _old_reconcile_files_fuzzy(self, file1_path, file2_path, threshold=85):
        """نسخه قدیمی تابع مغایرت‌گیری فازی برای حفظ سازگاری"""
        # خواندن فایل‌ها
        print(f"در حال خواندن فایل اول: {file1_path}")
        df1 = self.read_file(file1_path)
        
        print(f"در حال خواندن فایل دوم: {file2_path}")
        df2 = self.read_file(file2_path)
        
        # استخراج کدهای رهگیری
        print("در حال استخراج کدهای رهگیری از فایل اول...")
        codes1 = self.extract_potential_tracking_codes(df1)
        
        print("در حال استخراج کدهای رهگیری از فایل دوم...")
        codes2 = self.extract_potential_tracking_codes(df2)
        
        # نمایش نمونه‌ای از کدهای استخراج شده برای عیب‌یابی
        if not codes1.empty:
            print("\nنمونه کدهای استخراج شده از فایل اول:")
            for code in codes1['code'].head(5).tolist():
                print(f"  - {code}")
        
        if not codes2.empty:
            print("\nنمونه کدهای استخراج شده از فایل دوم:")
            for code in codes2['code'].head(5).tolist():
                print(f"  - {code}")
        
        # یافتن تطابق‌ها و عدم تطابق‌ها
        print(f"\nدر حال تطبیق فازی کدهای رهگیری با آستانه شباهت {threshold}%...")
        matches, non_matches = self.find_similar_codes(codes1, codes2, threshold)
        
        # نمایش نتایج
        print(f"\nتعداد کدهای رهگیری یافت شده در فایل اول: {len(codes1)}")
        print(f"تعداد کدهای رهگیری یافت شده در فایل دوم: {len(codes2)}")
        print(f"تعداد تطابق‌های فازی: {len(matches)}")
        print(f"تعداد عدم تطابق‌ها: {len(non_matches)}")
        
        return {
            'file1': df1,
            'file2': df2,
            'codes1': codes1,
            'codes2': codes2,
            'matches': matches,
            'non_matches': non_matches
        }
    
    def gateway_specific_reconciliation(self, platform_path, provider_path, gateway_name):
        """
        مغایرت‌گیری با فیلتر کردن بر اساس نام gateway در فایل پلتفرم
        
        Parameters:
        -----------
        platform_path : str
            مسیر فایل پلتفرم
        provider_path : str
            مسیر فایل ارائه‌دهنده
        gateway_name : str
            نام gateway که می‌خواهیم فیلتر کنیم (مثلا: 'Payman', 'jibitcobank', 'ezpay', 'toman', 'vandar', 'jibit')
        """
        # خواندن فایل‌ها
        print(f"در حال خواندن فایل پلتفرم: {platform_path}")
        platform_df = self.read_file(platform_path)
        
        print(f"در حال خواندن فایل ارائه‌دهنده: {provider_path}")
        provider_df = self.read_file(provider_path)
        
        # بررسی وجود ستون gateway در فایل پلتفرم
        if 'gateway' not in platform_df.columns:
            print("خطا: ستون 'gateway' در فایل پلتفرم یافت نشد.")
            return None
        
        # فیلتر کردن داده‌های پلتفرم بر اساس gateway مورد نظر
        filtered_platform = platform_df[platform_df['gateway'].astype(str).str.lower() == gateway_name.lower()]
        
        if filtered_platform.empty:
            print(f"هیچ رکوردی با gateway '{gateway_name}' در فایل پلتفرم یافت نشد.")
            return None
        
        print(f"تعداد {len(filtered_platform)} رکورد با gateway '{gateway_name}' در فایل پلتفرم یافت شد.")
        
        # بررسی وجود ستون‌های کلیدی در فایل پلتفرم فیلتر شده
        platform_tracking_columns = [col for col in self.platform_tracking_columns if col in filtered_platform.columns]
        
        if not platform_tracking_columns:
            print(f"خطا: هیچ یک از ستون‌های مورد نظر {self.platform_tracking_columns} در فایل پلتفرم یافت نشد.")
            return None
        
        # جمع‌آوری کدهای رهگیری از فایل پلتفرم فیلتر شده
        platform_codes = []
        for col in platform_tracking_columns:
            print(f"استخراج کدها از ستون '{col}' در رکوردهای gateway '{gateway_name}'")
            for idx, value in filtered_platform[col].astype(str).items():
                if value and value != 'nan' and value != 'None':
                    # تبدیل هر نوع عدد بزرگ به رشته برای جلوگیری از 'int too big to convert'
                    if isinstance(value, (int, np.int64, np.int32)) and (value > 2**31-1 or value < -2**31):
                        value = str(value)
                        
                    platform_codes.append({
                        'code': value,
                        'column': col,
                        'row_index': idx,
                        'original_row_index': platform_df.index.get_loc(idx) if idx in platform_df.index else None
                    })
        
        if not platform_codes:
            print(f"هیچ کد رهگیری در رکوردهای gateway '{gateway_name}' یافت نشد.")
            return None
        
        # تبدیل به دیتافریم
        platform_codes_df = pd.DataFrame(platform_codes)
        
        # تطبیق ایمن برای اعداد بزرگ
        for col in platform_codes_df.select_dtypes(include=['int64', 'float64']).columns:
            platform_codes_df[col] = platform_codes_df[col].apply(safe_excel_value)
            
        print(f"تعداد {len(platform_codes_df)} کد از فایل پلتفرم برای gateway '{gateway_name}' استخراج شد.")
        print("نمونه کدها:")
        for code in platform_codes_df['code'].head(10).tolist():
            print(f"  - {code}")
        
        # جستجوی این کدها در تمام ستون‌های فایل ارائه‌دهنده
        matches = []
        non_matches = []
        
        # بررسی وجود هر کد پلتفرم در ارائه‌دهنده
        for _, row in platform_codes_df.iterrows():
            code = row['code']
            found = False
            
            # جستجو در تمام ستون‌های فایل ارائه‌دهنده
            for col in provider_df.columns:
                # جستجوی کد در هر سلول از ستون
                matching_rows = []
                for idx, cell_value in provider_df[col].astype(str).items():
                    if self.is_code_in_text(code, cell_value):
                        matching_rows.append((idx, cell_value))
                
                # اگر در این ستون کد پیدا شد، به تطابق‌ها اضافه کن
                for idx, cell_value in matching_rows:
                    found = True
                    # تبدیل هر نوع عدد بزرگ به رشته
                    if isinstance(cell_value, (int, np.int64, np.int32)) and (cell_value > 2**31-1 or cell_value < -2**31):
                        cell_value = str(cell_value)
                    
                    provider_row_num = None
                    try:
                        provider_row_num = provider_df.index.get_loc(idx) if idx in provider_df.index else None
                    except:
                        provider_row_num = str(idx)  # در صورت عدم امکان تبدیل، به رشته تبدیل می‌کنیم
                        
                    platform_row_num = row['original_row_index']
                    if isinstance(platform_row_num, (int, np.int64, np.int32)) and (platform_row_num > 2**31-1 or platform_row_num < -2**31):
                        platform_row_num = str(platform_row_num)
                    
                    matches.append({
                        'platform_code': code,
                        'platform_column': row['column'],
                        'platform_row': row['row_index'],
                        'platform_row_num': platform_row_num,
                        'provider_column': col,
                        'provider_row': idx,
                        'provider_value': str(cell_value)[:50] + ('...' if len(str(cell_value)) > 50 else ''),  # نمایش 50 کاراکتر اول
                        'provider_row_num': provider_row_num,
                        'match_type': 'درون متن' if len(str(cell_value)) > len(str(code)) else 'دقیق'
                    })
            
            # اگر کد در هیچ سلولی پیدا نشد، به عدم تطابق‌ها اضافه کن
            if not found:
                platform_row_num = row['original_row_index']
                if isinstance(platform_row_num, (int, np.int64, np.int32)) and (platform_row_num > 2**31-1 or platform_row_num < -2**31):
                    platform_row_num = str(platform_row_num)
                    
                non_matches.append({
                    'platform_code': code,
                    'platform_column': row['column'],
                    'platform_row': row['row_index'],
                    'platform_row_num': platform_row_num,
                    'match_type': 'فقط در پلتفرم'
                })
        
        # تبدیل به دیتافریم
        matches_df = pd.DataFrame(matches) if matches else pd.DataFrame()
        non_matches_df = pd.DataFrame(non_matches) if non_matches else pd.DataFrame()
        
        # چک و اصلاح ستون‌های تکراری
        matches_df = fix_duplicate_columns(matches_df)
        non_matches_df = fix_duplicate_columns(non_matches_df)
        
        # تطبیق ایمن برای اعداد بزرگ در نتایج
        for df in [matches_df, non_matches_df]:
            if not df.empty:
                for col in df.select_dtypes(include=['int64', 'float64']).columns:
                    df[col] = df[col].apply(safe_excel_value)
        
        # نمایش نتایج
        print(f"\nتعداد کدهای مطابقت داده شده: {len(matches_df)}")
        print(f"تعداد کدهای بدون مطابقت: {len(non_matches_df)}")
        
        return {
            'platform': platform_df,
            'provider': provider_df,
            'filtered_platform': filtered_platform,
            'platform_codes': platform_codes_df,
            'matches': matches_df,
            'non_matches': non_matches_df,
            'gateway_name': gateway_name
        }

    def generate_report(self, results, output_path="reconciliation_report.xlsx"):
        """
        تابع تولید گزارش اکسل با 5 شیت مشخص:
        1. filtered_platform - تمام ستون‌های پلتفرم فیلتر شده
        2. provider - تمام ستون‌های ارائه‌دهنده
        3. match - رکوردهای مچ شده با تمام ستون‌های هر دو طرف
        4. non_match_platform - رکوردهای مچ نشده پلتفرم با تمام ستون‌ها
        5. non_match_provider - رکوردهای مچ نشده ارائه‌دهنده با تمام ستون‌ها
        """
        if results is None:
            print("خطا: نتایج خالی است! گزارشی تولید نشد.")
            return False
        
        # ساخت دایرکتوری اگر وجود ندارد
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                print(f"خطا در ساخت دایرکتوری: {e}")
        
        try:
            import xlsxwriter
            
            print("\nدر حال ایجاد فایل Excel با 5 شیت...")
            
            # ایجاد کتاب کاری
            workbook = xlsxwriter.Workbook(output_path)
            
            # قالب‌بندی هدر
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D7E4BC',
                'border': 1
            })
            
            # --------- شیت 1: filtered_platform ---------
            if 'filtered_platform' in results and not results['filtered_platform'].empty:
                platform_df = results['filtered_platform'].copy()
                worksheet = workbook.add_worksheet("filtered_platform")
                
                # تبدیل همه نام‌های ستون به رشته و رفع ستون‌های تکراری
                column_names = self._get_unique_columns(platform_df)
                
                # نوشتن هدرها
                for col_idx, col_name in enumerate(column_names):
                    worksheet.write(0, col_idx, col_name, header_format)
                    worksheet.set_column(col_idx, col_idx, max(10, min(30, len(str(col_name)))))
                
                # نوشتن داده‌ها
                for row_idx, row in enumerate(platform_df.values):
                    for col_idx, cell_value in enumerate(row):
                        safe_value = self._safe_excel_value(cell_value)
                        worksheet.write(row_idx + 1, col_idx, safe_value)
                
                print(f"شیت filtered_platform با {len(platform_df)} رکورد ایجاد شد.")
            else:
                print("هشدار: دیتافریم filtered_platform وجود ندارد یا خالی است.")
                workbook.add_worksheet("filtered_platform")  # ایجاد شیت خالی
            
            # --------- شیت 2: provider ---------
            if 'provider' in results and not results['provider'].empty:
                provider_df = results['provider'].copy()
                worksheet = workbook.add_worksheet("provider")
                
                # تبدیل همه نام‌های ستون به رشته و رفع ستون‌های تکراری
                column_names = self._get_unique_columns(provider_df)
                
                # نوشتن هدرها
                for col_idx, col_name in enumerate(column_names):
                    worksheet.write(0, col_idx, col_name, header_format)
                    worksheet.set_column(col_idx, col_idx, max(10, min(30, len(str(col_name)))))
                
                # نوشتن داده‌ها
                for row_idx, row in enumerate(provider_df.values):
                    for col_idx, cell_value in enumerate(row):
                        safe_value = self._safe_excel_value(cell_value)
                        worksheet.write(row_idx + 1, col_idx, safe_value)
                
                print(f"شیت provider با {len(provider_df)} رکورد ایجاد شد.")
            else:
                print("هشدار: دیتافریم provider وجود ندارد یا خالی است.")
                workbook.add_worksheet("provider")  # ایجاد شیت خالی
            
            # --------- شیت 3: match ---------
            if 'matches' in results and not results['matches'].empty and 'filtered_platform' in results and 'provider' in results:
                match_worksheet = workbook.add_worksheet("match")
                matches_df = results['matches']
                platform_df = results['filtered_platform']
                provider_df = results['provider']
                
                # ایجاد دیتافریم ترکیبی برای مچ‌ها
                combined_records = []
                
                for _, match_row in matches_df.iterrows():
                    try:
                        # استخراج شماره ردیف‌ها
                        platform_row_idx = match_row.get('platform_row', match_row.get('file1_row', None))
                        provider_row_idx = match_row.get('provider_row', match_row.get('file2_row', None))
                        
                        if platform_row_idx is None or provider_row_idx is None:
                            print(f"هشدار: ردیف ناقص در مچ: {match_row}")
                            continue
                        
                        # تبدیل به int اگر رشته عددی است
                        if isinstance(platform_row_idx, str) and platform_row_idx.isdigit():
                            platform_row_idx = int(platform_row_idx)
                        if isinstance(provider_row_idx, str) and provider_row_idx.isdigit():
                            provider_row_idx = int(provider_row_idx)
                        
                        # پیدا کردن رکوردها
                        platform_record = self._get_record_by_index(platform_df, platform_row_idx)
                        provider_record = self._get_record_by_index(provider_df, provider_row_idx)
                        
                        if platform_record is None or provider_record is None:
                            print(f"هشدار: رکورد پیدا نشد - پلتفرم: {platform_row_idx}, ارائه‌دهنده: {provider_row_idx}")
                            continue
                        
                        # ترکیب رکوردها
                        combined_record = {}
                        
                        # افزودن اطلاعات مچ
                        combined_record['match_type'] = match_row.get('match_type', '')
                        combined_record['platform_code'] = match_row.get('platform_code', match_row.get('file1_code', ''))
                        combined_record['provider_code'] = match_row.get('provider_code', match_row.get('file2_code', ''))
                        
                        # افزودن تمام ستون‌های پلتفرم
                        for col, val in platform_record.items():
                            combined_record[f'platform_{col}'] = val
                        
                        # افزودن تمام ستون‌های ارائه‌دهنده
                        for col, val in provider_record.items():
                            combined_record[f'provider_{col}'] = val
                        
                        combined_records.append(combined_record)
                        
                    except Exception as e:
                        print(f"خطا در پردازش مچ: {str(e)}")
                
                # اگر هیچ رکوردی نداشتیم
                if not combined_records:
                    print("هشدار: هیچ مچی با اطلاعات کامل یافت نشد.")
                    # نوشتن هدر خالی
                    match_worksheet.write(0, 0, "هیچ مچی با اطلاعات کامل یافت نشد.", header_format)
                else:
                    # تبدیل به دیتافریم
                    combined_df = pd.DataFrame(combined_records)
                    
                    # تبدیل همه نام‌های ستون به رشته و رفع ستون‌های تکراری
                    column_names = self._get_unique_columns(combined_df)
                    
                    # نوشتن هدرها
                    for col_idx, col_name in enumerate(column_names):
                        match_worksheet.write(0, col_idx, col_name, header_format)
                        match_worksheet.set_column(col_idx, col_idx, max(10, min(30, len(str(col_name)))))
                    
                    # نوشتن داده‌ها
                    for row_idx, row in enumerate(combined_df.values):
                        for col_idx, cell_value in enumerate(row):
                            safe_value = self._safe_excel_value(cell_value)
                            match_worksheet.write(row_idx + 1, col_idx, safe_value)
                    
                    print(f"شیت match با {len(combined_df)} رکورد ایجاد شد.")
            else:
                print("هشدار: دیتافریم matches یا دیتافریم‌های مرتبط وجود ندارند یا خالی هستند.")
                workbook.add_worksheet("match")  # ایجاد شیت خالی
            
            # --------- شیت 4: non_match_platform ---------
            if 'non_matches' in results and not results['non_matches'].empty and 'filtered_platform' in results:
                non_match_platform_worksheet = workbook.add_worksheet("non_match_platform")
                non_matches_df = results['non_matches']
                platform_df = results['filtered_platform']
                
                # فیلتر کردن فقط مغایرت‌های پلتفرم
                platform_non_matches = non_matches_df[
                    (non_matches_df['match_type'] == 'فقط در فایل 1') | 
                    (non_matches_df['match_type'] == 'فقط در پلتفرم')
                ] if 'match_type' in non_matches_df.columns else pd.DataFrame()
                
                if platform_non_matches.empty:
                    print("هشدار: هیچ مغایرتی برای پلتفرم یافت نشد.")
                    non_match_platform_worksheet.write(0, 0, "هیچ مغایرتی برای پلتفرم یافت نشد.", header_format)
                else:
                    # ایجاد دیتافریم ترکیبی برای مغایرت‌های پلتفرم
                    platform_records = []
                    
                    for _, non_match_row in platform_non_matches.iterrows():
                        try:
                            # استخراج شماره ردیف
                            platform_row_idx = non_match_row.get('platform_row', non_match_row.get('file1_row', None))
                            
                            if platform_row_idx is None:
                                print(f"هشدار: ردیف ناقص در مغایرت پلتفرم: {non_match_row}")
                                continue
                            
                            # تبدیل به int اگر رشته عددی است
                            if isinstance(platform_row_idx, str) and platform_row_idx.isdigit():
                                platform_row_idx = int(platform_row_idx)
                            
                            # پیدا کردن رکورد
                            platform_record = self._get_record_by_index(platform_df, platform_row_idx)
                            
                            if platform_record is None:
                                print(f"هشدار: رکورد پلتفرم پیدا نشد - ردیف: {platform_row_idx}")
                                continue
                            
                            # افزودن اطلاعات مغایرت
                            platform_record['non_match_code'] = non_match_row.get('platform_code', non_match_row.get('file1_code', ''))
                            platform_record['non_match_type'] = non_match_row.get('match_type', '')
                            
                            platform_records.append(platform_record)
                            
                        except Exception as e:
                            print(f"خطا در پردازش مغایرت پلتفرم: {str(e)}")
                    
                    if not platform_records:
                        print("هشدار: هیچ مغایرت پلتفرم با اطلاعات کامل یافت نشد.")
                        non_match_platform_worksheet.write(0, 0, "هیچ مغایرت پلتفرم با اطلاعات کامل یافت نشد.", header_format)
                    else:
                        # تبدیل به دیتافریم
                        platform_non_matches_df = pd.DataFrame(platform_records)
                        
                        # تبدیل همه نام‌های ستون به رشته و رفع ستون‌های تکراری
                        column_names = self._get_unique_columns(platform_non_matches_df)
                        
                        # مرتب کردن ستون‌ها - ستون‌های مغایرت اول بیایند
                        if 'non_match_code' in column_names:
                            column_names.remove('non_match_code')
                            column_names.insert(0, 'non_match_code')
                        if 'non_match_type' in column_names:
                            column_names.remove('non_match_type')
                            column_names.insert(1, 'non_match_type')
                        
                        # نوشتن هدرها
                        for col_idx, col_name in enumerate(column_names):
                            non_match_platform_worksheet.write(0, col_idx, col_name, header_format)
                            non_match_platform_worksheet.set_column(col_idx, col_idx, max(10, min(30, len(str(col_name)))))
                        
                        # نوشتن داده‌ها
                        for row_idx, record in enumerate(platform_records):
                            for col_idx, col_name in enumerate(column_names):
                                cell_value = record.get(col_name, '')
                                safe_value = self._safe_excel_value(cell_value)
                                non_match_platform_worksheet.write(row_idx + 1, col_idx, safe_value)
                        
                        print(f"شیت non_match_platform با {len(platform_records)} رکورد ایجاد شد.")
            else:
                print("هشدار: دیتافریم non_matches یا دیتافریم‌های مرتبط وجود ندارند یا خالی هستند.")
                workbook.add_worksheet("non_match_platform")  # ایجاد شیت خالی
            
            # --------- شیت 5: non_match_provider ---------
            if 'non_matches' in results and not results['non_matches'].empty and 'provider' in results:
                non_match_provider_worksheet = workbook.add_worksheet("non_match_provider")
                non_matches_df = results['non_matches']
                provider_df = results['provider']
                
                # فیلتر کردن فقط مغایرت‌های ارائه‌دهنده
                provider_non_matches = non_matches_df[
                    (non_matches_df['match_type'] == 'فقط در فایل 2') | 
                    (non_matches_df['match_type'] == 'فقط در ارائه‌دهنده')
                ] if 'match_type' in non_matches_df.columns else pd.DataFrame()
                
                if provider_non_matches.empty:
                    print("هشدار: هیچ مغایرتی برای ارائه‌دهنده یافت نشد.")
                    non_match_provider_worksheet.write(0, 0, "هیچ مغایرتی برای ارائه‌دهنده یافت نشد.", header_format)
                else:
                    # ایجاد دیتافریم ترکیبی برای مغایرت‌های ارائه‌دهنده
                    provider_records = []
                    
                    for _, non_match_row in provider_non_matches.iterrows():
                        try:
                            # استخراج شماره ردیف
                            provider_row_idx = non_match_row.get('provider_row', non_match_row.get('file2_row', None))
                            
                            if provider_row_idx is None:
                                print(f"هشدار: ردیف ناقص در مغایرت ارائه‌دهنده: {non_match_row}")
                                continue
                            
                            # تبدیل به int اگر رشته عددی است
                            if isinstance(provider_row_idx, str) and provider_row_idx.isdigit():
                                provider_row_idx = int(provider_row_idx)
                            
                            # پیدا کردن رکورد
                            provider_record = self._get_record_by_index(provider_df, provider_row_idx)
                            
                            if provider_record is None:
                                print(f"هشدار: رکورد ارائه‌دهنده پیدا نشد - ردیف: {provider_row_idx}")
                                continue
                            
                            # افزودن اطلاعات مغایرت
                            provider_record['non_match_code'] = non_match_row.get('provider_code', non_match_row.get('file2_code', ''))
                            provider_record['non_match_type'] = non_match_row.get('match_type', '')
                            
                            provider_records.append(provider_record)
                            
                        except Exception as e:
                            print(f"خطا در پردازش مغایرت ارائه‌دهنده: {str(e)}")
                    
                    if not provider_records:
                        print("هشدار: هیچ مغایرت ارائه‌دهنده با اطلاعات کامل یافت نشد.")
                        non_match_provider_worksheet.write(0, 0, "هیچ مغایرت ارائه‌دهنده با اطلاعات کامل یافت نشد.", header_format)
                    else:
                        # تبدیل به دیتافریم
                        provider_non_matches_df = pd.DataFrame(provider_records)
                        
                        # تبدیل همه نام‌های ستون به رشته و رفع ستون‌های تکراری
                        column_names = self._get_unique_columns(provider_non_matches_df)
                        
                        # مرتب کردن ستون‌ها - ستون‌های مغایرت اول بیایند
                        if 'non_match_code' in column_names:
                            column_names.remove('non_match_code')
                            column_names.insert(0, 'non_match_code')
                        if 'non_match_type' in column_names:
                            column_names.remove('non_match_type')
                            column_names.insert(1, 'non_match_type')
                        
                        # نوشتن هدرها
                        for col_idx, col_name in enumerate(column_names):
                            non_match_provider_worksheet.write(0, col_idx, col_name, header_format)
                            non_match_provider_worksheet.set_column(col_idx, col_idx, max(10, min(30, len(str(col_name)))))
                        
                        # نوشتن داده‌ها
                        for row_idx, record in enumerate(provider_records):
                            for col_idx, col_name in enumerate(column_names):
                                cell_value = record.get(col_name, '')
                                safe_value = self._safe_excel_value(cell_value)
                                non_match_provider_worksheet.write(row_idx + 1, col_idx, safe_value)
                        
                        print(f"شیت non_match_provider با {len(provider_records)} رکورد ایجاد شد.")
            else:
                print("هشدار: دیتافریم non_matches یا دیتافریم‌های مرتبط وجود ندارند یا خالی هستند.")
                workbook.add_worksheet("non_match_provider")  # ایجاد شیت خالی
            
            # بستن کتاب کاری
            workbook.close()
            print(f"فایل Excel با موفقیت در {output_path} ذخیره شد.")
            return True
            
        except Exception as e:
            import traceback
            print(f"خطا در ایجاد فایل Excel: {e}")
            traceback.print_exc()
            return False
    
    def _get_unique_columns(self, df):
        """تبدیل ستون‌ها به رشته و ایجاد نام‌های یکتا برای ستون‌های تکراری"""
        if df is None or df.empty:
            return []
        
        # تبدیل همه نام‌های ستون به رشته
        column_names = [str(col) for col in df.columns]
        
        # بررسی ستون‌های تکراری
        if len(column_names) != len(set(column_names)):
            # ایجاد نام‌های یکتا
            new_columns = []
            seen = set()
            for col in column_names:
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
            
            # اعمال نام‌های جدید به دیتافریم
            df.columns = new_columns
            return new_columns
        
        return column_names
    
    def _safe_excel_value(self, value):
        """تبدیل ایمن مقادیر برای نوشتن در اکسل"""
        if value is None or pd.isna(value):
            return ""
        
        try:
            # برای اعداد بزرگ
            if isinstance(value, (int, np.int64, np.int32)) and (value > 2**31-1 or value < -2**31):
                return str(value)
            
            # برای اعداد اعشاری
            if isinstance(value, (float, np.floating)):
                if pd.isna(value):
                    return ""
                else:
                    return f'{value:.6f}'.rstrip('0').rstrip('.') if '.' in f'{value:.6f}' else f'{value:.0f}'
            
            # تبدیل به رشته برای سایر انواع
            return str(value)
        
        except Exception as e:
            print(f"خطا در تبدیل مقدار {value}: {e}")
            return str(value)
    
    def _get_record_by_index(self, df, idx):
        """پیدا کردن رکورد با استفاده از شاخص (با پشتیبانی از انواع مختلف شاخص)"""
        if df is None or df.empty:
            return None
        
        try:
            # حالت 1: شاخص در ایندکس دیتافریم وجود دارد
            if idx in df.index:
                return df.loc[idx].to_dict()
            
            # حالت 2: شاخص عددی موقعیتی است
            if isinstance(idx, (int, np.integer)) and 0 <= idx < len(df):
                return df.iloc[idx].to_dict()
            
            # حالت 3: شاخص عددی است اما خارج از محدوده است
            print(f"هشدار: شاخص {idx} خارج از محدوده دیتافریم با طول {len(df)} است.")
            return None
            
        except Exception as e:
            print(f"خطا در پیدا کردن رکورد با شاخص {idx}: {e}")
            return None

    # تابع مخصوص برای ezpay
    def simple_ezpay_fix(self, platform_path, provider_path, output_dir=None):
        """
        ساده‌ترین راه حل ممکن برای ezpay که فقط فایل‌های CSV تولید می‌کند - اصلاح شده
        
        Parameters:
        -----------
        platform_path : str
            مسیر فایل پلتفرم
        provider_path : str
            مسیر فایل ارائه‌دهنده
        output_dir : str, optional
            دایرکتوری خروجی. اگر None باشد، در همان دایرکتوری فایل پلتفرم ذخیره می‌شود.
        """
        import os
        import pandas as pd
        import re
        
        print(f"شروع مغایرت‌گیری ezpay با روش ساده اصلاح شده...")
        
        # تعیین دایرکتوری خروجی
        if output_dir is None:
            output_dir = os.path.dirname(platform_path)
        
        # اطمینان از وجود دایرکتوری
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # خواندن فایل‌ها
        try:
            print(f"خواندن فایل پلتفرم: {platform_path}")
            platform_df = pd.read_csv(platform_path, dtype=str)  # همه ستون‌ها را به صورت رشته می‌خوانیم
            
            print(f"خواندن فایل ارائه‌دهنده: {provider_path}")
            provider_df = pd.read_csv(provider_path, dtype=str)  # همه ستون‌ها را به صورت رشته می‌خوانیم
        except Exception as e:
            print(f"خطا در خواندن فایل‌ها: {e}")
            # تلاش با روش‌های دیگر خواندن
            try:
                platform_df = self.read_file(platform_path)
                provider_df = self.read_file(provider_path)
                # تبدیل تمام ستون‌ها به رشته
                for col in platform_df.columns:
                    platform_df[col] = platform_df[col].astype(str)
                for col in provider_df.columns:
                    provider_df[col] = provider_df[col].astype(str)
            except Exception as e2:
                print(f"خطای دوم در خواندن فایل‌ها: {e2}")
                return None
        
        # فیلتر کردن برای ezpay
        try:
            # تبدیل نام‌های ستون به رشته برای جلوگیری از خطا
            platform_df.columns = [str(col) for col in platform_df.columns]
            provider_df.columns = [str(col) for col in provider_df.columns]
            
            # بررسی و اصلاح ستون‌های تکراری
            platform_df = fix_duplicate_columns(platform_df)
            provider_df = fix_duplicate_columns(provider_df)
            
            if 'gateway' in platform_df.columns:
                filtered_platform = platform_df[platform_df['gateway'].str.lower() == 'ezpay']
                print(f"تعداد {len(filtered_platform)} رکورد با gateway 'ezpay' یافت شد.")
            else:
                print("ستون gateway یافت نشد. از تمام داده‌ها استفاده می‌شود.")
                filtered_platform = platform_df
        except Exception as e:
            print(f"خطا در فیلتر کردن: {e}")
            return None
        
        # ذخیره فایل‌های اصلی به عنوان CSV
        platform_csv = os.path.join(output_dir, "platform_ezpay.csv")
        filtered_platform.to_csv(platform_csv, index=False, encoding='utf-8-sig')
        print(f"فایل پلتفرم فیلتر شده در {platform_csv} ذخیره شد.")
        
        provider_csv = os.path.join(output_dir, "provider_ezpay.csv")
        provider_df.to_csv(provider_csv, index=False, encoding='utf-8-sig')
        print(f"فایل ارائه‌دهنده در {provider_csv} ذخیره شد.")
        
        # جستجوی کدهای ezpay
        matches = []
        non_matches = []
        
        # ستون‌هایی که باید بررسی شوند
        platform_columns = [
            'gateway_tracking_code', 
            'gateway_identifier', 
            'meta_data_1'
        ]
        
        columns_to_check = [col for col in platform_columns if col in filtered_platform.columns]
        
        # الگوی ezpay (کد با ez شروع می‌شود)
        pattern = re.compile(r'^ez\d+', re.IGNORECASE)
        
        print(f"ستون‌های مورد بررسی: {columns_to_check}")
        
        # جستجوی کدها
        total_codes = 0
        
        for col in columns_to_check:
            for idx, value in filtered_platform[col].items():
                if pd.notna(value) and pattern.match(str(value)):
                    total_codes += 1
                    code = str(value).strip()
                    found = False
                    
                    # جستجو در ارائه‌دهنده
                    for p_col in provider_df.columns:
                        for p_idx, p_value in provider_df[p_col].items():
                            if code in str(p_value):
                                found = True
                                matches.append({
                                    'platform_index': str(idx),
                                    'platform_column': str(col),
                                    'platform_code': str(code),
                                    'provider_index': str(p_idx),
                                    'provider_column': str(p_col),
                                    'provider_value': str(p_value)[:100],
                                    'match_type': 'found'
                                })
                    
                    if not found:
                        non_matches.append({
                            'platform_index': str(idx),
                            'platform_column': str(col),
                            'platform_code': str(code),
                            'match_type': 'not_found'
                        })
        
        print(f"تعداد کل کدهای ezpay یافت شده: {total_codes}")
        print(f"تعداد تطابق‌ها: {len(matches)}")
        print(f"تعداد عدم تطابق‌ها: {len(non_matches)}")
        
        # تبدیل به دیتافریم
        matches_df = pd.DataFrame(matches) if matches else pd.DataFrame()
        non_matches_df = pd.DataFrame(non_matches) if non_matches else pd.DataFrame()
        
        # بررسی و اصلاح ستون‌های تکراری
        matches_df = fix_duplicate_columns(matches_df)
        non_matches_df = fix_duplicate_columns(non_matches_df)
        
        # ذخیره نتایج
        if not matches_df.empty:
            matches_csv = os.path.join(output_dir, "ezpay_matches.csv")
            matches_df.to_csv(matches_csv, index=False, encoding='utf-8-sig')
            print(f"فایل تطابق‌ها در {matches_csv} ذخیره شد.")
        
        if not non_matches_df.empty:
            non_matches_csv = os.path.join(output_dir, "ezpay_non_matches.csv")
            non_matches_df.to_csv(non_matches_csv, index=False, encoding='utf-8-sig')
            print(f"فایل عدم تطابق‌ها در {non_matches_csv} ذخیره شد.")
        
        print("عملیات با موفقیت انجام شد.")
        
        return {
            'matches': matches_df,
            'non_matches': non_matches_df,
            'platform': filtered_platform,
            'provider': provider_df
        }