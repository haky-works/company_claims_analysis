import pandas as pd # type: ignore
import numpy as np # type: ignore

def change_date_to_age(
    df, date_column_name, age_column_name, end_date, date_format="%Y-%m-%d"
):
    df = df.copy()

    df[age_column_name] = pd.to_datetime(df[date_column_name], format=date_format)

    # today = datetime.now()
    end_date = pd.to_datetime(end_date, format=date_format)

    df[age_column_name] = (
        df[age_column_name]
        .dt.year.rsub(end_date.year, fill_value=0)
        .where(
            (
                np.logical_or(
                    end_date.month > df[age_column_name].dt.month,
                    np.logical_and(
                        end_date.month == df[age_column_name].dt.month,
                        end_date.day >= df[age_column_name].dt.day,
                    ),
                )
            ),
            end_date.year - 1 - df[age_column_name].dt.year,
        )
    )

    return df


def convert_age_to_age_band(df, age_column_name, ageband_column_name):
    df = df.copy()

    ordered_age_bands = [
        "0-4",
        "5-9",
        "10-14",
        "15-18",
        "19-24",
        "25-30",
        "31-40",
        "41-50",
        "51-60",
        "61-Above",
    ]

    df[ageband_column_name] = pd.cut(
        df[age_column_name],
        bins=[0, 4, 9, 14, 18, 24, 30, 40, 50, 60, 200],
        labels=ordered_age_bands,
    )

    df[ageband_column_name] = df[ageband_column_name].where(
        df[age_column_name].ne(0), "0-4"
    )

    df[ageband_column_name] = pd.Categorical(
        df[ageband_column_name], ordered=True, categories=ordered_age_bands
    )

    return df

def convert_relationship_to_member_type_using_age(
    df,
    age_column_name,
    member_type_column_name,
    relationship_column_name="Relationship",
):
    df = df.copy()
    df[relationship_column_name] = df[relationship_column_name].str.upper()
    df[member_type_column_name] = (
        df[relationship_column_name]
        .where(df[age_column_name].lt(18), "Adult Dependent")
        .where(df[age_column_name].ge(18), "Child Dependent")
        .where(df[relationship_column_name].ne("SELF"), "Principal")
        .where(df[age_column_name].lt(60), "Overage")
    )
    return df