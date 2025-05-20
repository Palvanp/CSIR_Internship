# Vehicle Data Analytics Dashboard

This repository hosts a comprehensive Streamlit-based dashboard for analyzing vehicle registration data in India from 2009 to 2025. Built as part of an internship project under the mentorship of Dr. Mukti Advani at CSIR-CRRI, the application provides insightful visualizations and interactive filtering features to explore patterns and trends in transportation data.

## 🔍 Features

- Interactive dashboards segmented by fuel type, vehicle class, norms, and more
- Filters by state, fuel type, year range, and vehicle class
- Natural language query functionality (Ask with Text)
- Downloadable insights and summaries
- Distinct views for Electric Vehicles (EV) and non-EV data

## 🏗️ Project Structure

```
├── app.py                       # Main Streamlit app
├── requirements.txt            # Python dependencies
├── README.md                   # Repository overview
├── DataBase/
│   ├── data/                   # Contains all raw CSV data files (2009–2025)
│   ├── Excel files/            # Cleaned Excel files used in SQL conversion
│   └── vehicle_all.sql         # PostgreSQL database schema
├── Dashboard/                  # Contains graph generation scripts for dashboards
├── State_RTO_SQL/             # SQL files for state and RTO data
└── Convert_CSV_to_SQL/        # Scripts to convert CSV data to PostgreSQL
```

## 🚀 Getting Started

### Prerequisites

Ensure you have the following installed:
- Python 3.9+
- PostgreSQL installed and running locally

Install Python packages:
```bash
pip install -r requirements.txt
```

### Cloning the Repository

```bash
git clone https://github.com/<your-username>/vehicle-data-analytics.git
cd vehicle-data-analytics
```

### Setting Up the Database

1. Make sure your PostgreSQL database is set up and configured.
2. Update database credentials if needed in your conversion scripts or `app.py`.
3. If the data files have been updated or changed, run the relevant script from `Convert_CSV_to_SQL` to populate or update the database.

### Running the Application

```bash
streamlit run app.py
```

## 📁 Updating Data

- New data can be downloaded in the same CSV format (2009–2025) from [Parivahan Dashboard](https://analytics.parivahan.gov.in/analytics/publicdashboard/vahanpublicreport?lang=en).
- Place updated CSVs in the `/DataBase/data` folder.
- If structural changes are detected, rerun the CSV to SQL conversion scripts.

## 📖 Credits

Developed during a research internship at CSIR-CRRI under the guidance of **Dr. Mukti Advani** (Senior Principal Scientist, TPE Division).

---

© 2025 Vehicle Data Analytics – CSIR-CRRI Internship Project