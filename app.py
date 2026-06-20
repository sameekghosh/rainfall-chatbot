import streamlit as st
import pandas as pd
import zipfile
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
lat_col = find_column(["latitude", "lat"])
lon_col = find_column(["longitude", "lon", "long"])

def answer_question(q):
    q_lower = q.lower()

    if rain_col is None:
        return "I could not identify the rainfall column automatically.", None

    # Dataset columns
    if "columns" in q_lower:
        return f"The dataset columns are: {', '.join(df.columns)}", None

    # Count observations
    if "how many" in q_lower or "number of observations" in q_lower or "count" in q_lower:
        return f"The dataset contains {len(df):,} valid observations.", None

    # Mean ± 1 SD rainfall rule
    if (
        "standard deviation" in q_lower
        or "sd" in q_lower
        or "1 sd" in q_lower
        or "one sd" in q_lower
        or "mean plus minus" in q_lower
        or "+- 1" in q_lower
        or "±" in q_lower
    ):
        if lat_col is None or lon_col is None:
            return (
                "The dataset must contain latitude and longitude columns to answer this question. "
                f"Detected latitude column: {lat_col}, longitude column: {lon_col}",
                None
            )

        mean_rain = df[rain_col].mean()
        sd_rain = df[rain_col].std()

        lower_limit = mean_rain - sd_rain
        upper_limit = mean_rain + sd_rain

        result = df[
            (df[rain_col] >= lower_limit) &
            (df[rain_col] <= upper_limit)
        ].copy()

        output_cols = [lat_col, lon_col, rain_col]

        for extra_col in [state_col, district_col, year_col, month_col]:
            if extra_col and extra_col not in output_cols:
                output_cols.append(extra_col)

        result = result[output_cols]

        message = (
            f"Mean rainfall = {mean_rain:.2f}\n\n"
            f"Standard deviation = {sd_rain:.2f}\n\n"
            f"Rainfall range within ±1 SD = {lower_limit:.2f} to {upper_limit:.2f}\n\n"
            f"Number of matching locations/observations = {len(result):,}\n\n"
            "The matching latitude and longitude records are shown below."
        )

        return message, result

    # Highest rainfall
    if "highest" in q_lower or "maximum" in q_lower or "max" in q_lower:
        row = df.loc[df[rain_col].idxmax()]
        return f"The highest recorded rainfall is {row[rain_col]}.\n\nFull row:\n{row.to_dict()}", None

    # Lowest rainfall
    if "lowest" in q_lower or "minimum" in q_lower or "min" in q_lower:
        row = df.loc[df[rain_col].idxmin()]
        return f"The lowest recorded rainfall is {row[rain_col]}.\n\nFull row:\n{row.to_dict()}", None

    # Average rainfall
    if "average" in q_lower or "mean" in q_lower:
        filtered = df.copy()

        for col in [state_col, district_col]:
            if col:
                values = df[col].dropna().astype(str).unique()
                for v in values:
                    if str(v).lower() in q_lower:
                        filtered = filtered[filtered[col].astype(str).str.lower() == str(v).lower()]
                        break

        avg = filtered[rain_col].mean()
        return f"The average rainfall for the matching records is {avg:.2f}.", None

    # Total rainfall
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
        return f"The total rainfall for the matching records is {total:.2f}.", None

    return (
        "I can answer only questions based on the RF25 rainfall dataset. "
        "Try asking about average rainfall, highest rainfall, lowest rainfall, total rainfall, "
        "or locations within mean ± 1 standard deviation.",
        None
    )

st.subheader("Ask a question")

question = st.chat_input("Ask something about the rainfall dataset...")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_table" not in st.session_state:
    st.session_state.last_table = None

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if question:
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user"):
        st.write(question)

    response, table = answer_question(question)

    st.session_state.messages.append({"role": "assistant", "content": response})

    with st.chat_message("assistant"):
        st.write(response)
        if table is not None:
            st.dataframe(table)

            csv = table.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download matching latitude-longitude list as CSV",
                data=csv,
                file_name="rainfall_within_mean_plus_minus_1sd.csv",
                mime="text/csv"
            )

st.divider()

st.subheader("Quick dataset explorer")

if rain_col:
    st.write(f"Detected rainfall column: `{rain_col}`")

if lat_col:
    st.write(f"Detected latitude column: `{lat_col}`")

if lon_col:
    st.write(f"Detected longitude column: `{lon_col}`")

if state_col:
    selected_state = st.selectbox(
        "Select state",
        ["All"] + sorted(df[state_col].dropna().astype(str).unique().tolist())
    )

    temp = df.copy()

    if selected_state != "All":
        temp = temp[temp[state_col].astype(str) == selected_state]

    st.metric("Number of observations", len(temp))
    st.metric("Average rainfall", round(temp[rain_col].mean(), 2))
    st.metric("Standard deviation", round(temp[rain_col].std(), 2))
    st.metric("Maximum rainfall", round(temp[rain_col].max(), 2))

    if month_col:
        monthly = temp.groupby(month_col)[rain_col].mean().reset_index()

        fig, ax = plt.subplots()
        ax.plot(monthly[month_col], monthly[rain_col], marker="o")
        ax.set_xlabel("Month")
        ax.set_ylabel("Average rainfall")
        ax.set_title("Average monthly rainfall")
        st.pyplot(fig)
