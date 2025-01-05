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
    schedule_end=None,
    leftover_incoming=None,
    leftover_amount=None,
    leftover_repayment=None,
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
            0,
            principal,
        )
    )

    while principal > 0 or (
        leftover_incoming is not None and curr_date <= leftover_incoming
    ):
        curr_date = curr_date + timedelta(days=1)

        curr_interest = None
        curr_redraw = None
        curr_repayment = None

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

        # redraw

        if leftover_incoming is not None and leftover_amount is not None:
            if curr_date >= leftover_incoming:
                curr_redraw = leftover_amount
                principal = principal + leftover_amount
                leftover_amount = None  # making sure the amount is only added once

        # repayment

        actual_repayment = repayment

        if leftover_incoming is not None and leftover_repayment is not None:
            if curr_date >= leftover_incoming:
                actual_repayment = actual_repayment + leftover_repayment

        if curr_date >= prev_repayment_date + repayment_cycle_days:
            curr_repayment = min(principal, actual_repayment)

            principal = principal - curr_repayment
            prev_repayment_date = prev_repayment_date + repayment_cycle_days

        # data collection

        if (
            curr_interest is not None
            or curr_redraw is not None
            or curr_repayment is not None
        ):
            schedule.append(
                (
                    (curr_date - schedule_start).days / (365 / 12),
                    (curr_date - schedule_start).days / 365,
                    curr_date,
                    curr_interest,
                    curr_redraw,
                    curr_repayment,
                    principal,
                )
            )

        if schedule_end is not None and curr_date >= schedule_end:
            break

    return pd.DataFrame(
        schedule,
        columns=[
            "Months",
            "Years",
            "Date",
            "Interest",
            "Redraw",
            "Repayment",
            "Principal",
        ],
    )
