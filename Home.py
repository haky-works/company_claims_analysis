import os

import pandas as pd # type: ignore
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
data = os.environ["DATA_PATH"]

@st.cache_data()
def get_claims():
    claims = pd.read_csv(data)
    return claims

claims = get_claims()

company_name = os.environ["COMPANY_NAME"]
claims['DateofAttendance'] = pd.to_datetime(claims['DateofAttendance'])
claims['Year'] = claims['DateofAttendance'].dt.year
claims['Month'] = claims['DateofAttendance'].dt.month
claims['Month Name'] = claims['DateofAttendance'].dt.month_name()
claims['Week'] = claims['DateofAttendance'].dt.isocalendar().week
grouped_claims_by_week = claims.groupby(by=['Year','Week']).agg(Claimed=('Claimed','sum')).reset_index()
grouped_claims_by_week['label'] = 'Week ' + grouped_claims_by_week['Week'].astype(str).str.zfill(2) + ' ' + grouped_claims_by_week['Year'].astype(str)
grouped_claims_by_month = claims.groupby(by=['Year', 'Month', 'Month Name']).agg(Claimed=('Claimed','sum')).reset_index()
grouped_claims_by_month['label'] = grouped_claims_by_month['Year'].astype(str) + ' ' + grouped_claims_by_month['Month'].astype(str).str.zfill(2)

groups = {
    'Day': {'data': claims, 'x': 'DateofAttendance', 'y': 'Claimed'},
    'Week': {'data': grouped_claims_by_week, 'x': 'label', 'y': 'Claimed'},
    'Month': {'data': grouped_claims_by_month, 'x': 'label', 'y': 'Claimed'},
}

st.write(list(groups.keys()))

st.header(f"Analysis of {company_name} Claims")

group = st.selectbox("Select a grouping", list(groups.keys()))

selected = groups[group]

if selected:
    st.line_chart(selected['data'], x=selected['x'], y=selected['y'])
