import pandas as pd
import numpy as np
import re
import os
import json
from fuzzywuzzy import fuzz
import xlsxwriter
import tempfile
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

class SmartReconciliationSystem:
    def __init__(self):
        self.tracking_patterns = [
            r'\b[a-zA-Z0-9]{6,30}\b',
            r'TR-\d+',
            r'TRK\d+',
            r'wallex-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+',
        ]
        self.platform_tracking_columns = ['gateway_tracking_code', 'gateway_identifier', 'meta_data_1']
        self.chunk_size = 10000  # اندازه دسته برای پردازش

    def detect_file_type(self, file_path):
        _, ext = os.path.splitext(file_path)
        return ext.lower()

    def read_file(self, file_path, columns=None):
        file_type = self.detect_file_type(file_path)
        if file_type == '.csv':
            try:
                return pd.read_csv(file_path, encoding='utf-8', usecols=columns)
            except UnicodeDecodeError:
                return pd.read_csv(file_path, encoding='windows-1256', usecols=columns)
        elif file_type in ['.xlsx', '.xls']:
            return pd.read_excel(file_path, usecols=columns)
        elif file_type == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return pd.DataFrame(data) if isinstance(data, list) else self.extract_from_complex_json(data)
        else:
            raise ValueError(f"Unsupported file format: {file_type}")

    def extract_from_complex_json(self, data):
        flat_data = pd.json_normalize(data)
        return flat_data

    def extract_potential_tracking_codes(self, df, is_platform=False):
        tracking_codes = []
        columns_to_check = self.platform_tracking_columns if is_platform else df.columns
        columns_to_check = [col for col in columns_to_check if col in df.columns]

        def process_chunk(chunk):
            codes = []
            for col in columns_to_check:
                chunk[col] = chunk[col].astype(str).fillna('')
                for pattern in self.tracking_patterns:
                    matches = chunk[col].str.extractall(f'({pattern})')[0].unique()
                    for match in matches:
                        rows = chunk[chunk[col].str.contains(match, regex=False, na=False)].index
                        for idx in rows:
                            codes.append({
                                'code': match,
                                'column': col,
                                'row_index': idx,
                                'original_text': chunk.loc[idx, col]
                            })
            return codes

        for start in range(0, len(df), self.chunk_size):
            chunk = df.iloc[start:start + self.chunk_size]
            tracking_codes.extend(process_chunk(chunk))

        return pd.DataFrame(tracking_codes).drop_duplicates(subset=['code'])

    def extract_codes_from_platform(self, df):
        return self.extract_potential_tracking_codes(df, is_platform=True)

    def extract_codes_from_provider(self, df):
        return self.extract_potential_tracking_codes(df, is_platform=False)

    def find_exact_matches(self, codes1, codes2):
        if codes1.empty or codes2.empty:
            return pd.DataFrame(), pd.concat([codes1.assign(match_type='فقط در فایل 1'), 
                                             codes2.assign(match_type='فقط در فایل 2')])

        # استفاده از merge برای تطبیق سریع
        matches = codes1.merge(codes2, how='inner', left_on='code', right_on='code', 
                               suffixes=('_file1', '_file2'))
        matches['match_type'] = 'دقیق'

        unmatched1 = codes1[~codes1['code'].isin(matches['code'])].assign(match_type='فقط در فایل 1')
        unmatched2 = codes2[~codes2['code'].isin(matches['code'])].assign(match_type='فقط در فایل 2')
        non_matches = pd.concat([unmatched1, unmatched2])

        return matches, non_matches

    def find_similar_codes(self, codes1, codes2, threshold=85):
        if codes1.empty or codes2.empty:
            return pd.DataFrame(), pd.concat([codes1.assign(match_type='فقط در فایل 1'), 
                                             codes2.assign(match_type='فقط در فایل 2')])

        def fuzzy_match(code, codes_list):
            best_score, best_match = max(((fuzz.ratio(code, c), c) for c in codes_list), default=(0, None))
            return best_match, best_score if best_score >= threshold else (None, 0)

        codes2_set = set(codes2['code'])
        matches = []
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(lambda x: (x, fuzzy_match(x, codes2_set)), codes1['code']))
        
        for code, (best_match, score) in results:
            if best_match:
                row1 = codes1[codes1['code'] == code].iloc[0]
                row2 = codes2[codes2['code'] == best_match].iloc[0]
                matches.append({
                    'file1_code': code,
                    'file1_column': row1['column'],
                    'file1_row': row1['row_index'],
                    'file2_code': best_match,
                    'file2_column': row2['column'],
                    'file2_row': row2['row_index'],
                    'file2_text': row2['original_text'][:50],
                    'similarity': score,
                    'match_type': 'فازی'
                })

        matches_df = pd.DataFrame(matches)
        unmatched1 = codes1[~codes1['code'].isin(matches_df['file1_code'])].assign(match_type='فقط در فایل 1')
        unmatched2 = codes2[~codes2['code'].isin(matches_df['file2_code'])].assign(match_type='فقط در فایل 2')
        non_matches = pd.concat([unmatched1, unmatched2])

        return matches_df, non_matches

    def reconcile_platform_with_provider(self, platform_path, provider_path):
        platform_df = self.read_file(platform_path, columns=self.platform_tracking_columns + ['gateway'])
        provider_df = self.read_file(provider_path)
        
        platform_codes = self.extract_codes_from_platform(platform_df)
        provider_codes = self.extract_codes_from_provider(provider_df)
        
        matches, non_matches = self.find_exact_matches(platform_codes, provider_codes)
        
        return {
            'platform': platform_df,
            'provider': provider_df,
            'platform_codes': platform_codes,
            'provider_codes': provider_codes,
            'matches': matches,
            'non_matches': non_matches
        }

    def gateway_specific_reconciliation(self, platform_path, provider_path, gateway_name):
        platform_df = self.read_file(platform_path, columns=self.platform_tracking_columns + ['gateway'])
        provider_df = self.read_file(provider_path)
        
        filtered_platform = platform_df[platform_df['gateway'].astype(str).str.lower() == gateway_name.lower()]
        if filtered_platform.empty:
            print(f"No records with gateway '{gateway_name}' found.")
            return None

        platform_codes = self.extract_codes_from_platform(filtered_platform)
        provider_codes = self.extract_codes_from_provider(provider_df)

        matches, non_matches = self.find_exact_matches(platform_codes, provider_codes)
        unmatched_provider = provider_df[~provider_df.index.isin(matches['file2_row'])]

        return {
            'platform': platform_df,
            'provider': provider_df,
            'filtered_platform': filtered_platform,
            'platform_codes': platform_codes,
            'provider_codes': provider_codes,
            'matches': matches,
            'non_matches': non_matches,
            'gateway_name': gateway_name,
            'unmatched_provider': unmatched_provider
        }

    def generate_report(self, results, output_path="reconciliation_report.xlsx"):
        if not results:
            print("Error: Results are empty!")
            return False

        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            for sheet_name, df in [
                ('filtered_platform', results.get('filtered_platform')),
                ('provider', results.get('provider')),
                ('matches', results.get('matches')),
                ('non_match_platform', results.get('non_matches', pd.DataFrame()).query("match_type == 'فقط در پلتفرم'")),
                ('non_match_provider', results.get('unmatched_provider'))
            ]:
                if df is not None and not df.empty:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    print(f"Sheet {sheet_name} with {len(df)} records created.")
                else:
                    pd.DataFrame().to_excel(writer, sheet_name=sheet_name)
                    print(f"Warning: {sheet_name} is empty or not present.")

        print(f"Excel file saved at {output_path}")
        return True

if __name__ == "__main__":
    st.title("Smart Reconciliation System")

    platform_file = st.file_uploader("Upload Platform File", type=['csv', 'xlsx', 'json'])
    provider_file = st.file_uploader("Upload Provider File", type=['csv', 'xlsx', 'json'])
    gateway_name = st.text_input("Enter Gateway Name (e.g., toman)", value="toman")

    if st.button("Start Reconciliation"):
        if platform_file and provider_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_platform, \
                 tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_provider:
                tmp_platform.write(platform_file.read())
                tmp_provider.write(provider_file.read())
                
                system = SmartReconciliationSystem()
                results = system.gateway_specific_reconciliation(tmp_platform.name, tmp_provider.name, gateway_name)
                
                if results:
                    output_path = f"reconciliation_report_{gateway_name}.xlsx"
                    if system.generate_report(results, output_path):
                        st.success(f"Report generated: {output_path}")
                        with open(output_path, "rb") as f:
                            st.download_button(label="Download Report", data=f, file_name=output_path)
                
                os.unlink(tmp_platform.name)
                os.unlink(tmp_provider.name)
        else:
            st.warning("Please upload both files.")
