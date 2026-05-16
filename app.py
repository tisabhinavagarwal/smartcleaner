import os
import re
import io
import csv
import pandas as pd
import numpy as np
import streamlit as st
import requests
import hashlib
from rapidfuzz import process, fuzz

def setup_directories():
    """Ensure required file system structure exists for local operations."""
    for folder in ['input', 'output']:
        os.makedirs(folder, exist_ok=True)

def fetch_api_data(url):
    """Retrieve and parse JSON payload from a given REST endpoint."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, list):
            return pd.json_normalize(data)
        if isinstance(data, dict):
            for _, value in data.items():
                if isinstance(value, list):
                    return pd.json_normalize(value)
            return pd.json_normalize([data])
        raise ValueError("Unsupported JSON structure")
    except Exception as e:
        st.error(f"API Request Failed: {e}")
        return None

class DataValidator:
    @staticmethod
    def is_valid_email(email):
        if pd.isna(email):
            return False
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return bool(re.match(pattern, str(email).strip()))

    @staticmethod
    def extract_phone(phone):
        if pd.isna(phone):
            return np.nan
        digits = re.sub(r'\D', '', str(phone))
        return digits[-10:] if len(digits) >= 10 else np.nan

class SmartCleaner:
    def __init__(self, df, options):
        self.df = df.copy()
        self.options = options
        self.metrics = {
            "initial_rows": len(df),
            "duplicates_removed": 0,
            "missing_filled": 0,
            "invalid_emails_flagged": 0,
            "final_rows": 0
        }

    def process(self):
        if self.options.get('remove_duplicates'):
            self._remove_duplicates()
        if self.options.get('handle_missing'):
            self._handle_missing()
        if self.options.get('normalize_text'):
            self._normalize_text()
        if self.options.get('validate_emails'):
            self._validate_emails()
        if self.options.get('standardize_phones'):
            self._standardize_phones()
        if self.options.get('standardize_dates'):
            self._standardize_dates()
        if self.options.get('fuzzy_match'):
            self._fuzzy_match_cities()

        self.metrics['final_rows'] = len(self.df)
        return self.df, self.metrics

    def _remove_duplicates(self):
        initial_len = len(self.df)
        self.df.drop_duplicates(inplace=True)
        self.metrics['duplicates_removed'] = initial_len - len(self.df)

    def _handle_missing(self):
        missing_count = self.df.isna().sum().sum()
        for col in self.df.columns:
            if pd.api.types.is_numeric_dtype(self.df[col]):
                self.df[col] = self.df[col].fillna(self.df[col].median())
            else:
                self.df[col] = self.df[col].fillna("Unknown")
        self.metrics['missing_filled'] = missing_count

    def _normalize_text(self):
        for col in self.df.select_dtypes(include=['object', 'string']):
            self.df[col] = self.df[col].astype(str).str.strip().str.title()

    def _validate_emails(self):
        email_col = next((c for c in self.df.columns if 'email' in c.lower()), None)
        if email_col:
            unique_vals = self.df[email_col].dropna().unique()
            valid_map = {val: DataValidator.is_valid_email(val) for val in unique_vals}
            is_valid = self.df[email_col].map(valid_map).fillna(False)
            self.metrics['invalid_emails_flagged'] = (~is_valid).sum()
            self.df.loc[~is_valid, email_col] = "Invalid_Email"

    def _standardize_phones(self):
        phone_col = next((c for c in self.df.columns if 'phone' in c.lower() or 'contact' in c.lower()), None)
        if phone_col:
            unique_vals = self.df[phone_col].dropna().unique()
            phone_map = {val: DataValidator.extract_phone(val) for val in unique_vals}
            self.df[phone_col] = self.df[phone_col].map(phone_map)

    def _standardize_dates(self):
        date_cols = [c for c in self.df.columns if 'date' in c.lower() or 'join' in c.lower()]
        for col in date_cols:
            self.df[col] = pd.to_datetime(self.df[col], errors='coerce').dt.strftime('%Y-%m-%d')
            self.df[col] = self.df[col].fillna("Unknown")

    def _fuzzy_match_cities(self):
        city_col = next((c for c in self.df.columns if 'city' in c.lower() or 'location' in c.lower()), None)
        if city_col:
            standard_cities = ['Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad', 'Pune']
            unique_vals = self.df[city_col].dropna().unique()
            def match(val):
                if pd.isna(val) or val == "Unknown": return val
                match_tuple = process.extractOne(str(val), standard_cities, scorer=fuzz.WRatio)
                return match_tuple[0] if match_tuple and match_tuple[1] > 75 else val
            city_map = {val: match(val) for val in unique_vals}
            self.df[city_col] = self.df[city_col].map(city_map)

class Exporter:
    @staticmethod
    def to_csv(df):
        return df.to_csv(index=False).encode('utf-8')

    @staticmethod
    def to_excel(df, metrics, quarantined_df=None):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Cleaned_Data', index=False)
            summary_df = pd.DataFrame(list(metrics.items()), columns=['Metric', 'Value'])
            summary_df.to_excel(writer, sheet_name='Cleaning_Report', index=False)
            
            # Dynamically add the quarantine sheet if bad rows were caught
            if quarantined_df is not None and not quarantined_df.empty:
                quarantined_df.to_excel(writer, sheet_name='Quarantined_Rows', index=False)
                
        return output.getvalue()

    @staticmethod
    def save_local(df, filename="output/clean_output.csv"):
        df.to_csv(filename, index=False)

st.set_page_config(page_title="SmartClean", layout="wide")

def main():
    setup_directories()

    st.title("SmartClean Pipeline")
    st.markdown("Automated data standardization and cleaning engine.")

    # Initialize persistent state memory 
    for key in ['raw_data', 'cleaned_df', 'metrics', 'csv_data', 'excel_data', 'quarantined_df', 'recovered_count']:
        if key not in st.session_state:
            st.session_state[key] = None

    st.sidebar.header("Data Ingestion")
    data_source = st.sidebar.radio("Source Type", ("Upload File(s)", "REST API Endpoint"))
    auto_recover = st.sidebar.checkbox("Auto-Recover Broken Rows", value=True, help="Smart-merge unescaped commas back into text columns.")

    if data_source == "Upload File(s)":
        uploaded_files = st.sidebar.file_uploader("Select CSV or XLSX", type=['csv', 'xlsx'], accept_multiple_files=True)
        if uploaded_files:
            dfs = []
            seen_hashes = set()
            quarantined_records = []
            recovered_count = 0
            
            for uf in uploaded_files:
                file_bytes = uf.getvalue()
                f_hash = hashlib.md5(file_bytes).hexdigest()
                
                if f_hash in seen_hashes:
                    st.sidebar.warning(f"Skipped identical file: {uf.name}")
                    continue
                
                seen_hashes.add(f_hash)
                uf.seek(0)
                try:
                    if uf.name.endswith('.csv'):
                        # Smart Header Detection (Lightweight O(1) operation)
                        uf.seek(0)
                        sample = uf.read(8192).decode('utf-8', errors='ignore')
                        uf.seek(0)
                        
                        has_header = True
                        try:
                            # Sniffer evaluates data types. Extremely fast, negligible resource usage.
                            has_header = csv.Sniffer().has_header(sample)
                        except Exception:
                            pass # Fallback to standard pandas behavior if sniffer is unsure
                            
                        header_arg = 'infer' if has_header else None

                        try:
                            # Fast path: Try standard C engine first (strict but fast)
                            df = pd.read_csv(uf, encoding='utf-8', on_bad_lines='error', low_memory=False, header=header_arg)
                        except Exception:
                            # Intercept malformed rows (Auto-Recovery or Quarantine)
                            uf.seek(0)
                            first_line = uf.readline().decode('utf-8', errors='ignore')
                            try:
                                num_cols = len(next(csv.reader(io.StringIO(first_line))))
                            except StopIteration:
                                num_cols = 1
                            uf.seek(0)
                            
                            def handle_bad_lines(bad_line):
                                nonlocal recovered_count
                                if auto_recover:
                                    recovered_count += 1
                                    # Merge extra fractured columns into the last column
                                    if len(bad_line) > num_cols:
                                        return bad_line[:num_cols-1] + [",".join(bad_line[num_cols-1:])]
                                    return bad_line + [""] * (num_cols - len(bad_line))
                                else:
                                    quarantined_records.append(",".join(bad_line))
                                    return None # Skip from main ingestion
                                
                            try:
                                df = pd.read_csv(uf, engine='python', on_bad_lines=handle_bad_lines, encoding='utf-8', header=header_arg)
                            except UnicodeDecodeError:
                                uf.seek(0)
                                df = pd.read_csv(uf, engine='python', on_bad_lines=handle_bad_lines, encoding='latin-1', header=header_arg)
                        
                        # Apply generic Column_N names if no header was detected
                        if not has_header:
                            df.columns = [f"Column_{i+1}" for i in range(len(df.columns))]

                    else:
                        df = pd.read_excel(uf)
                    dfs.append(df)
                except Exception as e:
                    st.sidebar.error(f"Failed to read {uf.name}: {e}")
            
            if dfs:
                combined_df = pd.concat(dfs, ignore_index=True)
                
                # Update session state securely
                if st.session_state['raw_data'] is None or not st.session_state['raw_data'].equals(combined_df):
                    st.session_state['raw_data'] = combined_df
                    st.session_state['cleaned_df'] = None
                    st.session_state['recovered_count'] = recovered_count
                    
                    if quarantined_records:
                        st.session_state['quarantined_df'] = pd.DataFrame(quarantined_records, columns=['Raw_Malformed_Row'])
                        st.sidebar.error(f"{len(quarantined_records)} structurally malformed rows isolated to Quarantine.")
                    else:
                        st.session_state['quarantined_df'] = None
                        
                    if recovered_count > 0:
                        st.sidebar.success(f"Auto-recovered and merged {recovered_count} broken rows back into the dataset!")
    
    elif data_source == "REST API Endpoint":
        api_url = st.sidebar.text_input("Endpoint URL", placeholder="https://api.example.com/data")
        if st.sidebar.button("Fetch Data") and api_url:
            with st.spinner("Fetching data from API..."):
                fetched_data = fetch_api_data(api_url)
                if fetched_data is not None:
                    st.session_state['raw_data'] = fetched_data
                    st.session_state['cleaned_df'] = None
                    st.session_state['quarantined_df'] = None
                    st.session_state['recovered_count'] = 0

    df = st.session_state['raw_data']

    if df is not None:
        st.subheader("Source Data Profile")
        st.caption(f"Dimensions: {df.shape[0]} rows, {df.shape[1]} columns")
        
        with st.expander("View Raw Data", expanded=False):
            st.caption("Note: Displaying a preview of the first 100 rows to optimize browser performance.")
            st.dataframe(df.head(100), use_container_width=True)

        st.sidebar.markdown("---")
        st.sidebar.header("Pipeline Configuration")
        options = {
            'remove_duplicates': st.sidebar.checkbox("Remove Duplicates", value=True),
            'handle_missing': st.sidebar.checkbox("Resolve Missing Values", value=True),
            'normalize_text': st.sidebar.checkbox("Normalize Text formatting", value=True),
            'validate_emails': st.sidebar.checkbox("Validate Emails", value=True),
            'standardize_phones': st.sidebar.checkbox("Standardize Phones", value=True),
            'standardize_dates': st.sidebar.checkbox("Standardize Dates", value=True),
            'fuzzy_match': st.sidebar.checkbox("Fuzzy Match Locations", value=True)
        }

        if st.sidebar.button("Execute Pipeline", type="primary"):
            with st.spinner("Processing massive dataset... (Optimized for 1M+ rows)"):
                cleaner = SmartCleaner(df, options)
                cleaned_df, metrics = cleaner.process()
                
                Exporter.save_local(cleaned_df)
                st.session_state['cleaned_df'] = cleaned_df
                st.session_state['metrics'] = metrics
                st.session_state['csv_data'] = Exporter.to_csv(cleaned_df)
                
                # Generate Excel with dynamic Quarantine sheet
                st.session_state['excel_data'] = Exporter.to_excel(
                    cleaned_df, 
                    metrics, 
                    st.session_state['quarantined_df']
                )
                
            st.success("Pipeline execution completed successfully.")

        if st.session_state['cleaned_df'] is not None:
            cleaned_df = st.session_state['cleaned_df']
            metrics = st.session_state['metrics']
            
            st.subheader("Execution Metrics")
            
            if st.session_state['quarantined_df'] is not None:
                st.warning(f"**Data Integrity Alert:** {len(st.session_state['quarantined_df'])} malformed rows were quarantined and removed from the main pipeline. Check your export artifacts.")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Processed Rows", metrics['final_rows'], delta=f"{metrics['final_rows'] - metrics['initial_rows']} rows")
            col2.metric("Duplicates Removed", metrics['duplicates_removed'])
            col3.metric("Imputations Performed", metrics['missing_filled'])
            col4.metric("Invalid Emails Detected", metrics['invalid_emails_flagged'])

            st.subheader("Processed Data")
            st.caption("Note: Displaying a preview of the first 100 rows. Download the artifacts below for the complete dataset.")
            st.dataframe(cleaned_df.head(100), use_container_width=True)

            st.subheader("Export Artifacts")
            
            # Layout dynamically adjusts if we need 2 or 3 buttons
            has_quarantine = st.session_state['quarantined_df'] is not None and not st.session_state['quarantined_df'].empty
            
            if has_quarantine:
                d_col1, d_col2, d_col3 = st.columns(3)
            else:
                d_col1, d_col2 = st.columns(2)
                
            d_col1.download_button("Download CSV", st.session_state['csv_data'], "clean_output.csv", "text/csv", use_container_width=True)
            d_col2.download_button("Download Excel Report", st.session_state['excel_data'], "cleaning_report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
            if has_quarantine:
                q_csv_data = Exporter.to_csv(st.session_state['quarantined_df'])
                d_col3.download_button("Download Quarantined Rows", q_csv_data, "quarantined_rows.csv", "text/csv", use_container_width=True)
    else:
        st.info("Awaiting data source configuration.")

if __name__ == "__main__":
    main()