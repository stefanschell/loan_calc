import pandas as pd


def get_balance_over_time(
    df, account_name, add_col_with_account_name=False, return_positive_balance=False
):
    df = pd.DataFrame(df)

    df = df[df["AccountName"] == account_name]
    df = df[["DateSeries", "Balance"]]

    df = df.drop_duplicates(subset=["DateSeries"], keep="last")

    if add_col_with_account_name:
        df["Account"] = account_name
    if return_positive_balance:
        df["Balance"] = abs(df["Balance"])

    return df


def get_total_balance_over_time(df):
    df = pd.DataFrame(df)

    df_fixed = get_balance_over_time(df, "Fixed")
    df_variable = get_balance_over_time(df, "Variable")
    df_offset = get_balance_over_time(df, "Offset")
