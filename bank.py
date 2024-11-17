import pandas as pd
from os import listdir
from os.path import isfile, join


def read_from_file(df, csv, loan):
    df_csv = pd.read_csv(csv)

    df_csv["File"] = csv
    df_csv["Loan"] = loan
    df_csv["Date-Series"] = pd.to_datetime(df_csv["Date"], dayfirst=True)

    if df is None:
        df = df_csv
    else:
        df = pd.concat([df, df_csv], ignore_index=True)

    return df


def read_from_files():
    path_loans = "loans"

    path_fixed = "fixed"
    path_variable = "variable"

    path_fixed = join(path_loans, path_fixed)
    path_variable = join(path_loans, path_variable)

    csvs_fixed = [
        join(path_fixed, f)
        for f in listdir(path_fixed)
        if isfile(join(path_fixed, f)) and ".csv" in f
    ]
    csvs_variable = [
        join(path_variable, f)
        for f in listdir(path_variable)
        if isfile(join(path_variable, f)) and ".csv" in f
    ]

    df = None

    for csv in csvs_fixed:
        df = read_from_file(df, csv, "Fixed")
    for csv in csvs_variable:
        df = read_from_file(df, csv, "Variable")

    df.drop_duplicates(inplace=True)

    df["Label"] = df.apply(label_row, axis=1)

    return df


def label_row(row):
    if "Repayment" in row["Description"]:
        return "Repayment"
    if "Interest" in row["Description"]:
        return "Interest"
    return "Other"


def get_dataframe():
    df = read_from_files()
    return df
