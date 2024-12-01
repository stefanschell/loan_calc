import pandas as pd
from os import listdir
from os.path import isfile, join


def read_statement_from_file(df, file, account_name):
    df_in = pd.read_csv(file)

    df_in["File"] = file
    df_in["AccountName"] = account_name
    df_in["DateSeries"] = pd.to_datetime(df_in["Date"], dayfirst=True)

    if df is None:
        df = df_in
    else:
        df = pd.concat([df, df_in], ignore_index=True)

    return df


def read_account_from_folder(path_loans, account_name, df):
    path_account = join(path_loans, account_name)
    csvs_account = [
        join(path_account, f)
        for f in listdir(path_account)
        if isfile(join(path_account, f)) and ".csv" in f
    ]

    for csv in csvs_account:
        df = read_statement_from_file(df, csv, account_name)

    return df


def label_row(row):
    if row["AccountName"] == "Offset":
        if row["Debit"] < 0:
            return "OffsetDown"
        if row["Credit"] > 0:
            return "OffsetUp"
    if row["Debit"] < 0:
        if "Interest" in row["Description"]:
            return "Interest"
        else:
            return "Redraw"
    if row["Credit"] > 0:
        if "Repayment" in row["Description"]:
            return "Repayment"
        if row["Credit"] > 0:
            return "Extrarepayment"
    else:
        return "Unknown"


def read_accounts_from_folders(date_from=None, date_to=None):
    path_loans = "Loans"

    df = None
    df = read_account_from_folder(path_loans, "Fixed", df)
    df = read_account_from_folder(path_loans, "Variable", df)
    df = read_account_from_folder(path_loans, "Offset", df)

    df.drop_duplicates(
        inplace=True, subset=["Date", "Description", "Credit", "Debit", "Balance"]
    )

    if date_from:
        df = df[df["DateSeries"] >= date_from]
    if date_to:
        df = df[df["DateSeries"] <= date_to]

    df = df.iloc[::-1]  # invert order
    df.sort_values(by="DateSeries", inplace=True, kind="stable", ascending=True)  # sort
    df["OriginalIndex"] = df.index
    df.reset_index(inplace=True, drop=True)

    df["Label"] = df.apply(label_row, axis=1)

    return df


def get_dataframe(date_from=None, date_to=None):
    df = read_accounts_from_folders(date_from, date_to)
    return df
