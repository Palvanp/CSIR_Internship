# ---------------------- Imports ----------------------
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from io import BytesIO
import json
import os
import re
from difflib import get_close_matches
from xlsxwriter import Workbook

# ---------------------- Config ----------------------
st.set_page_config(page_title="Vehicle Dashboard India", layout="wide")  # Set Streamlit page configuration

# ---------------------- DB Connection ----------------------
@st.cache_data
def load_data(query):
    # Load data from SQLite DB with caching
    with sqlite3.connect(r"vehicle_analysis_1.db") as conn: # change the path if required
        df = pd.read_sql_query(query, conn)
        # Remove rows where values are identical to column names (data cleaning)
        for col in ['row_value', 'column_value']:
            if col in df.columns:
                df = df[df[col] != col]
        return df

# ---------------------- Setup: Load State Mapping ----------------------
@st.cache_data
def load_state_rto_mapping():
    # Load mapping of state codes to full names and RTOs from JSON
    with open("state_rto_data.json", "r") as f: # change the path if required
        data = json.load(f)
        return {
            entry["State Code"]: {
                "state_name": entry["Full State Name"].strip(),
                "rtos": [rto.strip() for rto in entry["RTO List"].split(",")]
            }
            for entry in data
        }

state_rto_map = load_state_rto_mapping()
abbr_to_full = {abbr: info["state_name"] for abbr, info in state_rto_map.items()}

# ---------------------- Utility: Load CSV Data ----------------------
def load_csv_data(folder_path):
    # Load and concatenate all CSVs in given folder
    all_data = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".csv"):
            file_path = os.path.join(folder_path, filename)
            try:
                df = pd.read_csv(file_path)
                df = df.iloc[:-1]  # Remove last row (summary/total row if present)
                year = filename.split('_')[-1].replace('.csv', '')
                df['year'] = year
                all_data.append(df)
            except Exception:
                pass
    return pd.concat(all_data, ignore_index=True) if all_data else None

# ---------------------- Main Dashboard ----------------------
def dashboard_overview(): 
    st.title("📊 Vehicle Registration Summary")

    # Load required datasets
    df_total = load_csv_data(r"DataBase\Excel files\state_wise_total") # change the path if required
    df_ev = load_csv_data(r"DataBase\Excel files\State_wise_total(EV)") # change the path if required
    df_fuel = load_data("SELECT * FROM fuel_vs_state")
    df_class = load_data("SELECT * FROM vehicle_class_vs_state")
    df_cat = load_data("SELECT * FROM vehicle_category_group_vs_state")

    # Convert relevant columns to numeric type for analysis
    df_total['count'] = pd.to_numeric(df_total['Total Consolidated'], errors='coerce').fillna(0)
    df_ev['count'] = pd.to_numeric(df_ev['Total Consolidated'], errors='coerce').fillna(0)
    df_fuel['count'] = pd.to_numeric(df_fuel['count'], errors='coerce').fillna(0)
    df_class['count'] = pd.to_numeric(df_class['count'], errors='coerce').fillna(0)
    df_cat['count'] = pd.to_numeric(df_cat['count'], errors='coerce').fillna(0)

    df_total['year'] = pd.to_numeric(df_total['year'], errors='coerce')
    df_ev['year'] = pd.to_numeric(df_ev['year'], errors='coerce')

    # Compute national statistics
    total_count = df_total['count'].sum()
    total_ev = df_ev['count'].sum()
    ev_share = round((total_ev / total_count) * 100, 2) if total_count else 0

    # Display key metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Vehicles", f"{int(total_count):,}")
    col2.metric("EV Registered", f"{int(total_ev):,}")
    col3.metric("EV Share", f"{ev_share}%")

    # ---------------------- Year-wise State Registration ----------------------
    if not df_total.empty:
        min_year_total, max_year_total = int(df_total["year"].min()), int(df_total["year"].max())
        selected_years_total = st.slider("Select Year Range for Registration", min_year_total, max_year_total, (min_year_total, max_year_total))
        df_total_filtered = df_total[(df_total["year"] >= selected_years_total[0]) & (df_total["year"] <= selected_years_total[1])]
        fig1 = px.line(df_total_filtered, x="year", y="count", color="State", title=f"Year-wise Registration by State ({selected_years_total[0]} - {selected_years_total[1]})")
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.warning("No data available for year-wise registration.")

    # ---------------------- Fuel Type Trend ----------------------
    fuel_types = sorted(df_fuel['row_value'].dropna().unique())
    fuel_options = ["Select All"] + fuel_types
    selected_fuel_types = st.multiselect("Select Fuel Type(s)", fuel_options, help="Select 'Select All' to include all fuel types")
    if "Select All" in selected_fuel_types:
        selected_fuel_types = fuel_types
    if selected_fuel_types:
        df_fuel_filtered = df_fuel[df_fuel['row_value'].isin(selected_fuel_types)]
        df_fuel_grouped = df_fuel_filtered.groupby(['year', 'row_value'])['count'].sum().reset_index()
        fig2 = px.area(df_fuel_grouped, x="year", y="count", color="row_value", title="National Fuel Type Trend Over Years")
        st.plotly_chart(fig2, use_container_width=True)

    # ---------------------- Vehicle Class Trend ----------------------
    vehicle_classes = sorted(df_class['row_value'].dropna().unique())
    class_options = ["Select All"] + vehicle_classes
    selected_vehicle_classes = st.multiselect("Select Vehicle Class(es)", class_options, help="Select 'Select All' to include all classes")
    if "Select All" in selected_vehicle_classes:
        selected_vehicle_classes = vehicle_classes
    if selected_vehicle_classes:
        df_class_filtered = df_class[df_class['row_value'].isin(selected_vehicle_classes)]
        df_class_grouped = df_class_filtered.groupby(['year', 'row_value'])['count'].sum().reset_index()
        fig3 = px.area(df_class_grouped, x="year", y="count", color="row_value", title="Vehicle Class Trend Across India")
        st.plotly_chart(fig3, use_container_width=True)

    # ---------------------- EV Adoption by State ----------------------
    ev_states = sorted(df_ev['State'].dropna().unique())
    ev_options = ["Select All"] + ev_states
    selected_ev_states = st.multiselect("Select States for EV Adoption", ev_options, help="Select 'Select All' to include all states")
    if "Select All" in selected_ev_states:
        selected_ev_states = ev_states
    if selected_ev_states:
        df_ev_filtered = df_ev[df_ev['State'].isin(selected_ev_states)]
        df_ev_statewise = df_ev_filtered.groupby("State")["count"].sum().reset_index().sort_values(by="count", ascending=False).head(10)
        fig5 = px.bar(df_ev_statewise, x="State", y="count", title="Top 10 States by EV Registration")
        st.plotly_chart(fig5, use_container_width=True)

        # ---------------------- EV vs Total Registration Over Time ----------------------
        df_ev_vs_total = df_ev_filtered.groupby("year")["count"].sum().reset_index()
        df_total_vs_ev = pd.merge(df_total.groupby("year")['count'].sum().reset_index(), df_ev_vs_total, on="year", suffixes=('_total', '_ev'))
        fig6 = px.line(df_total_vs_ev, x="year", y=["count_total", "count_ev"], title="EV vs Total Vehicle Registrations Over Time")
        st.plotly_chart(fig6, use_container_width=True)


# ---------------------- EV Insights ----------------------
def ev_insights():
    st.title("⚡ Electric Vehicle (EV) Analysis")

    # Load State Abbreviation Mapping from JSON
    with open("state_rto_data.json", "r") as f: # change the path if required
        state_data = json.load(f)

    state_code_to_name = {
        entry["State Code"].strip().lower(): entry["Full State Name"].strip()
        for entry in state_data
    }
    state_name_to_code = {
        entry["Full State Name"].strip(): entry["State Code"].strip().lower()
        for entry in state_data
    }

    # 1️⃣ EV Registrations by Fuel Type (State-wise)
    df_ev_state = load_data("SELECT * FROM fuel_vs_stateev")
    unique_states = df_ev_state["column_value"].dropna().unique()
    state_full_names = [state_code_to_name.get(state.strip().lower(), state) for state in unique_states]
    
    state_selection = st.selectbox("Select a State", sorted(state_full_names))
    selected_abbr = state_name_to_code.get(state_selection.strip(), state_selection.strip().lower())
    filtered = df_ev_state[df_ev_state["column_value"].str.lower() == selected_abbr]

    fig1 = px.bar(
        filtered, x="year", y="count", color="row_value", barmode="group",
        title=f"EV Registrations by Fuel Type in {state_selection}"
    )
    st.plotly_chart(fig1, use_container_width=True)

    # 2️⃣ EV Growth Over Years (National) with Year Range Filter
    st.subheader("📈 National EV Growth Over Years")
    ev_growth = df_ev_state.groupby("year")["count"].sum().reset_index()

    if not ev_growth.empty:
        min_year_nat, max_year_nat = int(ev_growth["year"].min()), int(ev_growth["year"].max())
        selected_years_nat = st.slider("Select Year Range (National)", min_year_nat, max_year_nat, (min_year_nat, max_year_nat))
        ev_growth = ev_growth[(ev_growth["year"] >= selected_years_nat[0]) & (ev_growth["year"] <= selected_years_nat[1])]
    else:
        st.warning("No national EV data available for selected range.")

    fig2 = px.line(ev_growth, x="year", y="count", title="Total EVs Registered per Year in India")
    st.plotly_chart(fig2, use_container_width=True)

# ---------------------- Fuel-Norm Distribution ----------------------
def fuel_norm_distribution_dashboard(root_dir, state_mapping_file, start_year=2009, end_year=2025):
    
    # Folder paths
    folders = {
        "statewise": os.path.join(root_dir, "Fuel_vs_state"),
        "norms": os.path.join(root_dir, "Norm_vs_state"),
        "fuelwise": os.path.join(root_dir, "Fuel_vs_Norm")
    }

    # Load the state mapping JSON file
    with open(state_mapping_file, 'r') as f:
        state_mapping = json.load(f)

    # Create a dictionary mapping state codes to full state names
    state_dict = {item["State Code"].upper(): item["Full State Name"].strip() for item in state_mapping}

    def load_data(folder_path, year_file):
        file_path = os.path.join(folder_path, year_file)
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            if "Total" in df.columns:
                df = df.drop(columns=["Total"])
            if df.iloc[:, 0].str.contains("Total", na=False).any():
                df = df[~df.iloc[:, 0].str.contains("Total", na=False)]
            df["Year"] = int(year_file.split(".")[0])
            return df
        else:
            st.warning(f"File not found: {file_path}")
            return pd.DataFrame()

    def load_data_for_year_range(folder_path, start_year, end_year):
        combined_df = pd.DataFrame()
        for year in range(start_year, end_year + 1):
            year_file = f"{year}.csv"
            df = load_data(folder_path, year_file)
            combined_df = pd.concat([combined_df, df], ignore_index=True)
        return combined_df

    statewise_df = load_data_for_year_range(folders["statewise"], start_year, end_year)
    norms_df = load_data_for_year_range(folders["norms"], start_year, end_year)
    fuelwise_df = load_data_for_year_range(folders["fuelwise"], start_year, end_year)

    st.title("🛢 Fuel Allocation & Emission Norms Dashboard (2009–2025)")

    tab1, tab2, tab3 = st.tabs([
        "📍 Fuel Distribution over States",
        "📊 Norm Distribution by State",
        "🔥 Emission by Fuel Type"
    ])

    with tab1:
        st.subheader("Fuel Distribution Across States")
        if not statewise_df.empty:
            melted_df = pd.melt(statewise_df, id_vars=["Fuel", "Year"], var_name="State", value_name="Fuel_Amount")
            melted_df["State"] = melted_df["State"].apply(lambda x: state_dict.get(x.upper(), x))

            selected_states = st.multiselect("Select States", ["Select All"] + sorted(melted_df["State"].unique()), default=[], key="state_selection")
            if "Select All" in selected_states:
                selected_states = list(melted_df["State"].unique())

            year_range = st.slider("Select Year Range", min_value=start_year, max_value=end_year, value=(start_year, end_year), key="fuel_state_year")
            filtered_df = melted_df[(melted_df["State"].isin(selected_states)) &
                                    (melted_df["Year"].between(year_range[0], year_range[1]))]

            fig1 = px.bar(filtered_df, x="State", y="Fuel_Amount", color="Fuel",
                          title=f"Fuel Distribution from {year_range[0]} to {year_range[1]}",
                          labels={"Fuel_Amount": "Amount (in units)"}, barmode="group")
            st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.subheader("Emission Norm Distribution by State")
        if not norms_df.empty:
            melted_norms = pd.melt(norms_df, id_vars=["Norms", "Year"], var_name="State", value_name="Count")
            melted_norms["State"] = melted_norms["State"].apply(lambda x: state_dict.get(x.upper(), x))

            selected_states = st.multiselect("Select States", ["Select All"] + sorted(melted_norms["State"].unique()), default=[], key="norm_state_selection")
            if "Select All" in selected_states:
                selected_states = list(melted_norms["State"].unique())

            year_range = st.slider("Select Year Range", min_value=start_year, max_value=end_year, value=(start_year, end_year), key="norm_state_year")
            filtered_norms = melted_norms[(melted_norms["State"].isin(selected_states)) &
                                          (melted_norms["Year"].between(year_range[0], year_range[1]))]

            fig2 = px.bar(filtered_norms, x="State", y="Count", color="Norms",
                          title=f"Emission Norms Distribution from {year_range[0]} to {year_range[1]}",
                          labels={"Count": "Count of Norms"}, barmode="group")
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("Norm Emissions by Fuel Type and Year")

        base_path = r"DataBase\data" # change the path if required
        fuel_vs_norm_path = os.path.join(base_path, "Fuel_vs_Norm")
        norm_vs_category_path = os.path.join(base_path, "norm_vs_category")

        available_files = os.listdir(fuel_vs_norm_path)
        available_years = sorted([int(f.split(".")[0]) for f in available_files if f.endswith(".csv")])
        year_range = st.slider("Select Year Range", min_value=min(available_years), max_value=max(available_years),
                            value=(min(available_years), max(available_years)), key="tab3_year_range")

        def load_and_standardize_csv(path, melt_type=None):
            df = pd.read_csv(path)
            df.columns = [col.strip().lower() for col in df.columns]

            if melt_type == "fuel_norm" and "fuel" in df.columns:
                df = df.melt(id_vars='fuel', var_name='norm', value_name='emission')
            elif melt_type == "norm_category" and "norms" in df.columns:
                df = df.rename(columns={"norms": "norm"})
                df = df.melt(id_vars='norm', var_name='vehicle_category', value_name='count')
            return df

        fuel_vs_norm_combined = pd.DataFrame()
        norm_vs_category_combined = pd.DataFrame()

        for year in range(year_range[0], year_range[1] + 1):
            try:
                fuel_df = load_and_standardize_csv(os.path.join(fuel_vs_norm_path, f"{year}.csv"), melt_type="fuel_norm")
                fuel_df["year"] = year
                fuel_vs_norm_combined = pd.concat([fuel_vs_norm_combined, fuel_df], ignore_index=True)

                norm_df = load_and_standardize_csv(os.path.join(norm_vs_category_path, f"{year}.csv"), melt_type="norm_category")
                norm_df["year"] = year
                norm_vs_category_combined = pd.concat([norm_vs_category_combined, norm_df], ignore_index=True)
            except Exception as e:
                st.warning(f"Error loading data for {year}: {e}")

        fuel_options = sorted(fuel_vs_norm_combined['fuel'].dropna().unique())
        category_options = sorted(norm_vs_category_combined['vehicle_category'].dropna().unique())

        fuel_options = [f for f in fuel_options if f.lower() != "total"]
        category_options = [c for c in category_options if c.lower() != "total"]

        selected_fuels = st.multiselect("Select Fuel Type(s)", options=["All"] + fuel_options, default=["All"])
        selected_categories = st.multiselect("Select Vehicle Category(s)", options=["All"] + category_options, default=["All"])

        if "All" in selected_fuels:
            selected_fuels = fuel_options
        if "All" in selected_categories:
            selected_categories = category_options

        # Emissions: Fuel vs Norms
        st.markdown("### Norms vs Fuel")
        fuel_norm_filtered = fuel_vs_norm_combined[
            fuel_vs_norm_combined['fuel'].isin(selected_fuels) &
            fuel_vs_norm_combined['year'].between(year_range[0], year_range[1])
        ]
        if not fuel_norm_filtered.empty:
            fig1 = px.bar(fuel_norm_filtered, x="norm", y="emission", color="fuel",
                        title=f"Emissions by Fuel Types ({year_range[0]}–{year_range[1]})",
                        labels={"emission": "Emission", "norm": "Norm Type"})
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No emission data available for selected fuel types and years.")

        # Norm vs Vehicle Category
        st.markdown("### Norm vs Vehicle Category")
        norm_cat_filtered = norm_vs_category_combined[
            (norm_vs_category_combined['vehicle_category'].isin(selected_categories)) &
            norm_vs_category_combined['year'].between(year_range[0], year_range[1])
        ]
        if not norm_cat_filtered.empty:
            fig2 = px.bar(norm_cat_filtered, x="norm", y="count", color="vehicle_category",
                        title=f"Emissions by Vehicle Categories ({year_range[0]}–{year_range[1]})",
                        labels={"count": "Count", "norm": "Norm Type"})
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No norm vs category data available for selected vehicle categories and years.")

        # 🔝 Top Fuel Types by Total Emissions
        st.markdown("### 🔝 Top Fuel Types by Total Emissions")
        top_fuel_emissions = fuel_norm_filtered.groupby("fuel")["emission"].sum().reset_index().sort_values(by="emission", ascending=False)
        if not top_fuel_emissions.empty:
            fig3 = px.bar(top_fuel_emissions, x="fuel", y="emission", color="fuel",
                        title="Top Fuel Types by Total Emissions",
                        labels={"emission": "Total Emission", "fuel": "Fuel Type"})
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No data for top fuel types.")

        # 🔝 Top Vehicle Categories by Norm Count
        st.markdown("### 🔝 Top Vehicle Categories by Total Emissions")
        top_categories = norm_cat_filtered.groupby("vehicle_category")["count"].sum().reset_index().sort_values(by="count", ascending=False)
        if not top_categories.empty:
            fig4 = px.bar(top_categories, x="vehicle_category", y="count", color="vehicle_category",
                        title="Top Vehicle Categories by Norm Count",
                        labels={"count": "Total Count", "vehicle_category": "Category"})
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No data for top vehicle categories.")

        # 📥 Download Filtered Data
        st.markdown("### 📥 Download Filtered Data")
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            fuel_norm_filtered.to_excel(writer, sheet_name="Fuel_vs_Norm", index=False)
            norm_cat_filtered.to_excel(writer, sheet_name="Norm_vs_Category", index=False)
            top_fuel_emissions.to_excel(writer, sheet_name="Top_Fuels", index=False)
            top_categories.to_excel(writer, sheet_name="Top_Categories", index=False)

        st.download_button("Download Excel File", data=output.getvalue(),
                        file_name="filtered_emission_data.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ---------------------- vehicle Class & Vehicle Category ----------------------
def vehicle_class_category():
    st.title("🚗 Vehicle Class & Category")
     # Load data
    df_class = load_data("SELECT * FROM vehicle_class_vs_state")
    df_cat = load_data("SELECT * FROM vehicle_category_group_vs_state")

    # Unique states
    unique_states = df_class["column_value"].dropna().unique()
    selected_state = st.selectbox("Select a State", sorted(unique_states), key="state_select")

    # Filter state-wise
    df_class_filtered = df_class[df_class["column_value"] == selected_state]
    df_cat_filtered = df_cat[df_cat["column_value"] == selected_state]
    

    # Tabs for Class and Category
    tab1, tab2 = st.tabs(["🚘 Vehicle Class", "🚛 Vehicle Category"])

    with tab1:
        st.subheader(f"Vehicle Class Trend - {selected_state}")

        # Row_value filter for class
        row_class_values = sorted(df_class_filtered["row_value"].dropna().unique())
        selected_class_types = st.multiselect(
            "Select Vehicle Class Types",
            options=row_class_values,
            default=[],
            key="class_select",
            help="Leave empty to show all vehicle classes"
        )
        if selected_class_types:
            df_class_filtered = df_class_filtered[df_class_filtered["row_value"].isin(selected_class_types)]

        # Graph
        fig1 = px.line(
            df_class_filtered,
            x="year",
            y="count",
            color="row_value",
            title=f"{selected_state} - Vehicle Class Trend"
        )
        st.plotly_chart(fig1, use_container_width=True, key="vehicle_class_trend")

        # Download button for vehicle class
        csv_class = df_class_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Vehicle Class Data",
            data=csv_class,
            file_name=f"{selected_state}_vehicle_class_data.csv",
            mime="text/csv"
        )

    with tab2:
        st.subheader(f"Vehicle Category Trend - {selected_state}")

        # Row_value filter for category
        row_cat_values = sorted(df_cat_filtered["row_value"].dropna().unique())
        selected_cat_types = st.multiselect(
            "Select Vehicle Category Types",
            options=row_cat_values,
            default=[],
            key="category_select",
            help="Leave empty to show all vehicle categories"
        )
        if selected_cat_types:
            df_cat_filtered = df_cat_filtered[df_cat_filtered["row_value"].isin(selected_cat_types)]

        # Graph
        fig2 = px.line(
            df_cat_filtered,
            x="year",
            y="count",
            color="row_value",
            title=f"{selected_state} - Vehicle Category Trend"
        )
        st.plotly_chart(fig2, use_container_width=True, key="vehicle_category_trend")

        # Download button for vehicle category
        csv_category = df_cat_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Vehicle Category Data",
            data=csv_category,
            file_name=f"{selected_state}_vehicle_category_data.csv",
            mime="text/csv")

# ---------------------- Ask With LLM ----------------------
def ask_with_llm():
    """
    Single function to run the entire Streamlit dashboard:
    - Loads databases and mappings
    - Parses natural-language queries
    - Executes queries and renders results
    - Allows download of resulting data
    """
    # ---------- CONFIG ----------
    DATABASE_PATH  = r"DataBase\vehicle_analysis_1.db" # change the path if required
    STATE_RTO_JSON = r"State_RTO_mapping\state_rto_data.json" # change the path if required

    TABLE_MAPPINGS = {
        'fuel':    {'state': 'fuel_vs_state',                   'state_ev': 'fuel_vs_stateev',                   'rto': 'fuel_vs_rto',                   'rto_ev': 'fuel_vs_rtoev'},
        'norm':    {'state': 'norm_vs_state',                   'state_ev': 'norm_vs_stateev',                   'rto': 'norm_vs_rto',                   'rto_ev': 'norm_vs_rtoev'},
        'category':{'state': 'vehicle_category_group_vs_state', 'state_ev': 'vehicle_category_group_vs_stateev', 'rto': 'vehicle_category_group_vs_rto', 'rto_ev': 'vehicle_category_group_vs_rtoev'},
        'class':   {'state': 'vehicle_class_vs_state',          'state_ev': 'vehicle_class_vs_stateev',          'rto': None,                             'rto_ev': 'vehicle_class_vs_rtoev'}
    }
    TABLE_TOTALS = {'state': 'state_wise_total', 'state_ev': 'state_wise_totalev'}

    @st.cache_data
    def load_all():
        # Load DB tables
        conn = sqlite3.connect(DATABASE_PATH)
        df_map = {}
        for dims in TABLE_MAPPINGS.values():
            for tbl in dims.values():
                if tbl and tbl not in df_map:
                    df_map[tbl] = pd.read_sql(f"SELECT * FROM {tbl}", conn)
        for tbl in TABLE_TOTALS.values():
            if tbl not in df_map:
                df_map[tbl] = pd.read_sql(f"SELECT * FROM {tbl}", conn)
        conn.close()

        # Load JSON mapping
        with open(STATE_RTO_JSON, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        state_rto_map = {}
        if isinstance(raw, dict):
            for state, rtos in raw.items():
                state_rto_map[state.lower()] = rtos
        elif isinstance(raw, list):
            for entry in raw:
                if isinstance(entry, dict):
                    for state, rtos in entry.items():
                        state_rto_map[state.lower()] = rtos
        else:
            st.error("Invalid JSON format for state→RTO mapping.")

        return df_map, state_rto_map

    # Load data and mappings
    df_map, state_rto_map = load_all()
    STATES = df_map['fuel_vs_state']['column_value'].unique().tolist()
    RTOS   = df_map['fuel_vs_rto']['column_value'].unique().tolist()

    # Parsers
    def parse_ev(q: str) -> bool:
        return bool(re.search(r"\bEV\b|electric|evs?\b", q, re.IGNORECASE))

    def parse_dimension(q: str) -> str | None:
        ql = q.lower()
        for d in TABLE_MAPPINGS:
            if re.search(rf"\b{d}\b", ql):
                return d
        for tok in re.findall(r"\w+", ql):
            match = get_close_matches(tok, TABLE_MAPPINGS.keys(), n=1, cutoff=0.8)
            if match:
                return match[0]
        return None

    def parse_year_filter(q: str) -> tuple[str|None,int|tuple[int,int]|None]:
        ql = q.lower()
        # Check for year range like "from 2018 to 2022"
        if m := re.search(r"(from|between)\s*(20\d{2})\s*(to|-)\s*(20\d{2})", ql):
            y1, y2 = int(m.group(2)), int(m.group(4))
            return ('range', (min(y1, y2), max(y1, y2)))
        if m := re.search(r"after\s*(20\d{2})", ql):   return ('>',  int(m.group(1)))
        if m := re.search(r"before\s*(20\d{2})", ql):  return ('<',  int(m.group(1)))
        if m := re.search(r"in\s*(20\d{2})", ql):      return ('==', int(m.group(1)))
        if m := re.search(r"\b(20\d{2})\b", ql):       return ('==', int(m.group(1)))
        return (None, None)


    def parse_top_n(q: str) -> int|None:
        ql = q.lower()
        if m := re.search(r"top\s*(\d+)\s*states?\b", ql):
            return int(m.group(1))
        return None

    def parse_location(q: str) -> tuple[str|None,str|None]:
        ql = q.lower()
        for r in RTOS:
            if r.lower() in ql:
                return ('rto', r)
        for s in STATES:
            if s.lower() in ql:
                return ('state', s)
        for tok in re.findall(r"\w+", ql):
            m = get_close_matches(tok, [s.lower() for s in STATES], n=1, cutoff=0.8)
            if m:
                return ('state', STATES[[s.lower() for s in STATES].index(m[0])])
        for tok in re.findall(r"\w+", ql):
            m = get_close_matches(tok, [r.lower() for r in RTOS], n=1, cutoff=0.8)
            if m:
                return ('rto', RTOS[[r.lower() for r in RTOS].index(m[0])])
        return (None, None)

    # Streamlit UI
    st.title("🚗 Vehicle Data Dashboard (Ask Anything)")
    query = st.text_input("🔍 Ask your vehicle data question:", placeholder="e.g., Norm-wise registrations in Maharashtra in 2024")
    if not query:
        return

    ev       = parse_ev(query)
    dim      = parse_dimension(query)
    op, year = parse_year_filter(query)
    top_n    = parse_top_n(query)
    loc_type, loc = parse_location(query)

    # Determine table
    if dim:
        opts   = TABLE_MAPPINGS[dim]
        suffix = (f"{loc_type}{'_ev' if ev else ''}" if loc_type in ('state','rto') else ('state_ev' if ev else 'state'))
        tbl_name = opts.get(suffix) or (opts['state_ev'] if ev else opts['state'])
    else:
        tbl_name = TABLE_TOTALS['state_ev' if ev else 'state']

    df = df_map[tbl_name]
    if op and year:
        if op == 'range' and isinstance(year, tuple):
            df = df[df['year'].between(year[0], year[1])]
        else:
            df = df.query(f"year {op} @year")
    if loc_type == 'rto':
        df = df[df['column_value']==loc]
    elif loc_type == 'state':
        if 'rto' in tbl_name:
            rto_list = state_rto_map.get(loc.lower(), [])
            df = df[df['column_value'].isin(rto_list)]
        else:
            df = df[df['column_value']==loc]

    # Render
    if dim:
        if top_n and loc_type is None:
            agg    = df.groupby('column_value', as_index=False)['count'].sum()
            result = agg.nlargest(top_n, 'count')
            title  = f"Top {top_n} states by {dim}{' (EV)' if ev else ''}" + (f" in {year}" if op=='==' else "")
            fig    = px.bar(result, x='column_value', y='count', labels={'column_value':'State','count':'Total'})
        elif loc_type:
            brk    = df.groupby('row_value', as_index=False)['count'].sum().sort_values('count', ascending=False)
            title  = f"{dim.capitalize()} breakdown for {loc_type.upper()}: {loc}" + (f" after {year}" if op=='>' else "")
            result = brk.rename(columns={'row_value':dim.capitalize(),'count':'Total'})
            fig    = px.bar(brk, x='row_value', y='count', labels={'row_value':dim.capitalize(),'count':'Total'})
        else:
            agg    = df.groupby('column_value', as_index=False)['count'].sum()
            title  = f"State-wise totals by {dim}{' (EV)' if ev else ''}"
            result = agg.rename(columns={'column_value':'State','count':'Total'})
            fig    = px.bar(agg, x='column_value', y='count', labels={'column_value':'State','count':'Total'})
    else:
        if loc_type == 'state':
            ts     = df[df['column_value']==loc].groupby('year', as_index=False)['count'].sum()
            title  = f"Total registrations for STATE: {loc}{' (EV)' if ev else ''}"
            result = ts.rename(columns={'count':'Total'})
            fig    = px.line(ts, x='year', y='count', labels={'count':'Total'})
        else:
            ts     = df.groupby('year', as_index=False)['count'].sum()
            title  = f"Overall total registrations{' (EV)' if ev else ''}"
            result = ts.rename(columns={'count':'Total'})
            fig    = px.line(ts, x='year', y='count', labels={'count':'Total'})

    st.subheader(title)
    st.dataframe(result)

    # Append year info to result if applicable
    if op and year:
        if op == '==':
            year_info = f"In {year}"
        elif op == '>':
            year_info = f"After {year}"
        elif op == '<':
            year_info = f"Before {year}"
        elif op == 'range' and isinstance(year, tuple):
            year_info = f"From {year[0]} to {year[1]}"
        else:
            year_info = f"Year Filter: {op} {year}"
        result['Query_Year_Info'] = year_info

    # Download option
    csv = result.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download Result as CSV", data=csv, file_name="query_result.csv", mime='text/csv')

    st.plotly_chart(fig)
    

# Run the entire app
# ask_with_llm()
        
# ---------------------- Sidebar ----------------------
st.sidebar.title("🔍 Navigation")
section = st.sidebar.radio("Go to", [
    "Dashboard Overview",
    "EV Insights",
    "Fuel Norm Analysis(StateWise)",
    "Vehicle Class & Category",
    "Ask with Text (LLM)"
])

# ---------------------- Page Routing ----------------------
if section == "Dashboard Overview":
    dashboard_overview()
elif section == "EV Insights":
    ev_insights()
elif section == "Fuel Norm Analysis(StateWise)":
    fuel_norm_distribution_dashboard(
    root_dir=r"DataBase\data", # change the path if required
    state_mapping_file=r'State_RTO_Mapping\state_rto_data.json' # change the path if required
)
elif section == "Vehicle Class & Category":
    vehicle_class_category()
elif section == "Ask with Text (LLM)":
    ask_with_llm()
    st.markdown("#### 💬 Try asking:")
    st.markdown("- Top 5 states by fuel in 2022  ")
    st.markdown("- Norm-wise registrations in Maharashtra in 2024 ")
    st.markdown("- Electric (EV) norm-wise registrations in Karnataka after 2021 ")
    st.markdown("- Fuel-wise registrations in Delhi in 2020")
    st.markdown("- Vehicle classes by registrations in Tamil Nadu in 2022 ")
