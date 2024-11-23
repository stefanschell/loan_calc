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


def find_balance(df, date):
    previous = df[df["DateSeries"] <= date]["Balance"]
    if len(previous) > 0:
        return previous.iloc[-1]
    return 0


def get_total_balance_over_time(
    df,
    selected_dates=None,
    add_col_with_account_name=False,
    return_positive_balance=False,
):
    df = pd.DataFrame(df)

    df_fixed = get_balance_over_time(df, "Fixed")
    df_variable = get_balance_over_time(df, "Variable")
    df_offset = get_balance_over_time(df, "Offset")

    if not selected_dates:
        dates = (
            pd.concat([df_fixed, df_variable, df_offset])["DateSeries"]
            .drop_duplicates()
            .sort_values(ascending=True)
            .to_list()
        )
    else:
        dates = selected_dates

    balances = []
    for date in dates:
        balances.append(
            find_balance(df_fixed, date)
            + find_balance(df_variable, date)
            + find_balance(df_offset, date)
        )

    df = pd.DataFrame({"DateSeries": dates, "Balance": balances})

    if add_col_with_account_name:
        df["Account"] = "Total"
    if return_positive_balance:
        df["Balance"] = abs(df["Balance"])

    return df
