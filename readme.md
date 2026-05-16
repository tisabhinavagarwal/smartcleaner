🧹 SmartClean Pipeline

🌐 Live Application: Access SmartClean Pipeline Here

(Note: Replace the link above with your live domain once hosted)

SmartClean Pipeline is an intelligent, lightweight, and professional-grade data ingestion and standardization engine. Built for robustness and scale, it ingests messy datasets via file uploads or REST APIs, cleans them using optimized mappings, and securely handles malformed records using enterprise standard Quarantine (Dead Letter Queue) patterns.

🚀 Key Features

1. Robust Data Ingestion

Multi-format Support: Ingest .csv and .xlsx files simultaneously.

REST API Integration: Fetch nested JSON payloads directly from API endpoints. Deeply nested structures are automatically flattened (json_normalize).

Cryptographic Deduplication: Hashes incoming files (MD5) to prevent redundant processing of identical files.

Smart Header Detection: Uses O(1) csv.Sniffer byte-peeking to dynamically detect if a dataset has headers without sacrificing read times.

2. Enterprise Data Integrity (The Quarantine Engine)

Strict Fast-Path Parsing: Standard files are processed via a highly optimized C-engine.

Dead Letter Queue (DLQ): Structurally malformed rows (e.g., unescaped commas shifting columns) are intercepted and isolated from the main pipeline.

Intelligent Auto-Recovery: Optionally auto-stitches fractured columns back together in-memory, rescuing broken data and seamlessly appending it to the clean dataset.

3. Optimized Cleaning Engine

O(1) Mapping Optimization: Capable of processing 1M+ rows in seconds by utilizing Unique Value Mapping rather than row-by-row iteration.

Regex Standardizations: Validates emails and extracts/normalizes 10-digit phone numbers.

Text & Date Formatting: Enforces proper title-casing, strips whitespaces, and standardizes disparate date formats to YYYY-MM-DD.

Fuzzy Matching: Implements rapidfuzz to detect and unify typo-ridden location/city names (e.g., "Delih" → "Delhi").

Smart Imputation: Handles NaN and nulls contextually (median for numerics, "Unknown" for strings).

4. Interactive & Persistent UI

Built with Streamlit for a minimal, professional dashboard experience.

Session State Anchoring: Keeps heavy data artifacts anchored in memory so user interactions and downloads do not trigger costly script reruns.

Preview Throttling: Caps DataFrame rendering at 100 rows to prevent browser memory crashes on massive datasets.

🛠️ Technologies Used

Core Engine: Python, Pandas, NumPy

Frontend UI: Streamlit

Fuzzy Logic: Rapidfuzz

Data Retrieval: Requests

Export Handling: OpenPyXL

📂 Project Structure

smartclean/
│
├── app.py                  # Main Streamlit application and core pipeline
├── requirements.txt        # Project dependencies
├── README.md               # Documentation
│
├── input/                  # Auto-generated: Directory for local raw data (optional)
└── output/                 # Auto-generated: Directory for pipeline exports



💻 Installation & Setup (Local)

It is highly recommended to run this project inside an isolated virtual environment.

1. Clone the repository

git clone [https://github.com/tisabhinavagarwal/smartcleaner]
cd smartclean-pipeline



2. Create and activate a Virtual Environment

Windows:

python -m venv venv
venv\Scripts\activate



macOS / Linux:

python3 -m venv venv
source venv/bin/activate



3. Install Dependencies

pip install -r requirements.txt



🏃‍♂️ How to Run Locally

Launch the pipeline using the Streamlit CLI:

streamlit run app.py



The application will automatically open in your default web browser at http://localhost:8501.

☁️ Cloud Deployment (Streamlit Community Cloud)

This application is fully compatible with immediate, free deployment via Streamlit Community Cloud:

Push this complete repository to your GitHub account.

Sign in to Streamlit Community Cloud.

Click New App and link your GitHub repository.

Set the Main file path to app.py and click Deploy.

Your application will be live in minutes and accessible via a public web domain!

📊 Export Artifacts

Upon successful execution, the pipeline generates:

clean_output.csv: The finalized, standardized dataset.

cleaning_report.xlsx: A multi-sheet Excel file containing the clean data, an execution metrics report, and a dedicated Quarantined_Rows sheet (if malformed data was detected).

quarantined_rows.csv (Conditional): A direct CSV export of structurally broken rows for manual intervention.

🔮 Future Improvements

Database Connectors: Add direct ingestion and write-back functionality for PostgreSQL and Snowflake.

Custom Regex Rules: Allow users to define custom regex patterns for specific organizational ID formats via the UI.

Data Profiling PDF: Generate a downloadable PDF report with data distribution histograms before and after cleaning.

Docker Containerization: Package the app via a Dockerfile for single-command enterprise deployments.
