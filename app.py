import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import json
import io

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Interactive Data Visualization Dashboard",
    page_icon="📊",
    layout="wide"
)

# =========================
# DATABASE INIT
# =========================
DB_PATH = "graph_configs.db"
conn = sqlite3.connect(DB_PATH)
conn.execute("""
CREATE TABLE IF NOT EXISTS graphs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    chart_type TEXT,
    x_param TEXT,
    y_param TEXT,
    filters TEXT
)
""")
conn.commit()

# =========================
# HEADER
# =========================
st.title("📊 Interactive Data Visualization Dashboard")
st.caption("Upload → Filter → Visualize → Save → Export")

# =========================
# FILE UPLOAD
# =========================
uploaded_file = st.sidebar.file_uploader("Upload Dataset", type=["csv", "xlsx"])

CHART_TYPES = ["Bar", "Line", "Scatter", "Pie", "Histogram"]

if uploaded_file:

    # =========================
    # LOAD DATA
    # =========================
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success("✅ Dataset loaded successfully")

    # =========================
    # BASIC INFO
    # =========================
    col1, col2, col3 = st.columns(3)
    col1.metric("Rows", len(df))
    col2.metric("Columns", len(df.columns))
    col3.metric("Missing Values", df.isnull().sum().sum())

    st.subheader("📁 Dataset Preview")
    st.dataframe(df.head(), use_container_width=True)

    # =========================
    # COLUMN TYPES
    # =========================
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    # =========================
    # SIDEBAR CONTROLS
    # =========================
    chart_type = st.sidebar.selectbox("Chart Type", CHART_TYPES)
    x_param = st.sidebar.selectbox("X-axis", df.columns)

    if chart_type != "Histogram":
        y_param = st.sidebar.selectbox("Y-axis", numeric_cols)
    else:
        y_param = None

    # =========================
    # FILTERS
    # =========================
    st.subheader("🔍 Filters")
    filtered_df = df.copy()
    filters = {}

    for col in categorical_cols:
        selected = st.multiselect(f"{col}", df[col].dropna().unique())
        if selected:
            filtered_df = filtered_df[filtered_df[col].isin(selected)]
            filters[col] = selected

    # =========================
    # VISUALIZATION
    # =========================
    st.subheader("📈 Visualization")

    fig = None

    if chart_type == "Bar":
        fig = px.bar(filtered_df, x=x_param, y=y_param)
    elif chart_type == "Line":
        fig = px.line(filtered_df, x=x_param, y=y_param)
    elif chart_type == "Scatter":
        fig = px.scatter(filtered_df, x=x_param, y=y_param)
    elif chart_type == "Pie":
        fig = px.pie(filtered_df, names=x_param, values=y_param)
    elif chart_type == "Histogram":
        fig = px.histogram(filtered_df, x=x_param)

    if fig:
        st.plotly_chart(fig, use_container_width=True)

    # =========================
    # 🔥 NEW: CORRELATION HEATMAP
    # =========================
    if len(numeric_cols) >= 2:
        st.subheader("📊 Correlation Heatmap")
        corr = filtered_df[numeric_cols].corr()

        heatmap = px.imshow(
            corr,
            text_auto=True,
            aspect="auto",
            title="Feature Correlation Matrix"
        )
        st.plotly_chart(heatmap, use_container_width=True)

    # =========================
    # EXPORT
    # =========================
    st.subheader("⬇️ Export Processed Data")

    csv_data = filtered_df.to_csv(index=False)

    excel_buffer = io.BytesIO()
    filtered_df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)

    col1, col2 = st.columns(2)

    col1.download_button(
        "Download CSV",
        csv_data,
        file_name="processed_data.csv",
        mime="text/csv"
    )

    col2.download_button(
        "Download Excel",
        excel_buffer,
        file_name="processed_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # =========================
    # SAVE CHART CONFIG
    # =========================
    if st.button("💾 Save Chart Configuration"):
        conn.execute(
            "INSERT INTO graphs (name, chart_type, x_param, y_param, filters) VALUES (?, ?, ?, ?, ?)",
            (
                f"{chart_type} | {x_param}",
                chart_type,
                x_param,
                y_param if y_param else "",
                json.dumps(filters)
            )
        )
        conn.commit()
        st.success("Saved!")

    # =========================
    # LOAD SAVED CHARTS
    # =========================
    st.subheader("🗂️ Saved Charts")

    graphs = conn.execute("SELECT * FROM graphs").fetchall()

    for g in graphs:
        graph_id, name, ctype, xval, yval, fjson = g

        c1, c2 = st.columns([4,1])

        c1.write(name)

        if c2.button("Load", key=graph_id):
            temp_df = df.copy()
            stored_filters = json.loads(fjson)

            for col, vals in stored_filters.items():
                temp_df = temp_df[temp_df[col].isin(vals)]

            if ctype == "Bar":
                fig = px.bar(temp_df, x=xval, y=yval)
            elif ctype == "Line":
                fig = px.line(temp_df, x=xval, y=yval)
            elif ctype == "Scatter":
                fig = px.scatter(temp_df, x=xval, y=yval)
            elif ctype == "Pie":
                fig = px.pie(temp_df, names=xval, values=yval)
            elif ctype == "Histogram":
                fig = px.histogram(temp_df, x=xval)

            st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Upload a dataset to begin.")

conn.close()
