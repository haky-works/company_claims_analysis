import os

import pandas as pd # type: ignore
import numpy as np # type: ignore
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

time_frames = {
    '2022': {
        'data': claims[claims['DateofAttendance'].between('2022-02-15', '2023-02-14')].copy(),
    },
    '2023': {
        'data': claims[claims['DateofAttendance'].between('2023-02-15', '2024-02-14')].copy(),
    },
    '2024': {
        'data': claims[claims['DateofAttendance'].between('2024-02-15', '2025-02-14')].copy(),
    }
}

st.title(f"Analysis of {company_name} Claims")

company_info = st.expander('Basic Company Info')
with company_info:
    st.write('Total: 2452')
    st.write('Principals: 751')
    st.write('Dependents: 1701')

    st.write('Company Start Date: 15 Feb 2024')
    st.write('Company End Date: 14 Feb 2025')

st.header("Analyzing cost drivers")

claim_period = st.selectbox('Select the claim period', list(time_frames.keys()))

if claim_period:
    data = time_frames[claim_period]['data']
    total_cost = data['Claimed'].sum() # type: ignore
    grouped_data = data.groupby(by=['ClaimsNo', 'MembershipNo', 'DateofAttendance', 'ServiceProvider', 'ServiceType', 'Inout']).agg(cost=('Claimed','sum')).reset_index() # type: ignore
    grouped_data_specific = grouped_data[~grouped_data['ServiceType'].isin(["Universal Service", "Diagnostic Center", "Pharmacy"])].copy()
    total_attendance = grouped_data_specific['ClaimsNo'].nunique()
    facilities = grouped_data.groupby(by=['ServiceProvider']).agg(cost=('cost','sum'), count=('ClaimsNo','nunique'), members=('MembershipNo','nunique')).reset_index()
    facilities['Cost per visit'] = facilities['cost'] / facilities['count']
    facilities['Cost per person'] = facilities['cost'] / facilities['members']
    facilities = facilities.sort_values(by=['cost'], ascending=False).reset_index(drop=True)
    top_services = facilities.head(10)
    cost_per_service = data.groupby(by=['TypeName']).agg(cost=('Claimed','sum')).reset_index() # type: ignore
    cost_per_service = cost_per_service.sort_values(by=['cost'], ascending=False).reset_index(drop=True)

    top_5_services = cost_per_service.head(5)
    claims_of_top_5_services = data[np.logical_and(data['TypeName'].isin(top_5_services['TypeName']), data['ServiceProvider'].isin(facilities['ServiceProvider']))].copy() # type: ignore
    summarized_top_5_services_per_facility = claims_of_top_5_services.groupby(by=['ServiceProvider', 'TypeName']).agg(cost=('Claimed','sum'),  count=('ClaimsNo','nunique'), members=('MembershipNo','nunique')).reset_index()
    # top_5_services['Cost per visit'] = top_5_services['cost'] / top_5_services['TypeName'].count()
    # top_5_services['Cost per person'] = top_5_services['cost'] / top_5_services['MembershipNo'].nunique()


st.markdown('### What is the average cost per person?')

if claim_period:
    average_cost_per_person = data['Claimed'].sum() / data['MembershipNo'].nunique() # type: ignore
    st.metric('Average cost per person:', "{:,.2f}".format(round(average_cost_per_person, 1)))


st.markdown('### What is the average cost per visit?')

if claim_period:
    average_cost_per_visit = total_cost / total_attendance # type: ignore
    st.metric('Average cost per visit:', "{:,.2f}".format(round(average_cost_per_visit, 1)))


st.markdown('### What are the top 10 services with the highest cost?')

if claim_period:
    st.dataframe(top_services)

st.header("Analyzing cost by Service Type")
st.markdown('### What are the top 10 facilities with the highest cost?')

if claim_period:
    st.dataframe(cost_per_service)
    st.dataframe(summarized_top_5_services_per_facility)

# if claim_period:



