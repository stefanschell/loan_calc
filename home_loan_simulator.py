from datetime import timedelta
import pandas as pd
import numpy as np


def simulate(
    principal,
    offset,
    interest,
    interest_period,
    repayment,
    repayment_period,
    start_day,
):
    interest_period = timedelta(days=interest_period)
    repayment_period = timedelta(days=repayment_period)

    prev_interest_date = start_day
    prev_repayment_date = start_day

    curr_date = start_day

    schedule = []
    owing_daily_hist = []

    while principal > 0:
        curr_date = curr_date + timedelta(days=1)

        curr_interest = 0
        curr_repayment = 0

        # interest
        # note: we keep track of the amount owning on a daily basis,
        #       back to the previous interest calculation

        owing_daily_hist.append(max(0, principal - offset))

        if curr_date == prev_interest_date + interest_period:
            curr_interest = (
                np.mean(owing_daily_hist)
                * (interest_period.days / 365)
                * (interest / 100)
            )

            owing_daily_hist = []

            principal = principal + curr_interest
            prev_interest_date = curr_date

        # repayment

        if curr_date == prev_repayment_date + repayment_period:
            curr_repayment = min(principal, repayment)

            principal = principal - curr_repayment
            prev_repayment_date = curr_date

        # data collection

        if curr_repayment != 0 or curr_interest != 0:
            schedule.append(
                (
                    (curr_date - start_day).days / 30,
                    (curr_date - start_day).days / 365,
                    curr_date,
                    curr_repayment,
                    curr_interest,
                    principal,
                )
            )

    return pd.DataFrame(
        schedule,
        columns=["Months", "Years", "Date", "Repayment", "Interest", "Principal"],
    )
