import pandas as pd
import home_loan_planner
import home_loan_simulator


def simulated_to_demo(
    df_simulated: pd.DataFrame,
    extrarepayment,
    simulation_end: pd.Timestamp,
    account_name,
) -> pd.DataFrame:

    data = []

    first_row = df_simulated.iloc[0]
    data.append(
        (
            "initial redraw",
            0,
            -first_row["Principal"],
            first_row["Principal"],
            first_row["Date"],
            "Redraw",
        )
    )

    for _, row in df_simulated.iterrows():
        if row["Date"] > simulation_end:
            break

        if row["Interest"] > 0:
            data.append(
                (
                    "interest (monthly)",
                    0,
                    -row["Interest"],
                    row["Principal"],
                    row["Date"],
                    "Interest",
                )
            )

        if row["Repayment"] > 0:
            total_repayment = row["Repayment"]
            data.append(
                (
                    "repayment (fortnightly)",
                    total_repayment - extrarepayment,
                    0,
                    row["Principal"] + extrarepayment,
                    row["Date"],
                    "Repayment",
                )
            )
            if extrarepayment > 0:
                data.append(
                    (
                        "extrarepayment (fortnightly)",
                        extrarepayment,
                        0,
                        row["Principal"],
                        row["Date"],
                        "Extrarepayment",
                    )
                )

    df_demo = pd.DataFrame(
        data=data,
        columns=[
            "Description",
            "Credit",
            "Debit",
            "Balance",
            "DateSeries",
            "Label",
        ],
    )

    df_demo["AccountName"] = account_name

    return df_demo


def create_demo_account(
    demo_start: pd.Timestamp, demo_end: pd.Timestamp
) -> pd.DataFrame:

    interest_fixed = 5.5
    interest_variable = 6.5
    loan_amount = 1000000
    loan_amount_fixed_fraction = 0.4
    length_of_term = 15
    extrarepayment_fraction_variable = 0.3

    loan_amount_fixed = loan_amount_fixed_fraction * loan_amount
    loan_amount_variable = loan_amount - loan_amount_fixed

    repayment_fixed_planned = home_loan_planner.HomeLoanPlanner(
        "Demo",
        N=length_of_term,
        k=(365 / 14),
        P=loan_amount_fixed,
        R0=interest_fixed / 100,
    ).c0

    repayment_variable_planned = home_loan_planner.HomeLoanPlanner(
        "Demo",
        N=length_of_term,
        k=(365 / 14),
        P=loan_amount_variable,
        R0=interest_variable / 100,
    ).c0

    extrarepayment_variable_planned = (
        extrarepayment_fraction_variable * repayment_variable_planned
    )
    repayment_variable_planned = (
        repayment_variable_planned - extrarepayment_variable_planned
    )

    schedule_start = demo_start
    schedule_end = demo_end + pd.Timedelta(31 * 365, unit="days")

    df_simulated_fixed = home_loan_simulator.simulate(
        loan_start=schedule_start,
        principal=loan_amount_fixed,
        offset=0,
        schedule_start=schedule_start,
        interest_rate=interest_fixed,
        prev_interest_date=schedule_start,
        interest_cycle=home_loan_simulator.Cycle.MONTHLY_END_OF_MONTH,
        repayment=repayment_fixed_planned,
        prev_repayment_date=schedule_start,
        repayment_cycle=home_loan_simulator.Cycle.FORTNIGHTLY,
        repayment_use_stash=False,
        schedule_end=schedule_end,
    )

    df_simulated_variable = home_loan_simulator.simulate(
        loan_start=schedule_start,
        principal=loan_amount_variable,
        offset=0,
        schedule_start=schedule_start,
        interest_rate=interest_variable,
        prev_interest_date=schedule_start,
        interest_cycle=home_loan_simulator.Cycle.MONTHLY_END_OF_MONTH,
        repayment=repayment_variable_planned + extrarepayment_variable_planned,
        prev_repayment_date=schedule_start,
        repayment_cycle=home_loan_simulator.Cycle.FORTNIGHTLY,
        repayment_use_stash=False,
        schedule_end=schedule_end,
    )

    df_demo_fixed = simulated_to_demo(df_simulated_fixed, 0, demo_end, "Fixed")

    df_demo_variable = simulated_to_demo(
        df_simulated_variable,
        extrarepayment_variable_planned,
        demo_end,
        "Variable",
    )

    df_demo_offset = pd.DataFrame(
        data=[("no offset", 0, 0, 0, demo_start, "OffsetUp", "Offset")],
        columns=[
            "Description",
            "Credit",
            "Debit",
            "Balance",
            "DateSeries",
            "Label",
            "AccountName",
        ],
    )

    df_demo = pd.concat([df_demo_fixed, df_demo_variable, df_demo_offset])

    df_demo.sort_values(
        by="DateSeries", inplace=True, kind="stable", ascending=True
    )  # sort
    df_demo.reset_index(inplace=True, drop=True)

    return df_demo
