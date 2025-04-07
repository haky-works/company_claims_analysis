import os
import time

import pandas as pd  # type: ignore
import numpy as np  # type: ignore
import streamlit as st
import plotly.graph_objects as go  # type: ignore
from plotly.subplots import make_subplots  # type: ignore
import plotly.express as px  # type: ignore
from dotenv import load_dotenv
from typing import TypedDict
import src.conversions as conv

load_dotenv()
data = os.environ["DATA_PATH"]
member_data = os.environ["MEMBERSHIP_PATH"]
morbidity_data = os.environ["MORBIDITY_PATH"]
age_date = "2024-08-31"
company_name = os.environ["COMPANY_NAME"]


@st.cache_data()
def get_current_claims():
    all_data = pd.read_csv(data)
    all_data["BenefitOption"] = all_data["BenefitOption"].str.strip()
    all_data["DateofAttendance"] = pd.to_datetime(all_data["DateofAttendance"])
    all_data["AttendanceMonth"] = all_data["DateofAttendance"].dt.month
    claims = all_data[all_data["DateofAttendance"].between("2024-02-15", "2024-08-31")]
    claims["Claimed"] = claims["Claimed"].where(
        ~claims["ServiceProvider"].eq("INDIVIDUAL REFUNDS"), claims["Awarded"]
    )
    claims["ServiceType"] = claims["ServiceType"].where(
        ~claims["ServiceType"].isin(
            [
                "District / Primary Hospital",
                "Teaching / Tertiary Hospital",
                "Health Centre / Health Post",
                "CLINIC/HERBAL ",
            ]
        ),
        "Hospital/Clinic",
    )
    claims["ServiceType"] = claims["ServiceType"].where(
        ~claims["ServiceType"].eq("EYE CLINIC/HOSPITAL"), "Optical Centre"
    )
    return claims


@st.cache_data()
def get_current_membership():
    members = pd.read_csv(member_data)
    members["Benefit Option"] = members["Benefit Option"].str.strip()
    members["Benefit Option"] = members["Benefit Option"].astype("category")
    members["DOB"] = pd.to_datetime(members["DOB"])
    members["Start Date"] = pd.to_datetime(members["Start Date"])
    members["Expiry Date"] = pd.to_datetime(members["Expiry Date"])
    members_filtered = members[members["Start Date"].le(age_date)].copy()

    return members_filtered


@st.cache_data()
def get_classifications():
    classification = pd.read_parquet("parquet/classification.parquet")
    classification["Disease"] = classification["Disease"].str.upper()
    classification["Diagnosis"] = classification["Diagnosis"].str.upper()
    classification = classification.sort_values(by=["Disease", "Diagnosis"])
    classification = classification.drop_duplicates()
    classification = classification.drop_duplicates(subset="Disease", keep="first")

    return classification


@st.cache_data()
def get_morbidity_data():
    morbidity = pd.read_csv(morbidity_data)
    morbidity["DateofAttendance"] = pd.to_datetime(morbidity["DateofAttendance"])
    morbidity["Disease"] = morbidity["Disease"].str.upper()

    return morbidity


claims = get_current_claims()

membership = get_current_membership()

morbidity = get_morbidity_data()

classification = get_classifications()


class TimeFrame(TypedDict):
    data: pd.DataFrame  # assuming claims is a pandas DataFrame


time_frames: dict[str, TimeFrame] = {
    "2022": {
        "data": claims[
            claims["DateofAttendance"].between("2022-02-15", "2023-02-14")
        ].copy(),
    },
    "2023": {
        "data": claims[
            claims["DateofAttendance"].between("2023-02-15", "2024-02-14")
        ].copy(),
    },
    "2024": {
        "data": claims[
            claims["DateofAttendance"].between("2024-02-15", "2024-09-30")
        ].copy(),
    },
}

st.title(f"Analysis of {company_name} Claims")

st.dataframe(morbidity)

morbidity_with_diagnosis = morbidity.merge(classification, "left", "Disease")
st.dataframe(morbidity_with_diagnosis)
periods = [
    ("2022-02-15", "2022-09-30", "2022"),
    ("2023-02-15", "2023-09-30", "2023"),
    ("2024-02-15", "2024-09-30", "Current"),
]
total_morb_grouped = pd.DataFrame()
total_morb_grouped_all = pd.DataFrame()
for period in periods:
    morbidity_for_period = morbidity_with_diagnosis[
        morbidity_with_diagnosis["DateofAttendance"].between(period[0], period[1])
    ]
    morb_grouped = (
        morbidity_for_period.groupby(by=["Diagnosis", "BenefitOption"], observed=True)
        .agg(
            num_of_occurrences=("Total", "sum"),
            num_of_members=("MembershipNo", "nunique"),
        )
        .reset_index()
    )
    morb_grouped_all = (
        morbidity_for_period.groupby(
            by=[
                "Diagnosis",
            ],
            observed=True,
        )
        .agg(
            num_of_occurrences=("Total", "sum"),
            num_of_members=("MembershipNo", "nunique"),
        )
        .reset_index()
    )
    morb_grouped["Period"] = period[2]
    morb_grouped = morb_grouped.sort_values(by="num_of_occurrences", ascending=False)
    morb_grouped_top = morb_grouped.head(15)
    total_morb_grouped = pd.concat([total_morb_grouped, morb_grouped_top])
    morb_grouped_all["Period"] = period[2]
    morb_grouped_all = morb_grouped_all.sort_values(
        by="num_of_occurrences", ascending=False
    )
    total_morb_grouped_all = pd.concat([total_morb_grouped_all, morb_grouped_all])

total_morb_grouped["occurrences_per_beneficiary"] = (
    total_morb_grouped["num_of_occurrences"] / total_morb_grouped["num_of_members"]
)

morb_pivot = total_morb_grouped.pivot_table(
    "occurrences_per_beneficiary", ["Diagnosis", "BenefitOption"], "Period"
)
st.dataframe(total_morb_grouped)
st.dataframe(morb_pivot)
st.dataframe(total_morb_grouped[total_morb_grouped["Period"].eq("Current")])
st.dataframe(
    total_morb_grouped_all[total_morb_grouped_all["Period"].eq("Current")].head()
)

top_morbs = total_morb_grouped_all[total_morb_grouped_all["Period"].eq("Current")].head(
    10
)

cost_graph = px.bar(
    top_morbs,
    x="Diagnosis",
    y="num_of_occurrences",
    title="Number of occurances of top diagnosis",
    text=[f"{y:,.0f}" for y in top_morbs["num_of_occurrences"]],
    color_discrete_sequence=["#0d502f"],
)

chronic_conditions = ["HYPERTENSION", "DIABETES"]
chronic_morb = total_morb_grouped_all[
    total_morb_grouped_all["Diagnosis"].isin(chronic_conditions)
].copy()

chronic_morb["occurrences_per_beneficiary"] = (
    chronic_morb["num_of_occurrences"] / chronic_morb["num_of_members"]
)

# chronic_morb = (
#     chronic_morb.groupby(["Diagnosis", "Period"])
#     .agg(num_of_occurrences=("num_of_occurrences", "sum"))
#     .reset_index()
# )

chronic_morb["Period"] = chronic_morb["Period"].where(
    chronic_morb["Period"].ne("Current"), 2024
)

st.plotly_chart(cost_graph)
st.write(chronic_morb)

occurrence_graph = px.line(
    chronic_morb,
    x="Period",
    y="occurrences_per_beneficiary",
    color="Diagnosis",
    title="Number of occurrences per beneficiary for chronic conditions over the years",
    text=[f"{y:,.0f}" for y in chronic_morb["occurrences_per_beneficiary"]],
    # color_discrete_sequence=["#0d502f"],
)

st.plotly_chart(occurrence_graph)
