import streamlit as st
import pandas as pd
import zipfile
import re
import matplotlib.pyplot as plt

st.set_page_config(page_title="RF25 Rainfall Dataset Chatbot", layout="wide")

ZIP_FILE = "RF25_ind2010_csv_and_visualizations.zip"
CSV_FILE = "RF25_ind2010_rainfall_valid_observations.csv"

@st.cache_data
def load_data():
    with zipfile.ZipFile(ZIP_FILE) as z:
        with z.open(CSV_FILE) as f:
            df = pd.read_csv(f)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df

df = load_data()

st.title("RF25 Rainfall Dataset Chatbot")
st.caption("This chatbot answers only from RF25_ind2010_rainfall_valid_observations.csv")

with st.expander("Dataset columns"):
    st.write(df.columns.tolist())
    st.dataframe(df.head())

def find_column(possible_names):
    for col in df.columns:
        for name in possible_names:
            if name in col:
                return col
    return None

state_col = find_column(["state"])
district_col = find_column(["district"])
year_col = find_column(["year"])
month_col = find_column(["month"])
rain_col = find_column(["rainfall", "rain", "precipitation"])

def answer_question(q):
    q_lower = q.lower()

    if rain_col is None:
        return "I could not identify the rainfall column automatically. Please check the dataset column names."

    # Basic dataset summary
    if "columns" in q_lower:
        return f"The dataset columns are: {', '.join(df.columns)}"

    if "how many" in q_lower or "number of observations" in q_lower or "count" in q_lower:
        return f"The dataset contains {len(df):,} valid observations."

    if "highest" in q_lower or "maximum" in q_lower or "max" in q_lower:
        row = df.loc[df[rain_col].idxmax()]
        return f"The highest recorded rainfall is {row[rain_col]}.\n\nFull row:\n{row.to_dict()}"

    if "lowest" in q_lower or "minimum" in q_lower or "min" in q_lower:
        row = df.loc[df[rain_col].idxmin()]
        return f"The lowest recorded rainfall is {row[rain_col]}.\n\nFull row:\n{row.to_dict()}"

    if "average" in q_lower or "mean" in q_lower:
        filtered = df.copy()

        # Try filtering by state/district names if present in question
        for col in [state_col, district_col]:
            if col:
                values = df[col].dropna().astype(str).unique()
                for v in values:
                    if str(v).lower() in q_lower:
                        filtered = filtered[filtered[col].astype(str).str.lower() == str(v).lower()]
                        break

        avg = filtered[rain_col].mean()
        return f"The average rainfall for the matching records is {avg:.2f}."

    if "total" in q_lower or "sum" in q_lower:
        filtered = df.copy()

        for col in [state_col, district_col]:
            if col:
                values = df[col].dropna().astype(str).unique()
                for v in values:
                    if str(v).lower() in q_lower:
                        filtered = filtered[filtered[col].astype(str).str.lower() == str(v).lower()]
                        break

        total = filtered[rain_col].sum()
        return f"The total rainfall for the matching records is {total:.2f}."

    return (
        "I can answer only questions based on the RF25 rainfall dataset. "
        "Try asking about average rainfall, highest rainfall, lowest rainfall, totals, counts, states, districts, years, or months."
    )

st.subheader("Ask a question")

question = st.chat_input("Ask something about the rainfall dataset...")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    response = answer_question(question)

    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.write(response)

st.divider()

st.subheader("Quick dataset explorer")

if rain_col:
    st.write(f"Detected rainfall column: `{rain_col}`")

    if state_col:
        selected_state = st.selectbox("Select state", ["All"] + sorted(df[state_col].dropna().astype(str).unique().tolist()))
        temp = df.copy()
        if selected_state != "All":
            temp = temp[temp[state_col].astype(str) == selected_state]

        st.metric("Number of observations", len(temp))
        st.metric("Average rainfall", round(temp[rain_col].mean(), 2))
        st.metric("Maximum rainfall", round(temp[rain_col].max(), 2))

        if month_col:
            monthly = temp.groupby(month_col)[rain_col].mean().reset_index()
            fig, ax = plt.subplots()
            ax.plot(monthly[month_col], monthly[rain_col], marker="o")
            ax.set_xlabel("Month")
            ax.set_ylabel("Average rainfall")
            ax.set_title("Average monthly rainfall")
            st.pyplot(fig)