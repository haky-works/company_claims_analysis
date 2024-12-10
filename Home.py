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

load_dotenv()
data = os.environ["DATA_PATH"]

@st.cache_data()
def get_claims():
    claims = pd.read_csv(data)
    claims['Claimed'] = claims['Claimed'].where(~claims['ServiceProvider'].eq('INDIVIDUAL REFUNDS'), claims['Awarded'])
    claims['ServiceType'] = claims['ServiceType'].where(~claims['ServiceType'].isin(['District / Primary Hospital', 'Teaching / Tertiary Hospital', 'Health Centre / Health Post', 'CLINIC/HERBAL ']), 'Hospital/Clinic')
    claims['ServiceType'] = claims['ServiceType'].where(~claims['ServiceType'].eq('EYE CLINIC/HOSPITAL'), 'Optical Centre')

    return claims

claims = get_claims()

company_name = os.environ["COMPANY_NAME"]
claims['DateofAttendance'] = pd.to_datetime(claims['DateofAttendance'])
claims = claims.sort_values(by=['DateofAttendance'])
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
        'data': claims[claims['DateofAttendance'].between('2024-02-15', '2024-08-31')].copy(),
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

with st.sidebar:
    claim_period = st.selectbox('Select the claim period', list(time_frames.keys()))

if claim_period:
    data = time_frames[claim_period]['data']

    data['Types'] = data['TypeName'] # type: ignore

    data["Types"] = data["Types"].replace({"Administrative Services": "Admin", "Diagnostic Investigations": "Diagnostic", "Drugs": "Drugs", "Specialist Consultation Services": "SP", "ENT": "SP", "Paediatrician": "SP", "Physiotherapy": "SP", "General Consultation Services": "GP", "Hospital Accommodation Services": "Accommodation", "In-Patient Service": "In-Patient Services", "Out Patient Procedures": "Out-Patient Procedures", "Maternity Care Services": "Maternity", "Surgical Procedures": "Surgery", "Surgical/ Medical Materials": "Surgery", "Dental Services": "Dental", "Optical Services": "Optical",}) # type: ignore

    data['Types'] = data['Types'].where(~np.logical_and(data['Types'].eq('Others'), data['Inout'].eq('In')), 'In-Patient Services') # type: ignore
    data['Types'] = data['Types'].where(~np.logical_and(data['Types'].eq('Others'), data['Inout'].eq('Out')), 'Out-Patient Procedures') # type: ignore

    facility_types = data['ServiceType'].unique() # type: ignore
    facility_types = data.groupby(by='ServiceType')['Claimed'].sum().reset_index() # type: ignore
    facility_types['percent_value'] = (facility_types['Claimed'] / facility_types['Claimed'].sum()) * 100
    facility_types['Percentage'] = facility_types['percent_value'].round(2).astype(str) + '%'
    facility_types = facility_types.sort_values(by=['Claimed'], ascending=False).reset_index(drop=True)

    total_cost = data['Claimed'].sum() # type: ignore

    grouped_data = data.groupby(by=['ClaimsNo', 'MembershipNo', 'DateofAttendance', 'ServiceProvider', 'ServiceType', 'Inout']).agg(cost=('Claimed','sum')).reset_index() # type: ignore

    grouped_data_specific = grouped_data[~grouped_data['ServiceType'].isin(["Universal Service", "Diagnostic Center", "Pharmacy"])].copy()
    total_attendance = grouped_data_specific['ClaimsNo'].nunique()

    facilities = grouped_data.groupby(by=['ServiceProvider']).agg(cost=('cost','sum'), count=('ClaimsNo','nunique'), members=('MembershipNo','nunique')).reset_index()
    facilities['Cost per visit'] = facilities['cost'] / facilities['count']
    facilities['Cost per person'] = facilities['cost'] / facilities['members']
    facilities = facilities.sort_values(by=['cost'], ascending=False).reset_index(drop=True)
    facilities = facilities.reset_index()
    facilities = facilities.rename(columns={'index': 'rank'})
    top_5_facilities = facilities.head(6)

    cost_per_service = data.groupby(by=['TypeName']).agg(cost=('Claimed','sum')).reset_index() # type: ignore
    cost_per_service = cost_per_service.sort_values(by=['cost'], ascending=False).reset_index(drop=True)
    cost_per_service['percent_weight'] = cost_per_service['cost'] / cost_per_service['cost'].sum()
    cost_per_service['percent_value'] = cost_per_service['percent_weight']
    cost_per_service['Percentage'] = cost_per_service['percent_value'].round(2).astype(str) + '%'
    top_5_services = cost_per_service.head(5)

    claims_of_top_5_services = data[np.logical_and(data['TypeName'].isin(top_5_services['TypeName']), data['ServiceProvider'].isin(facilities['ServiceProvider']))].copy() # type: ignore
    summarized_top_5_services_per_facility = claims_of_top_5_services.groupby(by=['ServiceProvider', 'ServiceType', 'TypeName']).agg(cost=('Claimed','sum'),  count=('TypeName','count'), members=('MembershipNo','nunique'), average=('Claimed','mean')).reset_index()
    top_5_service_with_top_5_facilities = summarized_top_5_services_per_facility[summarized_top_5_services_per_facility['ServiceProvider'].isin(top_5_facilities['ServiceProvider'])]
    top_5_service_with_top_5_facilities['Cost per visit'] = top_5_service_with_top_5_facilities['cost'] / top_5_service_with_top_5_facilities['count']

    top_3_facility_types = facility_types.head(3)
    claims_for_top_3_facility_types = data[data['ServiceType'].isin(top_3_facility_types['ServiceType'])].copy() # type: ignore
    summary_for_top_3_facility_types = claims_for_top_3_facility_types.groupby(by=['ServiceProvider', 'ServiceType']).agg(cost=('Claimed','sum')).reset_index()
    top_facilities_claims_with_top_service_types = pd.DataFrame()

    for facility_type in top_3_facility_types['ServiceType']:
        all_facilities_with_type = summary_for_top_3_facility_types[summary_for_top_3_facility_types['ServiceType'] == facility_type].copy()
        top_facilities_with_type = all_facilities_with_type.sort_values(by=['cost'], ascending=False).reset_index(drop=True).head(5)
        claims_of_top_5_services_from_top_facilities = data[np.logical_and(data['TypeName'].isin(top_5_services['TypeName']), data['ServiceProvider'].isin(top_facilities_with_type['ServiceProvider']))].copy() # type: ignore
        summarized_top_5_services_per_top_facility = claims_of_top_5_services_from_top_facilities.groupby(by=['ServiceProvider', 'ServiceType', 'TypeName']).agg(cost=('Claimed','sum'),  count=('TypeName','count'), members=('MembershipNo','nunique'), average=('Claimed','mean')).reset_index()
        top_facilities_claims_with_top_service_types = pd.concat([top_facilities_claims_with_top_service_types, summarized_top_5_services_per_top_facility], ignore_index=True)

    top_facilities_claims_with_top_service_types = pd.merge(top_facilities_claims_with_top_service_types, top_5_services[['TypeName', 'percent_weight']], how='left', on='TypeName')
    top_facilities_claims_with_top_service_types['weighted_average'] = top_facilities_claims_with_top_service_types['average'] * top_facilities_claims_with_top_service_types['percent_weight']
    # st.write(top_5_services)
    # st.write(top_facilities_claims_with_top_service_types)

    cost_per_type = data.groupby(by=['Types']).agg(cost=('Claimed','sum')).reset_index() # type: ignore

st.markdown('### What is the average cost per visit?')

if claim_period:
    average_cost_per_visit = total_cost / total_attendance # type: ignore
    st.metric('Average cost per visit:', "{:,.2f}".format(round(average_cost_per_visit, 1)))


st.markdown('### What are the percentage cost associated with each Facility Type and each Service type?')

col1, col2 = st.columns(2)

if claim_period:
    fig1 = px.pie(facility_types, values='Claimed', names='ServiceType', hole=0.6)
    fig1.update_traces(rotation=-40,title="Proportion of Facility Types")

    fig2 = px.pie(cost_per_type, values='cost', names='Types', hole=0.6)
    fig2.update_traces(title="Proportion of Service Types")

    col1.plotly_chart(fig1, use_container_width=True)
    col2.plotly_chart(fig2, use_container_width=True)

st.header("Analyzing cost by Facility Type")
# st.markdown('### What are the top 10 facilities with the highest cost?')

# if claim_period:
#     st.dataframe(top_5_services)
#     # st.dataframe(cost_per_service)
#     st.dataframe(top_5_service_with_top_5_facilities)

# for index, service in top_5_services.iterrows():
#     # st.header(f"Analyzing cost by {group}")
#     st.dataframe(service)
#     service_data = top_5_service_with_top_5_facilities[top_5_service_with_top_5_facilities['TypeName'] == service['TypeName']]
#     bars = (
#         alt.Chart(service_data)
#         .mark_bar()
#         .encode(
#             x="ServiceProvider",
#             y="Cost per visit",
#         )
#         .properties(
#             width=550,
#         )
#     )
#     st.altair_chart(bars, theme="streamlit", use_container_width=True)

fig = go.Figure()

for facility_type in top_3_facility_types['ServiceType']:
    top = top_facilities_claims_with_top_service_types[top_facilities_claims_with_top_service_types['ServiceType'] == facility_type].copy()
    top_grouped = top.groupby(by=['ServiceProvider']).agg(cost=('cost','sum')).reset_index()
    top_grouped = top_grouped.sort_values(by=['cost'], ascending=False).reset_index(drop=True)

    radar_chart = go.Figure()
    st.markdown(f"#### Analyzing cost by {facility_type}")
    facility_expander = st.expander(f'What are the top {facility_type} with the highest cost?', expanded=True)
    service_cost_expander = st.expander(f'What are the top {facility_type} with the highest cost per visit?')
    cost_graph = px.bar(top_grouped, x="ServiceProvider", y="cost")
    number_check = (top['ServiceType'].count() /top['ServiceType'].nunique())/ top['ServiceProvider'].nunique()
    # st.write(top)
    # st.write(top_grouped.reset_index())
    facility_expander.plotly_chart(cost_graph)
    with st.expander(f'Comparison of weighted averages for top {facility_type} based on Service Type'):
        if number_check > 4:
            for provider in top_grouped['ServiceProvider'].unique():
                service_data = top[top['ServiceProvider'] == provider]
                radar_chart.add_trace(go.Scatterpolar(
                    r=service_data['weighted_average'],
                    theta=service_data['TypeName'],
                    fill='toself',
                    name=provider,
                ))
                radar_chart.update_layout(template='plotly_dark')

            st.plotly_chart(radar_chart)
        else:
            top_facility_type = facility_types.head(1)['ServiceType'].values[0]
            final = top.copy()
            if facility_type != top_facility_type:
                with st.popover("Chart Controls"):
                    chart = st.toggle(f"Include {top_facility_type} facilities", key='toggle{}'.format(facility_type))

                if chart:
                    service_types_in_current_facility_type = top['TypeName'].unique()
                    top_facility_type = top_facilities_claims_with_top_service_types[top_facilities_claims_with_top_service_types['ServiceType'] == top_facility_type].copy()
                    top_facility_type_with_current_service = top_facility_type[top_facility_type['TypeName'].isin(service_types_in_current_facility_type)]

                    final = pd.concat([final, top_facility_type_with_current_service])
                    final = final.reset_index(drop=True)

            final = pd.merge(final, facilities[['ServiceProvider', 'rank']], how='left', on='ServiceProvider')
            final = final.sort_values(by=['rank'], ascending=True).reset_index(drop=True)
            # service_facility_graph = px.bar(final, x="ServiceProvider", y="weighted_average", color="TypeName", barmode="group",  facet_col="ServiceType")
            # st.plotly_chart(service_facility_graph)

            service_facility_graph = make_subplots(rows=1, cols=1, subplot_titles=["Service Facility Graph"])

            for service_type in final['ServiceType'].unique():
                service_type_df = final[final['ServiceType'] == service_type]
                for type_name in service_type_df['TypeName'].unique():
                    type_name_df = service_type_df[service_type_df['TypeName'] == type_name]
                    service_facility_graph.add_trace(
                        go.Bar(x=type_name_df['ServiceProvider'], y=type_name_df['weighted_average'], name=type_name),
                        row=1, col=1
                    )

            service_facility_graph.update_layout(barmode='group')
            st.plotly_chart(service_facility_graph)
