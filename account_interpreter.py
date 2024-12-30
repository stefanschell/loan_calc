import pandas as pd
import numpy as np
from scipy.optimize import curve_fit


def get_balance_over_time(
    df, account_name, add_col_with_account_name=False, return_positive_balance=False
):
    df = pd.DataFrame(df)

    df = df[df["AccountName"] == account_name]
    df = df[["DateSeries", "Balance"]]

    df = df.drop_duplicates(subset=["DateSeries"], keep="last")

    if add_col_with_account_name:
        df["AccountName"] = account_name
    if return_positive_balance:
        df["Balance"] = abs(df["Balance"])

    return df


def find_balance(df, date):
    previous = df[df["DateSeries"] <= date]["Balance"]
    if len(previous) > 0:
        return previous.iloc[-1]
    return 0


def find_mean_balance(df, start_date, end_date):
    dates = (
        pd.date_range(start=start_date, end=end_date, freq="D").to_pydatetime().tolist()
    )

    balances = []
    for date in dates:
        balances.append(find_balance(df, date))

    return np.mean(balances)


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
        df["AccountName"] = "Total"
    if return_positive_balance:
        df["Balance"] = abs(df["Balance"])

    return df


def add_interest_information_for_account(df, account_name):
    df_account = get_balance_over_time(df, account_name)
    if account_name == "Variable":
        df_offset = get_balance_over_time(df, "Offset")

    for curr_index, curr_row in df.iterrows():
        if curr_row["AccountName"] == account_name and curr_row["Label"] == "Interest":
            prev_rows = df[
                (df["AccountName"] == account_name)
                & (df["Label"] == "Interest")
                & (df["DateSeries"] < curr_row["DateSeries"])
            ]

            if len(prev_rows) > 0:
                prev_row = prev_rows.iloc[-1]
            else:
                prev_row = df.iloc[0]

            prev_date = prev_row["DateSeries"]
            curr_date = curr_row["DateSeries"]

            interest_period = curr_date - prev_date
            df.loc[curr_index, "InterestPeriod"] = interest_period

            approx_offset = 0
            if account_name == "Variable":
                # use mean offset in interest period
                approx_offset = abs(find_mean_balance(df_offset, prev_date, curr_date))

            # use mean loan in interest period
            approx_loan = abs(find_mean_balance(df_account, prev_date, curr_date))

            approx_owing = max(0, approx_loan - approx_offset)

            df.loc[curr_index, "ApproxInterest"] = (
                (abs(curr_row["Debit"]) / approx_owing)
                / interest_period.days
                * 365
                * 100
            )

    return df


def add_interest_information(df):
    df = add_interest_information_for_account(df, "Fixed")
    df = add_interest_information_for_account(df, "Variable")
    return df


def get_interest_over_time(df, account_name, exclude_up_to_date):
    return_df = df[(df["AccountName"] == account_name) & (df["Label"] == "Interest")][
        ["DateSeries", "Debit", "Label"]
    ]
    return_df = return_df.rename(columns={"Debit": "Change"})
    return_df["Change"] = abs(return_df["Change"])
    return_df = return_df[return_df["DateSeries"] > exclude_up_to_date]
    return return_df


def get_redraw_repayment_extrarepayment_over_time(df, account_name, exclude_up_to_date):
    return_df = df[
        (df["AccountName"] == account_name)
        & (
            (df["Label"] == "Redraw")
            | (df["Label"] == "Repayment")
            | (df["Label"] == "Extrarepayment")
        )
    ][["DateSeries", "Debit", "Credit", "Label"]]
    return_df["Debit"] = return_df["Debit"].fillna(0)
    return_df["Credit"] = return_df["Credit"].fillna(0)
    return_df["Change"] = abs(return_df["Debit"]) + abs(return_df["Credit"])
    return_df.drop("Debit", axis=1, inplace=True)
    return_df.drop("Credit", axis=1, inplace=True)
    return_df = return_df[return_df["DateSeries"] > exclude_up_to_date]
    return return_df


def get_change_overt_time(df, account_name, exclude_up_to_date):
    df1 = get_interest_over_time(df, account_name, exclude_up_to_date)
    df2 = get_redraw_repayment_extrarepayment_over_time(
        df, account_name, exclude_up_to_date
    )
    df = pd.concat([df1, df2], axis=0)
    return df


def add_interpolated_value(
    df,
    label,
    col_name,
    timespan_search,
    timespan_include,
    timespane_normalize,
    drop_original,
    is_first_call=False,
):
    if is_first_call:
        df["interpolated"] = False

    new_rows = []

    for _, curr_row in df.iterrows():
        if curr_row["Label"] == label:
            df_previous_search = df[
                (df["Label"] == label)
                & (df["DateSeries"] > curr_row["DateSeries"] - timespan_search)
                & (df["DateSeries"] <= curr_row["DateSeries"])
            ]
            timespan_data_search = (
                df_previous_search.iloc[-1]["DateSeries"]
                - df_previous_search.iloc[0]["DateSeries"]
            )
            df_previous_include = df[
                (df["Label"] == label)
                & (df["DateSeries"] > curr_row["DateSeries"] - timespan_include)
                & (df["DateSeries"] <= curr_row["DateSeries"])
            ]
            timespan_data_include = (
                df_previous_include.iloc[-1]["DateSeries"]
                - df_previous_include.iloc[0]["DateSeries"]
            )

            new_row = curr_row.to_dict()
            new_row["interpolated"] = True

            if timespan_data_include.days > 0:
                new_row[col_name] = (
                    df_previous_include[col_name].mean()
                    / (
                        timespan_data_include.days
                        + timespan_data_include.seconds / (60 * 60 * 24)
                    )
                    * (
                        timespane_normalize.days
                        + timespane_normalize.seconds / (60 * 60 * 24)
                    )
                )
            else:
                if timespan_data_search.days > 0 or timespan_data_search.seconds > 0:
                    new_row[col_name] = (
                        curr_row[col_name]
                        / (
                            timespan_data_search.days
                            + timespan_data_search.seconds / (60 * 60 * 24)
                        )
                        * (
                            timespane_normalize.days
                            + timespane_normalize.seconds / (60 * 60 * 24)
                        )
                    )
                else:
                    new_row[col_name] = np.nan

            new_rows.append(new_row)

    df = pd.concat([df, pd.DataFrame(new_rows)])

    if drop_original:
        df = df[df["Label"] != label]

    return df


def my_fit_function(t, P, J, N):
    return P * (1 - ((1 + J) ** t - 1) / ((1 + J) ** N - 1))


def fit_balance(df_balance_in):
    t_in = df_balance_in["DateSeries"]
    p_in = df_balance_in["Balance"]
    a0_in = df_balance_in["AccountName"].iloc[0]

    t = t_in.map(pd.Timestamp.timestamp)
    t = t.to_numpy()
    t = t / (60 * 60 * 24 * 14)
    t0 = t[0]
    t = t - t0
    p = p_in.to_numpy()

    initial_guess = [1000000.0, 0.3, 15]  # Initial guess for P, J, N
    popt, _ = curve_fit(my_fit_function, t, p, p0=initial_guess)

    ti = np.linspace(t[0], t[-1], 100)
    pi = my_fit_function(ti, *popt)
    pi = np.clip(pi, a_min=0, a_max=None)

    t_out = (
        pd.to_datetime((ti + t0) * (60 * 60 * 24 * 14), unit="s")
        .to_series(name="DateSeries")
        .reset_index(drop=True)
    )
    p_out = pd.Series(pi, name="Balance")

    df_balance_out = pd.DataFrame({"DateSeries": t_out, "Balance": p_out})
    df_balance_out["AccountName"] = a0_in + " (fit)"

    return df_balance_out
