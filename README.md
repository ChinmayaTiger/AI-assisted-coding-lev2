# AI Assisted Coding - Level 2

## Customer 360 Analytics Application

This project builds a Customer 360 view by processing customer, order, and support ticket data.

The project includes:

- Data processing pipeline
- Customer analytics outputs
- Data quality checks
- Automated tests using pytest
- Streamlit dashboard for visualization

---

# Project Structure

```
AI-assisted-coding-lev2
│
├── data
│   ├── customers_source.xlsx
│   ├── orders_source.xlsx
│   └── support_tickets_source.xlsx
│
├── outputs
│   ├── customer_360.csv
│   ├── category_revenue.csv
│   ├── region_revenue.csv
│   ├── kpi_summary.csv
│   └── data_quality_report.csv
│
├── src
│   ├── index.py
│   └── customer_360_app.py
│
├── tests
│   └── test_pipeline.py
│
├── requirements.txt
└── README.md
```

---

# Setup Instructions

## 1. Clone the repository

```bash
git clone <repository-url>

cd AI-assisted-coding-lev2
```

---

## 2. Create Python Virtual Environment

```bash
py -m venv .venv
```

Activate environment:

### Windows PowerShell

```powershell
.\.venv\Scripts\activate
```

---

## 3. Install Dependencies

Install required packages:

```powershell
py -m pip install -r requirements.txt
```

---

# Running the Data Pipeline

The main data processing logic is available in:

```
src/index.py
```

Run:

```powershell
py src/index.py
```

This generates output files inside:

```
outputs/
```

Generated files:

- customer_360.csv
- category_revenue.csv
- region_revenue.csv
- kpi_summary.csv
- data_quality_report.csv

---

# Running the Streamlit Dashboard

The Streamlit application is:

```
src/customer_360_app.py
```

Run:

```powershell
py -m streamlit run src/customer_360_app.py
```

The application will open in:

```
http://localhost:8501
```

---

# Running Tests

Tests are available in:

```
tests/test_pipeline.py
```

Run all tests:

```powershell
py -m pytest
```

Run with details:

```powershell
py -m pytest -v
```

---

# Understanding the Application Flow

```
Source Excel Files
        |
        |
        v
src/index.py
(Data Processing Pipeline)
        |
        |
        v
outputs/
(CSV Analytics Results)
        |
        |
        v
src/customer_360_app.py
(Streamlit Dashboard)
```

---

# Development Notes

Python version:

```
Python 3.x
```

Main application files:

```
src/index.py
src/customer_360_app.py
```

Testing framework:

```
pytest
```

Dashboard framework:

```
Streamlit
```

---

# Sharing Project Structure

To display the folder structure:

Windows PowerShell:

```powershell
tree /F /A
```

This helps understand the project layout when requesting code changes or reviews.