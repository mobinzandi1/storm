import pandas as pd
import numpy as np
import re
import os
import json
from fuzzywuzzy import fuzz, process
import xlsxwriter
import tempfile
import streamlit as st

class SmartReconciliationSystem:
    def __init__(self):
        # الگوهای جستجوی کد رهگیری - به‌روزرسانی با توجه به داده‌ها
        self.tracking_patterns = [
            r'\b[a-zA-Z0-9]{6,30}\b',  # کدهای مثل Z17yRAnW
            r'\bTransfer\s+from\s+[A-Za-z]+\s+to\s+[A-Za-z]+\b',  # مثل Transfer from Mellat to Paya
            r'\b\d{6,30}\b',  # اعداد بلند (مثل 10000000000)
            r'[A-Za-z0-9-]+-[A-Za-z0-9-]+',  # فرمت‌های ترکیبی
            r'TR-\d+',  # مثال: TR-12345678
            r'TRK\d+',  # مثال: TRK12345678
            r'wallex-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+',  # UUID با پیشوند wallex
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
            try:
                return pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                return pd.read_csv(file_path, encoding='windows-1256')
        
        elif file_type in ['.xlsx', '.xls']:
            return pd.read_excel(file_path)
        
        elif file_type == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                return pd.DataFrame(data)
            else:
                return self.extract_from_complex_json(data)
        
        else:
            raise ValueError(f"فرمت فایل {file_type} پشتیبانی نمی‌شود")
    
    def extract_from_complex_json(self, data):
        """استخراج داده‌ها از JSON با ساختار پیچیده"""
        flat_data = []
        
        def flatten_json(json_obj, prefix=""):
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
        """استخراج کدهای رهگیری احتمالی از دیتافریم"""
        tracking_codes = []
        
        df_unique = df.drop_duplicates(keep='first')
        print(f"تعداد ردیف‌ها قبل از حذف داپلیکیت: {len(df)}, بعد از حذف داپلیکیت: {len(df_unique)}")
        
        if is_platform:
            columns_to_check = [col for col in self.platform_tracking_columns if col in df_unique.columns]
            print(f"بررسی ستون‌های خاص پلتفرم: {columns_to_check}")
        else:
            columns_to_check = df_unique.columns
            print(f"بررسی تمام ستون‌ها در ارائه‌دهنده: {columns_to_check.tolist()}")
        
        seen_codes = set()
        for column in columns_to_check:
            print(f"در حال بررسی ستون: {column}")
            for idx, value in df_unique[column].astype(str).items():
                if value in ['nan', 'None', '']:
                    continue
                
                normalized_value = self.simple_normalize(value) if any('\u0600' <= c <= '\u06FF' for c in value) else value
                
                for pattern in self.tracking_patterns:
                    matches = re.finditer(pattern, normalized_value)
                    for match in matches:
                        tracking_code = match.group().strip()
                        if tracking_code and tracking_code not in seen_codes:
                            tracking_codes.append({
                                'code': tracking_code,
                                'column': column,
                                'row_index': idx,
                                'original_text': value
                            })
                            seen_codes.add(tracking_code)
                            print(f"کد رهگیری یافت شد (بدون داپلیکیت): {tracking_code} در ستون {column}، ردیف {idx}")
        
        result_df = pd.DataFrame(tracking_codes) if tracking_codes else pd.DataFrame(columns=['code', 'column', 'row_index', 'original_text'])
        print(f"تعداد کدهای استخراج‌شده (بدون داپلیکیت): {len(result_df)}")
        return result_df
    
    def extract_codes_from_platform(self, df):
        """استخراج کدهای رهگیری از فایل پلتفرم"""
        return self.extract_potential_tracking_codes(df, is_platform=True)
    
    def extract_codes_from_provider(self, df):
        """استخراج کدهای رهگیری از فایل ارائه‌دهنده"""
        return self.extract_potential_tracking_codes(df, is_platform=False)
    
    def is_code_in_text(self, code, text):
        """بررسی وجود کد در متن"""
        return str(code) in str(text)
    
    def find_exact_matches(self, codes1, codes2):
        """یافتن کدهای کاملاً یکسان بین دو مجموعه"""
        matches = []
        non_matches_file1 = []
        non_matches_file2 = []
        
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
        
        matched_codes1 = set()
        
        for _, row1 in codes1.iterrows():
            code1 = row1['code']
            found = False
            
            for _, row2 in codes2.iterrows():
                code2 = row2['code']
                original_text2 = row2['original_text']
                
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
                    matched_codes1.add(code1)
                    break
            
            if not found:
                non_matches_file1.append({
                    'file1_code': code1,
                    'file1_column': row1['column'],
                    'file1_row': row1['row_index'],
                    'match_type': 'فقط در فایل 1'
                })
        
        matched_codes2 = set(match['file2_code'] for match in matches)
        for _, row2 in codes2.iterrows():
            code2 = row2['code']
            if code2 not in matched_codes2:
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
        
        non_matches = non_matches_file1 + non_matches_file2
        
        matches_df = pd.DataFrame(matches) if matches else pd.DataFrame()
        non_matches_df = pd.DataFrame(non_matches) if non_matches else pd.DataFrame()
        
        matches_df = self.fix_duplicate_columns(matches_df)
        non_matches_df = self.fix_duplicate_columns(non_matches_df)
        
        return matches_df, non_matches_df
    
    def find_similar_codes(self, codes1, codes2, threshold=85):
        """یافتن کدهای مشابه با استفاده از فاصله ویرایشی"""
        matches = []
        non_matches = []
        
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
        
        for _, row1 in codes1.iterrows():
            code1 = row1['code']
            best_match = None
            best_score = 0
            match_type = ""
            
            found_in_text = False
            for _, row2 in codes2.iterrows():
                if self.is_code_in_text(code1, row2['original_text']):
                    best_match = row2
                    best_score = 100
                    match_type = "درون متن"
                    found_in_text = True
                    break
            
            if not found_in_text:
                for _, row2 in codes2.iterrows():
                    code2 = row2['code']
                    score = fuzz.ratio(code1, code2)
                    if score > best_score:
                        best_score = score
                        best_match = row2
                        match_type = "فازی"
            
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
        
        matched_codes2 = [match['file2_code'] for match in matches if match['match_type'] != "درون متن"]
        for _, row2 in codes2.iterrows():
            code2 = row2['code']
            if code2 not in matched_codes2:
                found_in_text = False
                for _, row1 in codes1.iterrows():
                    if self.is_code_in_text(code2, row1['original_text']):
                        found_in_text = True
                        break
                
                if not found_in_text and not any(fuzz.ratio(code2, row1['code']) >= threshold for _, row1 in codes1.iterrows()):
                    non_matches.append({
                        'file2_code': code2,
                        'file2_column': row2['column'],
                        'file2_row': row2['row_index'],
                        'similarity': 0,
                        'match_type': 'فقط در فایل 2'
                    })
        
        matches_df = pd.DataFrame(matches) if matches else pd.DataFrame()
        non_matches_df = pd.DataFrame(non_matches) if non_matches else pd.DataFrame()
        
        matches_df = self.fix_duplicate_columns(matches_df)
        non_matches_df = self.fix_duplicate_columns(non_matches_df)
        
        return matches_df, non_matches_df
    
    def reconcile_platform_with_provider(self, platform_path, provider_path):
        """مغایرت‌گیری بین فایل پلتفرم و فایل ارائه‌دهنده"""
        print(f"در حال خواندن فایل پلتفرم: {platform_path}")
        platform_df = self.read_file(platform_path)
        
        print(f"در حال خواندن فایل ارائه‌دهنده: {provider_path}")
        provider_df = self.read_file(provider_path)
        
        print("در حال استخراج کدهای رهگیری از فایل پلتفرم...")
        platform_codes = self.extract_codes_from_platform(platform_df)
        
        print("در حال استخراج کدهای رهگیری از فایل ارائه‌دهنده...")
        provider_codes = self.extract_codes_from_provider(provider_df)
        
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
        
        print("\nدر حال تطبیق کدهای رهگیری...")
        matches, non_matches = self.find_exact_matches(platform_codes, provider_codes)
        
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
        """مغایرت‌گیری فازی بین فایل پلتفرم و ارائه‌دهنده"""
        print(f"در حال خواندن فایل پلتفرم: {platform_path}")
        platform_df = self.read_file(platform_path)
        
        print(f"در حال خواندن فایل ارائه‌دهنده: {provider_path}")
        provider_df = self.read_file(provider_path)
        
        print("در حال استخراج کدهای رهگیری از فایل پلتفرم...")
        platform_codes = self.extract_codes_from_platform(platform_df)
        
        print("در حال استخراج کدهای رهگیری از فایل ارائه‌دهنده...")
        provider_codes = self.extract_codes_from_provider(provider_df)
        
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
        
        print(f"\nدر حال تطبیق فازی کدهای رهگیری با آستانه شباهت {threshold}%...")
        matches, non_matches = self.find_similar_codes(platform_codes, provider_codes, threshold)
        
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
        """مغایرت‌گیری عمومی با تشخیص خودکار فایل پلتفرم"""
        file1_name = os.path.basename(file1_path).lower()
        file2_name = os.path.basename(file2_path).lower()
        
        if 'platform' in file1_name:
            return self.reconcile_platform_with_provider(file1_path, file2_path)
        elif 'platform' in file2_name:
            return self.reconcile_platform_with_provider(file2_path, file1_path)
        else:
            print("هشدار: فایل پلتفرم شناسایی نشد. از روش مغایرت‌گیری عمومی استفاده می‌شود.")
            return self._old_reconcile_files(file1_path, file2_path)
    
    def reconcile_files_fuzzy(self, file1_path, file2_path, threshold=85):
        """مغایرت‌گیری فازی عمومی با تشخیص خودکار فایل پلتفرم"""
        file1_name = os.path.basename(file1_path).lower()
        file2_name = os.path.basename(file2_path).lower()
        
        if 'platform' in file1_name:
            return self.reconcile_platform_with_provider_fuzzy(file1_path, file2_path, threshold)
        elif 'platform' in file2_name:
            return self.reconcile_platform_with_provider_fuzzy(file2_path, file1_path, threshold)
        else:
            print("هشدار: فایل پلتفرم شناسایی نشد. از روش مغایرت‌گیری فازی عمومی استفاده می‌شود.")
            return self._old_reconcile_files_fuzzy(file1_path, file2_path, threshold)
    
    def _old_reconcile_files(self, file1_path, file2_path):
        """نسخه قدیمی تابع مغایرت‌گیری"""
        print(f"در حال خواندن فایل اول: {file1_path}")
        df1 = self.read_file(file1_path)
        
        print(f"در حال خواندن فایل دوم: {file2_path}")
        df2 = self.read_file(file2_path)
        
        print("در حال استخراج کدهای رهگیری از فایل اول...")
        codes1 = self.extract_potential_tracking_codes(df1)
        
        print("در حال استخراج کدهای رهگیری از فایل دوم...")
        codes2 = self.extract_potential_tracking_codes(df2)
        
        if not codes1.empty:
            print("\nنمونه کدهای استخراج شده از فایل اول:")
            for code in codes1['code'].head(5).tolist():
                print(f"  - {code}")
        
        if not codes2.empty:
            print("\nنمونه کدهای استخراج شده از فایل دوم:")
            for code in codes2['code'].head(5).tolist():
                print(f"  - {code}")
        
        print("\nدر حال تطبیق دقیق کدهای رهگیری...")
        matches, non_matches = self.find_exact_matches(codes1, codes2)
        
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
        """نسخه قدیمی تابع مغایرت‌گیری فازی"""
        print(f"در حال خواندن فایل اول: {file1_path}")
        df1 = self.read_file(file1_path)
        
        print(f"در حال خواندن فایل دوم: {file2_path}")
        df2 = self.read_file(file2_path)
        
        print("در حال استخراج کدهای رهگیری از فایل اول...")
        codes1 = self.extract_potential_tracking_codes(df1)
        
        print("در حال استخراج کدهای رهگیری از فایل دوم...")
        codes2 = self.extract_potential_tracking_codes(df2)
        
        if not codes1.empty:
            print("\nنمونه کدهای استخراج شده از فایل اول:")
            for code in codes1['code'].head(5).tolist():
                print(f"  - {code}")
        
        if not codes2.empty:
            print("\nنمونه کدهای استخراج شده از فایل دوم:")
            for code in codes2['code'].head(5).tolist():
                print(f"  - {code}")
        
        print(f"\nدر حال تطبیق فازی کدهای رهگیری با آستانه شباهت {threshold}%...")
        matches, non_matches = self.find_similar_codes(codes1, codes2, threshold)
        
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
        """
        print(f"در حال خواندن فایل پلتفرم: {platform_path}")
        platform_df = self.read_file(platform_path)
        
        print(f"در حال خواندن فایل ارائه‌دهنده: {provider_path}")
        provider_df = self.read_file(provider_path)
        
        # اضافه کردن ستون ردیف برای پیگیری ساده‌تر
        provider_df['_row_number'] = np.arange(len(provider_df))
        provider_df['_matched'] = False  # افزودن یک ستون برای علامت‌گذاری رکوردهای تطبیق شده
        
        print("\nستون‌های فایل ارائه‌دهنده:")
        for col in provider_df.columns:
            print(f"ستون {col}: {provider_df[col].drop_duplicates().head().to_string()}")
        
        if 'gateway' not in platform_df.columns:
            print("خطا: ستون 'gateway' در فایل پلتفرم یافت نشد.")
            return None
        
        filtered_platform = platform_df[platform_df['gateway'].astype(str).str.lower() == gateway_name.lower()]
        
        if filtered_platform.empty:
            print(f"هیچ رکوردی با gateway '{gateway_name}' در فایل پلتفرم یافت نشد.")
            return None
        
        print(f"تعداد {len(filtered_platform)} رکورد با gateway '{gateway_name}' در فایل پلتفرم یافت شد.")
        
        platform_tracking_columns = [col for col in self.platform_tracking_columns if col in filtered_platform.columns]
        
        if not platform_tracking_columns:
            print(f"خطا: هیچ یک از ستون‌های مورد نظر {self.platform_tracking_columns} در فایل پلتفرم یافت نشد.")
            return None
        
        platform_codes = []
        for col in platform_tracking_columns:
            print(f"استخراج کدها از ستون '{col}' در رکوردهای gateway '{gateway_name}'")
            for idx, value in filtered_platform[col].astype(str).items():
                if value and value != 'nan' and value != 'None':
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
        
        platform_codes_df = pd.DataFrame(platform_codes)
        
        for col in platform_codes_df.select_dtypes(include=['int64', 'float64']).columns:
            platform_codes_df[col] = platform_codes_df[col].apply(self.safe_excel_value)
            
        print(f"تعداد {len(platform_codes_df)} کد از فایل پلتفرم برای gateway '{gateway_name}' استخراج شد.")
        print("نمونه کدها:")
        for code in platform_codes_df['code'].head(10).tolist():
            print(f"  - {code}")
        
        print("\nاستخراج کدهای رهگیری از فایل ارائه‌دهنده...")
        provider_codes = self.extract_codes_from_provider(provider_df)
        
        matches = []
        non_matches = []
        
        for _, row in platform_codes_df.iterrows():
            code = row['code']
            found = False
            
            for col in provider_df.columns:
                matching_rows = []
                for idx, cell_value in provider_df[col].astype(str).items():
                    if self.is_code_in_text(code, cell_value):
                        matching_rows.append((idx, cell_value))
                
                for idx, cell_value in matching_rows:
                    found = True
                    # علامت‌گذاری این رکورد به عنوان تطبیق شده
                    provider_df.loc[idx, '_matched'] = True
                    
                    if isinstance(cell_value, (int, np.int64, np.int32)) and (cell_value > 2**31-1 or cell_value < -2**31):
                        cell_value = str(cell_value)
                    
                    provider_row_num = provider_df.loc[idx, '_row_number'] if idx in provider_df.index else str(idx)
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
                        'provider_value': str(cell_value)[:50] + ('...' if len(str(cell_value)) > 50 else ''),
                        'provider_row_num': provider_row_num,
                        'match_type': 'درون متن' if len(str(cell_value)) > len(str(code)) else 'دقیق'
                    })
            
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
        
        # یافتن رکوردهای ارائه‌دهنده که تطبیق نشده‌اند
        unmatched_provider = provider_df[provider_df['_matched'] == False]
        print(f"تعداد رکوردهای بدون تطابق در ارائه‌دهنده: {len(unmatched_provider)}")
        
        # تبدیل رکوردهای بدون تطابق به فرمت مورد نیاز
        provider_non_matches = []
        for idx, row in unmatched_provider.iterrows():
            row_num = row['_row_number']
            row_codes = []
            
            # بررسی اگر این ردیف در provider_codes وجود دارد
            if not provider_codes.empty:
                matched_codes = provider_codes[provider_codes['row_index'] == idx]
                if not matched_codes.empty:
                    for _, code_row in matched_codes.iterrows():
                        row_codes.append(code_row['code'])
            
            # اگر کد پیدا نشد، از اولین ستون غیر _row_number و _matched استفاده کنیم
            if not row_codes:
                for col in provider_df.columns:
                    if col not in ['_row_number', '_matched']:
                        value = row[col]
                        if pd.notna(value) and str(value).strip() != '':
                            row_codes.append(str(value)[:30])  # محدود به 30 کاراکتر اول
                            break
            
            for code in row_codes:
                provider_non_matches.append({
                    'file2_code': code,
                    'file2_column': 'N/A' if 'column' not in locals() else col,
                    'file2_row': idx,
                    'file2_row_num': row_num,
                    'match_type': 'فقط در ارائه‌دهنده'
                })
        
        # اگر هیچ کدی وجود نداشت، حداقل یک ردیف برای هر رکورد بدون تطابق اضافه کنیم
        if not provider_non_matches and not unmatched_provider.empty:
            for idx, row in unmatched_provider.iterrows():
                provider_non_matches.append({
                    'file2_code': 'NO_CODE',
                    'file2_column': 'N/A',
                    'file2_row': idx,
                    'file2_row_num': row['_row_number'],
                    'match_type': 'فقط در ارائه‌دهنده'
                })
        
        matches_df = pd.DataFrame(matches) if matches else pd.DataFrame()
        non_matches_df = pd.DataFrame(non_matches + provider_non_matches) if (non_matches or provider_non_matches) else pd.DataFrame()
        
        matches_df = self.fix_duplicate_columns(matches_df)
        non_matches_df = self.fix_duplicate_columns(non_matches_df)
        
        for df in [matches_df, non_matches_df]:
            if not df.empty:
                for col in df.select_dtypes(include=['int64', 'float64']).columns:
                    df[col] = df[col].apply(self.safe_excel_value)
        
        print(f"\nتعداد کدهای مطابقت داده شده: {len(matches_df)}")
        print(f"تعداد کدهای بدون مطابقت: {len(non_matches_df)}")
        
        # حذف ستون‌های اضافی از provider_df
        if '_row_number' in provider_df.columns:
            provider_df = provider_df.drop('_row_number', axis=1)
        if '_matched' in provider_df.columns:
            provider_df = provider_df.drop('_matched', axis=1)
        
        return {
            'platform': platform_df,
            'provider': provider_df,
            'filtered_platform': filtered_platform,
            'platform_codes': platform_codes_df,
            'provider_codes': provider_codes,
            'matches': matches_df,
            'non_matches': non_matches_df,
            'gateway_name': gateway_name,
            'unmatched_provider': unmatched_provider.drop(['_row_number', '_matched'], axis=1)
        }

    def safe_excel_value(self, value):
        """تبدیل ایمن مقادیر برای اکسل"""
        if isinstance(value, (int, np.int64, np.int32)) and (value > 2**31-1 or value < -2**31):
            return str(value)
        return value

    def simple_normalize(self, text):
        """نرمال‌سازی متن فارسی"""
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
            '‌': ' ',
            '\u200c': ' '
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def fix_duplicate_columns(self, df):
        """رفع ستون‌های تکراری در دیتافریم"""
        if df is None or df.empty:
            return df
        columns = [str(col) for col in df.columns]
        if len(columns) != len(set(columns)):
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
            df_fixed = df.copy()
            df_fixed.columns = new_columns
            print("ستون‌های تکراری اصلاح شدند.")
            return df_fixed
        return df

    def generate_report(self, results, output_path="reconciliation_report.xlsx"):
        """تولید گزارش اکسل با 5 شیت"""
        if results is None:
            print("خطا: نتایج خالی است! گزارشی تولید نشد.")
            return False
        
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                print(f"خطا در ساخت دایرکتوری: {e}")
        
        try:
            import xlsxwriter
            print("\nدر حال ایجاد فایل Excel با 5 شیت...")
            
            workbook = xlsxwriter.Workbook(output_path)
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D7E4BC',
                'border': 1
            })
            
            # شیت 1: filtered_platform
            if 'filtered_platform' in results and not results['filtered_platform'].empty:
                platform_df = results['filtered_platform'].copy()
                worksheet = workbook.add_worksheet("filtered_platform")
                column_names = self._get_unique_columns(platform_df)
                for col_idx, col_name in enumerate(column_names):
                    worksheet.write(0, col_idx, col_name, header_format)
                    worksheet.set_column(col_idx, col_idx, max(10, min(30, len(str(col_name)))))
                for row_idx, row in enumerate(platform_df.values):
                    for col_idx, cell_value in enumerate(row):
                        safe_value = self._safe_excel_value(cell_value)
                        worksheet.write(row_idx + 1, col_idx, safe_value)
                print(f"شیت filtered_platform با {len(platform_df)} رکورد ایجاد شد.")
            else:
                print("هشدار: دیتافریم filtered_platform وجود ندارد یا خالی است.")
                workbook.add_worksheet("filtered_platform")
            
            # شیت 2: provider
            if 'provider' in results and not results['provider'].empty:
                provider_df = results['provider'].copy()
                worksheet = workbook.add_worksheet("provider")
                column_names = self._get_unique_columns(provider_df)
                for col_idx, col_name in enumerate(column_names):
                    worksheet.write(0, col_idx, col_name, header_format)
                    worksheet.set_column(col_idx, col_idx, max(10, min(30, len(str(col_name)))))
                for row_idx, row in enumerate(provider_df.values):
                    for col_idx, cell_value in enumerate(row):
                        safe_value = self._safe_excel_value(cell_value)
                        worksheet.write(row_idx + 1, col_idx, safe_value)
                print(f"شیت provider با {len(provider_df)} رکورد ایجاد شد.")
            else:
                print("هشدار: دیتافریم provider وجود ندارد یا خالی است.")
                workbook.add_worksheet("provider")
            
            # شیت 3: match
            if 'matches' in results and not results['matches'].empty and 'filtered_platform' in results and 'provider' in results:
                match_worksheet = workbook.add_worksheet("match")
                matches_df = results['matches']
                platform_df = results['filtered_platform']
                provider_df = results['provider']
                
                combined_records = []
                for _, match_row in matches_df.iterrows():
                    try:
                        platform_row_idx = match_row.get('platform_row', match_row.get('file1_row', None))
                        provider_row_idx = match_row.get('provider_row', match_row.get('file2_row', None))
                        
                        if platform_row_idx is None or provider_row_idx is None:
                            print(f"هشدار: ردیف ناقص در مچ: {match_row}")
                            continue
                        
                        if isinstance(platform_row_idx, str) and platform_row_idx.isdigit():
                            platform_row_idx = int(platform_row_idx)
                        if isinstance(provider_row_idx, str) and provider_row_idx.isdigit():
                            provider_row_idx = int(provider_row_idx)
                        
                        platform_record = self._get_record_by_index(platform_df, platform_row_idx)
                        provider_record = self._get_record_by_index(provider_df, provider_row_idx)
                        
                        if platform_record is None or provider_record is None:
                            print(f"هشدار: رکورد پیدا نشد - پلتفرم: {platform_row_idx}, ارائه‌دهنده: {provider_row_idx}")
                            continue
                        
                        combined_record = {}
                        combined_record['match_type'] = match_row.get('match_type', '')
                        combined_record['platform_code'] = match_row.get('platform_code', match_row.get('file1_code', ''))
                        combined_record['provider_code'] = match_row.get('provider_code', match_row.get('file2_code', ''))
                        
                        for col, val in platform_record.items():
                            combined_record[f'platform_{col}'] = val
                        for col, val in provider_record.items():
                            combined_record[f'provider_{col}'] = val
                        
                        combined_records.append(combined_record)
                    except Exception as e:
                        print(f"خطا در پردازش مچ: {str(e)}")
                
                if not combined_records:
                    print("هشدار: هیچ مچی با اطلاعات کامل یافت نشد.")
                    match_worksheet.write(0, 0, "هیچ مچی با اطلاعات کامل یافت نشد.", header_format)
                else:
                    combined_df = pd.DataFrame(combined_records)
                    column_names = self._get_unique_columns(combined_df)
                    for col_idx, col_name in enumerate(column_names):
                        match_worksheet.write(0, col_idx, col_name, header_format)
                        match_worksheet.set_column(col_idx, col_idx, max(10, min(30, len(str(col_name)))))
                    for row_idx, row in enumerate(combined_df.values):
                        for col_idx, cell_value in enumerate(row):
                            safe_value = self._safe_excel_value(cell_value)
                            match_worksheet.write(row_idx + 1, col_idx, safe_value)
                    print(f"شیت match با {len(combined_df)} رکورد ایجاد شد.")
            else:
                print("هشدار: دیتافریم matches یا دیتافریم‌های مرتبط وجود ندارند یا خالی هستند.")
                workbook.add_worksheet("match")
            
            # شیت 4: non_match_platform
            if 'non_matches' in results and not results['non_matches'].empty and 'filtered_platform' in results:
                non_match_platform_worksheet = workbook.add_worksheet("non_match_platform")
                non_matches_df = results['non_matches']
                platform_df = results['filtered_platform']
                
                platform_non_matches = non_matches_df[
                    (non_matches_df['match_type'] == 'فقط در فایل 1') | 
                    (non_matches_df['match_type'] == 'فقط در پلتفرم')
                ] if 'match_type' in non_matches_df.columns else pd.DataFrame()
                
                if platform_non_matches.empty:
                    print("هشدار: هیچ مغایرتی برای پلتفرم یافت نشد.")
                    non_match_platform_worksheet.write(0, 0, "هیچ مغایرتی برای پلتفرم یافت نشد.", header_format)
                else:
                    platform_records = []
                    for _, non_match_row in platform_non_matches.iterrows():
                        try:
                            platform_row_idx = non_match_row.get('platform_row', non_match_row.get('file1_row', None))
                            if platform_row_idx is None:
                                print(f"هشدار: ردیف ناقص در مغایرت پلتفرم: {non_match_row}")
                                continue
                            if isinstance(platform_row_idx, str) and platform_row_idx.isdigit():
                                platform_row_idx = int(platform_row_idx)
                            platform_record = self._get_record_by_index(platform_df, platform_row_idx)
                            if platform_record is None:
                                print(f"هشدار: رکورد پلتفرم پیدا نشد - ردیف: {platform_row_idx}")
                                continue
                            platform_record['non_match_code'] = non_match_row.get('platform_code', non_match_row.get('file1_code', ''))
                            platform_record['non_match_type'] = non_match_row.get('match_type', '')
                            platform_records.append(platform_record)
                        except Exception as e:
                            print(f"خطا در پردازش مغایرت پلتفرم: {str(e)}")
                    
                    if not platform_records:
                        print("هشدار: هیچ مغایرت پلتفرم با اطلاعات کامل یافت نشد.")
                        non_match_platform_worksheet.write(0, 0, "هیچ مغایرت پلتفرم با اطلاعات کامل یافت نشد.", header_format)
                    else:
                        platform_non_matches_df = pd.DataFrame(platform_records)
                        column_names = self._get_unique_columns(platform_non_matches_df)
                        if 'non_match_code' in column_names:
                            column_names.remove('non_match_code')
                            column_names.insert(0, 'non_match_code')
                        if 'non_match_type' in column_names:
                            column_names.remove('non_match_type')
                            column_names.insert(1, 'non_match_type')
                        for col_idx, col_name in enumerate(column_names):
                            non_match_platform_worksheet.write(0, col_idx, col_name, header_format)
                            non_match_platform_worksheet.set_column(col_idx, col_idx, max(10, min(30, len(str(col_name)))))
                        for row_idx, record in enumerate(platform_records):
                            for col_idx, col_name in enumerate(column_names):
                                cell_value = record.get(col_name, '')
                                safe_value = self._safe_excel_value(cell_value)
                                non_match_platform_worksheet.write(row_idx + 1, col_idx, safe_value)
                        print(f"شیت non_match_platform با {len(platform_records)} رکورد ایجاد شد.")
            else:
                print("هشدار: دیتافریم non_matches یا دیتافریم‌های مرتبط وجود ندارند یا خالی هستند.")
                workbook.add_worksheet("non_match_platform")
            
            # شیت 5: non_match_provider - روش جدید با استفاده از unmatched_provider
            non_match_provider_worksheet = workbook.add_worksheet("non_match_provider")
            
            # بررسی آیا unmatched_provider وجود دارد
            if 'unmatched_provider' in results and not results['unmatched_provider'].empty:
                unmatched_provider = results['unmatched_provider']
                
                print(f"تعداد رکوردهای بدون تطابق در ارائه‌دهنده: {len(unmatched_provider)}")
                
                if unmatched_provider.empty:
                    print("هشدار: هیچ مغایرتی برای ارائه‌دهنده یافت نشد.")
                    non_match_provider_worksheet.write(0, 0, "هیچ مغایرتی برای ارائه‌دهنده یافت نشد.", header_format)
                else:
                    # اضافه کردن یک ستون برای نشان دادن اینکه رکورد تطبیق نشده است
                    unmatched_provider = unmatched_provider.copy()
                    unmatched_provider['non_match_type'] = 'فقط در ارائه‌دهنده'
                    
                    # چینش ستون‌ها به صورت مناسب
                    column_names = ['non_match_type'] + [col for col in unmatched_provider.columns if col != 'non_match_type']
                    
                    # نوشتن هدرها
                    for col_idx, col_name in enumerate(column_names):
                        non_match_provider_worksheet.write(0, col_idx, col_name, header_format)
                        non_match_provider_worksheet.set_column(col_idx, col_idx, max(10, min(30, len(str(col_name)))))
                    
                    # نوشتن داده‌ها
                    for row_idx, row in enumerate(unmatched_provider[column_names].values):
                        for col_idx, cell_value in enumerate(row):
                            safe_value = self._safe_excel_value(cell_value)
                            non_match_provider_worksheet.write(row_idx + 1, col_idx, safe_value)
                    
                    print(f"شیت non_match_provider با {len(unmatched_provider)} رکورد ایجاد شد.")
            else:
                # اگر unmatched_provider وجود نداشت، از روش قدیمی استفاده کنیم
                print("هشدار: دیتافریم unmatched_provider وجود ندارد یا خالی است. از روش قدیمی استفاده می‌شود.")
                
                non_matches_df = results.get('non_matches', pd.DataFrame())
                provider_df = results.get('provider', pd.DataFrame())
                
                # فیلتر کردن فقط مغایرت‌های ارائه‌دهنده
                provider_non_matches = non_matches_df[
                    (non_matches_df['match_type'] == 'فقط در فایل 2') | 
                    (non_matches_df['match_type'] == 'فقط در ارائه‌دهنده')
                ] if 'match_type' in non_matches_df.columns else pd.DataFrame()
                
                if provider_non_matches.empty:
                    print("هشدار: هیچ مغایرتی برای ارائه‌دهنده یافت نشد.")
                    non_match_provider_worksheet.write(0, 0, "هیچ مغایرتی برای ارائه‌دهنده یافت نشد.", header_format)
                else:
                    provider_records = []
                    for _, non_match_row in provider_non_matches.iterrows():
                        try:
                            provider_row_idx = non_match_row.get('provider_row', non_match_row.get('file2_row', None))
                            if provider_row_idx is None:
                                print(f"هشدار: ردیف ناقص در مغایرت ارائه‌دهنده: {non_match_row}")
                                continue
                            
                            if isinstance(provider_row_idx, str) and provider_row_idx.isdigit():
                                provider_row_idx = int(provider_row_idx)
                                
                            provider_record = self._get_record_by_index(provider_df, provider_row_idx)
                            if provider_record is None:
                                print(f"هشدار: رکورد ارائه‌دهنده پیدا نشد - ردیف: {provider_row_idx}")
                                provider_record = {
                                    'non_match_code': non_match_row.get('provider_code', non_match_row.get('file2_code', '')),
                                    'non_match_type': non_match_row.get('match_type', '')
                                }
                            else:
                                provider_record['non_match_code'] = non_match_row.get('provider_code', non_match_row.get('file2_code', ''))
                                provider_record['non_match_type'] = non_match_row.get('match_type', '')
                            
                            provider_records.append(provider_record)
                        except Exception as e:
                            print(f"خطا در پردازش مغایرت ارائه‌دهنده: {str(e)}")
                    
                    if not provider_records:
                        print("هشدار: هیچ مغایرت ارائه‌دهنده با اطلاعات کامل یافت نشد.")
                        non_match_provider_worksheet.write(0, 0, "هیچ مغایرت ارائه‌دهنده با اطلاعات کامل یافت نشد.", header_format)
                    else:
                        # حذف داپلیکیت‌های احتمالی براساس شاخص ردیف
                        unique_rows = {}
                        for record in provider_records:
                            row_key = record.get('row_index', record.get('file2_row', str(record)))
                            if row_key not in unique_rows:
                                unique_rows[row_key] = record
                        
                        provider_records = list(unique_rows.values())
                        provider_non_matches_df = pd.DataFrame(provider_records)
                        
                        column_names = self._get_unique_columns(provider_non_matches_df)
                        priority_columns = ['non_match_code', 'non_match_type']
                        for col in reversed(priority_columns):
                            if col in column_names:
                                column_names.remove(col)
                                column_names.insert(0, col)
                                
                        for col_idx, col_name in enumerate(column_names):
                            non_match_provider_worksheet.write(0, col_idx, col_name, header_format)
                            non_match_provider_worksheet.set_column(col_idx, col_idx, max(10, min(30, len(str(col_name)))))
                            
                        for row_idx, record in enumerate(provider_records):
                            for col_idx, col_name in enumerate(column_names):
                                cell_value = record.get(col_name, '')
                                safe_value = self._safe_excel_value(cell_value)
                                non_match_provider_worksheet.write(row_idx + 1, col_idx, safe_value)
                                
                        print(f"شیت non_match_provider با {len(provider_records)} رکورد ایجاد شد.")
            
            workbook.close()
            print(f"فایل Excel با موفقیت در {output_path} ذخیره شد.")
            return True
            
        except Exception as e:
            import traceback
            print(f"خطا در ایجاد فایل Excel: {e}")
            traceback.print_exc()
            return False

    def _get_unique_columns(self, df):
        """تبدیل ستون‌ها به رشته و ایجاد نام‌های یکتا"""
        if df is None or df.empty:
            return []
        column_names = [str(col) for col in df.columns]
        if len(column_names) != len(set(column_names)):
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
            df.columns = new_columns
            return new_columns
        return column_names

    def _safe_excel_value(self, value):
        """تبدیل ایمن مقادیر برای اکسل"""
        if value is None or pd.isna(value):
            return ""
        try:
            if isinstance(value, (int, np.int64, np.int32)) and (value > 2**31-1 or value < -2**31):
                return str(value)
            if isinstance(value, (float, np.floating)):
                if pd.isna(value):
                    return ""
                return f'{value:.6f}'.rstrip('0').rstrip('.') if '.' in f'{value:.6f}' else f'{value:.0f}'
            return str(value)
        except Exception as e:
            print(f"خطا در تبدیل مقدار {value}: {e}")
            return str(value)

    def _get_record_by_index(self, df, idx):
        """پیدا کردن رکورد با استفاده از شاخص"""
        if df is None or df.empty:
            return None
        try:
            if idx in df.index:
                return df.loc[idx].to_dict()
            if isinstance(idx, (int, np.integer)) and 0 <= idx < len(df):
                return df.iloc[idx].to_dict()
            print(f"هشدار: شاخص {idx} خارج از محدوده دیتافریم با طول {len(df)} است.")
            return None
        except Exception as e:
            print(f"خطا در پیدا کردن رکورد با شاخص {idx}: {e}")
            return None

if __name__ == "__main__":
    st.title("سیستم مغایرت‌گیری هوشمند")

    platform_file = st.file_uploader("فایل پلتفرم را انتخاب کنید", type=['csv', 'xlsx', 'json'], label_visibility="visible")
    provider_file = st.file_uploader("فایل ارائه‌دهنده را انتخاب کنید", type=['csv', 'xlsx', 'json'], label_visibility="visible")
    gateway_name = st.text_input("نام Gateway را وارد کنید (مثلاً toman)", value="toman", label_visibility="visible")
    
    if st.button("شروع مغایرت‌گیری", help="برای شروع فرآیند مغایرت‌گیری کلیک کنید", label_visibility="visible"):
        if platform_file and provider_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx' if platform_file.name.endswith('.xlsx') else '.csv') as tmp_platform:
                tmp_platform.write(platform_file.read())
                platform_path = tmp_platform.name
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx' if provider_file.name.endswith('.xlsx') else '.csv') as tmp_provider:
                tmp_provider.write(provider_file.read())
                provider_path = tmp_provider.name
            
            system = SmartReconciliationSystem()
            results = system.gateway_specific_reconciliation(platform_path, provider_path, gateway_name)
            
            if results:
                output_path = f"reconciliation_report_{gateway_name}.xlsx"
                if system.generate_report(results, output_path):
                    st.success(f"گزارش با موفقیت تولید شد: {output_path}")
                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="دانلود گزارش",
                            data=f,
                            file_name=output_path,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            label_visibility="visible"
                        )
                
                for key in ['filtered_platform', 'provider', 'matches', 'non_matches', 'unmatched_provider']:
                    if key in results and not results[key].empty:
                        df = results[key].copy()
                        for col in df.columns:
                            df[col] = df[col].astype(str)
                        st.subheader(f"دیتافریم {key}")
                        st.dataframe(df)
            else:
                st.error("خطایی در فرآیند مغایرت‌گیری رخ داد.")
            
            os.unlink(platform_path)
            os.unlink(provider_path)
        else:
            st.warning("لطفاً هر دو فایل را بارگذاری کنید.")
