from datetime import timedelta
import pandas as pd
import numpy as np


def simulate(
    principal,
    offset,
    interest_rate,
    interest_cycle_days,
    repayment,
    repayment_cycle_days,
    schedule_start,
):
    interest_cycle_days = timedelta(days=interest_cycle_days)
    repayment_cycle_days = timedelta(days=repayment_cycle_days)

    prev_interest_date = schedule_start
    prev_repayment_date = schedule_start

    curr_date = schedule_start

    schedule = []
    owing_daily_hist = []

    schedule.append(
        (
            0,
            0,
            curr_date,
            0,
            0,
            principal,
        )
    )

    while principal > 0:
        curr_date = curr_date + timedelta(days=1)

        curr_interest = 0
        curr_repayment = 0

        # interest
        # note: we keep track of the amount owning on a daily basis,
        #       back to the previous interest calculation

        owing_daily_hist.append(max(0, principal - offset))

        if curr_date >= prev_interest_date + interest_cycle_days:
            curr_interest = (
                np.mean(owing_daily_hist)
                * (
                    (interest_cycle_days.days / float(365))
                    + (interest_cycle_days.seconds / float(60 * 60 * 24 * 365))
                )
                * (interest_rate / 100)
            )

            owing_daily_hist = []

            principal = principal + curr_interest
            prev_interest_date = prev_interest_date + interest_cycle_days

        # repayment

        if curr_date >= prev_repayment_date + repayment_cycle_days:
            curr_repayment = min(principal, repayment)

            principal = principal - curr_repayment
            prev_repayment_date = prev_repayment_date + repayment_cycle_days

        # data collection

        if curr_repayment != 0 or curr_interest != 0:
            schedule.append(
                (
                    (curr_date - schedule_start).days / (365 / 12),
                    (curr_date - schedule_start).days / 365,
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
