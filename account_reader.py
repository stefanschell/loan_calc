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
        return "Offset"
    if "Repayment" in row["Description"]:
        return "Repayment"
    if "Interest" in row["Description"]:
        return "Interest"
    return "Other"


def read_accounts_from_folders():
    path_loans = "Loans"

    df = None
    df = read_account_from_folder(path_loans, "Fixed", df)
    df = read_account_from_folder(path_loans, "Variable", df)
    df = read_account_from_folder(path_loans, "Offset", df)

    df.drop_duplicates(inplace=True)

    df["Label"] = df.apply(label_row, axis=1)

    return df


def get_dataframe():
    df = read_accounts_from_folders()
    return df
