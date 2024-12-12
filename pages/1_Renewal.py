import os
import time

import pandas as pd  # type: ignore
import numpy as np  # type: ignore
import streamlit as st
import plotly.graph_objects as go  # type: ignore
from plotly.subplots import make_subplots  # type: ignore
import plotly.express as px  # type: ignore
from dotenv import load_dotenv
import src.conversions as conv

load_dotenv()
data = os.environ["DATA_PATH"]
member_data = os.environ["MEMBERSHIP_PATH"]
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


claims = get_current_claims()

membership = get_current_membership()

st.title(f"Analysis of {company_name} Claims")

st.write(membership)

st.header("Distribution of Membership per plan")

st.write(membership.shape)

month_number = {"first_day": [], "size": [], "plan": []}  # type: ignore
for plan in membership["Benefit Option"].unique():
    members_in_plan = membership[membership["Benefit Option"].eq(plan)].copy()
    # members_in_plan = members_in_plan[members_in_plan['Start D'].]
    member_ages = conv.change_date_to_age(
        members_in_plan, "DOB", "Age", age_date, date_format="mixed"
    )

    member_ages = conv.convert_age_to_age_band(member_ages, "Age", "AgeBand")

    member_ages = conv.convert_relationship_to_member_type_using_age(
        member_ages, "Age", "MemberType"
    )

    member_summary = (
        member_ages.groupby(by=["AgeBand", "Gender"], observed=False)
        .agg(num_members=("Membership No", "nunique"))
        .reset_index()
    )

    start_date = "2024-02-01"
    end_date = "2024-08-31"
    months = pd.DataFrame()
    months["month"] = (
        pd.date_range(start=start_date, end=end_date, freq="MS", inclusive="both")
        .strftime("%Y-%m")
        .tolist()
    )
    months["first_day"] = pd.to_datetime(months["month"], format="%Y-%m")
    member_ages["start_month"] = (
        member_ages["Start Date"].to_numpy().astype("datetime64[M]")
    )
    member_ages["expiry_month"] = (
        member_ages["Expiry Date"].to_numpy().astype("datetime64[M]")
    )
    member_bar = px.bar(
        member_summary, "AgeBand", "num_members", "Gender", barmode="group"
    )
    st.markdown(f"### Member distribution for {plan}")
    st.plotly_chart(member_bar)
    # st.write(member_ages)
    for month in months["first_day"].unique():
        size = member_ages[
            np.logical_and(
                member_ages["start_month"].le(month),
                member_ages["expiry_month"].ge(month),
            )
        ]["Membership No"].nunique()
        month_number["first_day"].append(month)
        month_number["size"].append(size)
        month_number["plan"].append(plan)

member_size_breakdown = pd.DataFrame(month_number)
member_size_breakdown["month_number"] = member_size_breakdown["first_day"].dt.month
member_size_breakdown["month_name"] = member_size_breakdown["first_day"].dt.strftime(
    "%B"
)
# st.write(member_size_breakdown)

# st.write(claims.head())
# st.write(claims["BenefitOption"].unique())
claims_breakdown = (
    claims.groupby(by=["BenefitOption", "AttendanceMonth"])
    .agg(
        cost=("Claimed", "sum"),
        number_of_claims=("ClaimsNo", "nunique"),
        number_of_members_accessed=("MembershipNo", "nunique"),
    )
    .reset_index()
)
claims_breakdown = claims_breakdown.rename(
    columns={"AttendanceMonth": "month_number", "BenefitOption": "plan"}
)
claims_breakdown_with_members = pd.merge(
    claims_breakdown, member_size_breakdown, "left", on=["month_number", "plan"]
)

claims_breakdown_with_members["average_cost_per_person"] = (
    claims_breakdown_with_members["cost"] / claims_breakdown_with_members["size"]
)
# st.write(
#     claims_breakdown_with_members[
#         ["plan", "month_name", "cost", "size", "average_cost_per_person"]
#     ]
# )

date1 = "2024-02-15"
date2 = "2024-08-31"
date3 = "2025-02-14"
# Convert the strings to datetime objects
date1 = pd.to_datetime(date1)
date2 = pd.to_datetime(date2)
date3 = pd.to_datetime(date3)
# Calculate the difference in days
difference = (date2 - date1).days  # type: ignore
diff_full = (date3 - date1).days  # type: ignore

# st.write(diff_full, difference)
claims_per_plan = (
    claims_breakdown_with_members.groupby("plan")
    .agg(cost=("cost", "sum"))
    .reset_index()
)
claims_per_plan["projected"] = claims_per_plan["cost"] * diff_full / difference
claims_per_plan["difference"] = claims_per_plan["projected"] - claims_per_plan["cost"]

# max_numbers = df.groupby("label")["number"].max().reset_index()
max_numbers = (
    claims_breakdown_with_members.groupby("plan")["month_number"].max().reset_index()
)

max_numbers = max_numbers.merge(
    claims_breakdown_with_members[["plan", "month_number", "size"]],
    "left",
    ["plan", "month_number"],
)

claims_for_now = (
    claims_breakdown_with_members.groupby("plan")
    .agg(average_cost_for_now=("average_cost_per_person", "sum"))
    .reset_index()
)

claims_per_plan = claims_per_plan.merge(max_numbers[["plan", "size"]], "left", "plan")
claims_per_plan = claims_per_plan.merge(claims_for_now, "left", "plan")
claims_per_plan["average_cost_for_rest_of_year"] = (
    claims_per_plan["difference"] / claims_per_plan["size"]
)
claims_per_plan["cost_for_year_per_person"] = (
    claims_per_plan["average_cost_for_rest_of_year"]
    + claims_per_plan["average_cost_for_now"]
)

st.write(claims_per_plan[["plan", "cost", "cost_for_year_per_person"]])
