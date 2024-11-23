import pandas as pd


def get_balance_over_time(df, account_name):
    df = pd.DataFrame(df)
    df = df[df["AccountName"] == account_name]
    df = df[["DateSeries", "Balance"]]
    return df
