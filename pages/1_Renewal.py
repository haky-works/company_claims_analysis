import os
import time

import pandas as pd # type: ignore
import numpy as np # type: ignore
import streamlit as st
import plotly.graph_objects as go # type: ignore
from plotly.subplots import make_subplots # type: ignore
import plotly.express as px # type: ignore
from dotenv import load_dotenv
import altair as alt
import src.conversions as conv

load_dotenv()
data = os.environ["DATA_PATH"]
member_data = os.environ["MEMBERSHIP_PATH"]
age_date = '2024-08-31'
company_name = os.environ["COMPANY_NAME"]

@st.cache_data()
def get_current_claims():
    all_data = pd.read_csv(data)
    claims = all_data[all_data['DateofAttendance'].between('2024-02-15', '2024-08-31')]
    claims['Claimed'] = claims['Claimed'].where(~claims['ServiceProvider'].eq('INDIVIDUAL REFUNDS'), claims['Awarded'])
    claims['ServiceType'] = claims['ServiceType'].where(~claims['ServiceType'].isin(['District / Primary Hospital', 'Teaching / Tertiary Hospital', 'Health Centre / Health Post', 'CLINIC/HERBAL ']), 'Hospital/Clinic')
    claims['ServiceType'] = claims['ServiceType'].where(~claims['ServiceType'].eq('EYE CLINIC/HOSPITAL'), 'Optical Centre')
    return claims

@st.cache_data()
def get_current_membership():
    members = pd.read_csv(member_data)
    members['Benefit Option'] = members['Benefit Option'].astype('category')
    members['DOB'] = pd.to_datetime(members['DOB'])
    members['Start Date'] = pd.to_datetime(members['Start Date'])
    members['Expiry Date'] = pd.to_datetime(members['Expiry Date'])
    members_filtered = members[members['Start Date'].le(age_date)].copy()

    return members_filtered

claims = get_current_claims()

membership = get_current_membership()

st.title(f"Analysis of {company_name} Claims")

st.write(membership)

st.header('Distribution of Membership per plan')

st.write(membership.shape)

for plan in membership['Benefit Option'].unique():
    members_in_plan = membership[membership['Benefit Option'].eq(plan)].copy()
    # members_in_plan = members_in_plan[members_in_plan['Start D'].]
    member_ages = conv.change_date_to_age(
            members_in_plan, "DOB", "Age", age_date, date_format="mixed"
    )

    member_ages = conv.convert_age_to_age_band(
        member_ages, "Age", "AgeBand"
    )

    member_ages = conv.convert_relationship_to_member_type_using_age(
            member_ages, "Age", "MemberType"
    )

    member_summary = member_ages.groupby(by=['AgeBand', 'Gender'], observed=False).agg(num_members=('Membership No', 'nunique')).reset_index()
    member_bar = px.bar(member_summary, 'AgeBand', 'num_members', 'Gender', barmode='group')
    st.markdown(f'### Member distribution for {plan}')
    st.plotly_chart(member_bar)
    # st.write(member_ages)
    # st.write(member_summary)

