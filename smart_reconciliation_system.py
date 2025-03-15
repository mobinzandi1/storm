import pandas as pd
import numpy as np
import re
import os
import json
from fuzzywuzzy import fuzz
import xlsxwriter
import tempfile
import streamlit as st
from multiprocessing import Pool
import logging

# تنظیم لاگ برای دیباگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SmartReconciliationSystem:
    def __init__(self):
        self.tracking_patterns = [
            r'\b[a-zA-Z0-9]{6,30}\b',
            r'TR-\d+',
            r'TRK\d+',
            r'wallex-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+',
        ]
        self.platform_tracking_columns = ['gateway_tracking_code', 'gateway_identifier', 'meta_data_1']
        self.chunk_size = 2000  # کاهش اندازه تکه‌ها برای پردازش

    def detect_file_type(self, file_path):
        _, ext = os.path.splitext(file_path)
        return ext.lower()

    def read_file(self, file_path, columns=None, nrows=None):
        file_type = self.detect_file_type(file_path)
        logging.info(f"Reading file: {file_path}, type: {file_type}")
        if file_type == '.csv':
            try:
                return pd.read_csv(file_path, encoding='utf-8', usecols=columns if columns else None, nrows=nrows)
            except UnicodeDecodeError:
                return pd.read_csv(file_path, encoding='windows-1256', usecols=columns if columns else None, nrows=nrows)
        elif file_type in ['.xlsx', '.xls']:
            return pd.read_excel(file_path, usecols=columns if columns else None, nrows=nrows)
        elif file_type == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return pd.DataFrame(data) if isinstance(data, list) else pd.json_normalize(data)
        else:
            raise ValueError(f"Unsupported file format: {file_type}")

    def extract_potential_tracking_codes(self, df, is_platform=False):
        tracking_codes = []
        columns_to_check = self.platform_tracking_columns if is_platform else df.columns
        columns_to_check = [col for col in columns_to_check if col in df.columns]
        logging.info(f"Extracting codes from {len(df)} rows, columns: {columns_to_check}")

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

        with Pool() as pool:
            chunks = [df[i:i + self.chunk_size] for i in range(0, len(df), self.chunk_size)]
            tracking_codes = sum(pool.map(process_chunk, chunks), [])

        result = pd.DataFrame(tracking_codes).drop_duplicates(subset=['code'])
        logging.info(f"Extracted {len(result)} unique codes")
        return result

    def extract_codes_from_platform(self, df):
        return self.extract_potential_tracking_codes(df, is_platform=True)

    def extract_codes_from_provider(self, df):
        return self.extract_potential_tracking_codes(df, is_platform=False)

    def find_exact_matches(self, codes1, codes2):
        if codes1.empty or codes2.empty:
            logging.warning("One of the code sets is empty")
            return pd.DataFrame(), pd.concat([codes1.assign(match_type='فقط در فایل 1'), 
                                             codes2.assign(match_type='فقط در فایل 2')])

        matches = codes1.merge(codes2, how='inner', left_on='code', right_on='code', 
                               suffixes=('_file1', '_file2'))
        matches['match_type'] = 'دقیق'
        logging.info(f"Found {len(matches)} exact matches")

        unmatched1 = codes1[~codes1['code'].isin(matches['code'])].assign(match_type='فقط در فایل 1')
        unmatched2 = codes2[~codes2['code'].isin(matches['code'])].assign(match_type='فقط در فایل 2')
        non_matches = pd.concat([unmatched1, unmatched2])
        logging.info(f"Found {len(non_matches)} non-matches")

        return matches, non_matches

    def find_similar_codes(self, codes1, codes2, threshold=85):
        logging.warning("Fuzzy matching is disabled for performance (using exact matches only)")
        return self.find_exact_matches(codes1, codes2)

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
        logging.info(f"Platform data loaded with shape: {platform_df.shape}")
        provider_df = self.read_file(provider_path)
        logging.info(f"Provider data loaded with shape: {provider_df.shape}")

        filtered_platform = platform_df[platform_df['gateway'].astype(str).str.lower() == gateway_name.lower()]
        if filtered_platform.empty:
            logging.warning(f"No records with gateway '{gateway_name}' found.")
            return None

        logging.info(f"Filtered platform data for gateway '{gateway_name}' with {len(filtered_platform)} records")
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
            logging.error("Results are empty!")
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
                    logging.info(f"Sheet {sheet_name} with {len(df)} records created")
                else:
                    pd.DataFrame().to_excel(writer, sheet_name=sheet_name)
                    logging.warning(f"Sheet {sheet_name} is empty or not present")

        logging.info(f"Excel file saved at {output_path}")
        return True

if __name__ == "__main__":
    st.title("Smart Reconciliation System")

    platform_file = st.file_uploader("Upload Platform File", type=['csv', 'xlsx', 'json'])
    provider_file = st.file_uploader("Upload Provider File", type=['csv', 'xlsx', 'json'])
    gateway_name = st.text_input("Enter Gateway Name (e.g., toman)", value="toman")
    nrows_limit = st.number_input("Limit number of rows per file (0 for no limit)", min_value=0, value=1000)

    if st.button("Start Reconciliation"):
        if platform_file and provider_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_platform, \
                 tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_provider:
                tmp_platform.write(platform_file.read())
                tmp_provider.write(provider_file.read())
                platform_path, provider_path = tmp_platform.name, tmp_provider.name

            st.write("Starting reconciliation process...")
            system = SmartReconciliationSystem()
            try:
                st.write(f"Reading platform file with {platform_file.size/1024:.2f} KB...")
                platform_df = system.read_file(platform_path, columns=['gateway'] + system.platform_tracking_columns, 
                                            nrows=None if nrows_limit == 0 else nrows_limit)
                st.write(f"Platform data shape: {platform_df.shape}")
                st.write(f"Reading provider file...")
                provider_df = system.read_file(provider_path, nrows=None if nrows_limit == 0 else nrows_limit)
                st.write(f"Provider data shape: {provider_df.shape}")

                st.write("Extracting codes from platform...")
                platform_codes = system.extract_codes_from_platform(platform_df)
                st.write(f"Platform codes count: {len(platform_codes)}")
                st.write("Extracting codes from provider...")
                provider_codes = system.extract_codes_from_provider(provider_df)
                st.write(f"Provider codes count: {len(provider_codes)}")

                st.write("Matching codes...")
                results = system.gateway_specific_reconciliation(platform_path, provider_path, gateway_name)
                
                if results:
                    st.write("Reconciliation completed, generating report...")
                    output_path = f"reconciliation_report_{gateway_name}.xlsx"
                    if system.generate_report(results, output_path):
                        st.success(f"Report generated: {output_path}")
                        with open(output_path, "rb") as f:
                            st.download_button(label="Download Report", data=f, file_name=output_path)
                        for key in ['filtered_platform', 'provider', 'matches', 'non_matches', 'unmatched_provider']:
                            if key in results and not results[key].empty:
                                st.subheader(f"Dataframe {key}")
                                st.write(results[key].head())
                else:
                    st.error("No results from reconciliation.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
            finally:
                os.unlink(platform_path)
                os.unlink(provider_path)
        else:
            st.warning("Please upload both files.")
