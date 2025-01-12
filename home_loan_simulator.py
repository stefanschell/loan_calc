from enum import Enum
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np


class Cycle(Enum):
    FORTNIGHTLY = "fortnightly"
    MONTHLY_AVERAGE = "monthly (average)"

    def __str__(self):
        return str(self.value)


def increment_date(prev_date, cycle: Cycle):
    if cycle == Cycle.FORTNIGHTLY:
        return prev_date + timedelta(days=14)
    elif cycle == Cycle.MONTHLY_AVERAGE:
        return prev_date + timedelta(days=365 / 12)
    raise ValueError("Invalid cycle")


def simulate(
    *,
    loan_start,
    principal,
    offset,
    schedule_start,
    interest_rate,
    prev_interest_date,
    interest_cycle: Cycle,
    repayment,
    prev_repayment_date,
    repayment_cycle: Cycle,
    schedule_end=None,
    leftover_incoming=None,
    leftover_amount=None,
    leftover_repayment=None,
):
    curr_date = schedule_start

    schedule = []
    owing_daily_hist = []

    schedule.append(
        (
            curr_date,
            (curr_date - loan_start).days / 365,
            relativedelta(curr_date, loan_start),
            (curr_date - schedule_start).days / 365,
            relativedelta(curr_date, schedule_start),
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

        maturity_is_today = schedule_end is not None and curr_date >= schedule_end

        curr_interest = None
        curr_redraw = None
        curr_repayment = None

        # interest
        # note: we keep track of the amount owning on a daily basis,
        #       back to the previous interest calculation

        owing_daily_hist.append(max(0, principal - offset))

        if (
            curr_date >= increment_date(prev_interest_date, interest_cycle)
            or maturity_is_today
        ):
            curr_interest_date = (
                increment_date(prev_interest_date, interest_cycle)
                if not maturity_is_today
                else curr_date
            )

            curr_interest_cycle_days = curr_interest_date - prev_interest_date

            curr_interest = (
                np.mean(owing_daily_hist)
                * (
                    (curr_interest_cycle_days.days / float(365))
                    + (curr_interest_cycle_days.seconds / float(60 * 60 * 24 * 365))
                )
                * (interest_rate / 100)
            )

            owing_daily_hist = []

            principal = principal + curr_interest
            prev_interest_date = curr_interest_date

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

        if curr_date >= increment_date(prev_repayment_date, repayment_cycle):
            curr_repayment = min(principal, actual_repayment)

            principal = principal - curr_repayment
            prev_repayment_date = increment_date(prev_repayment_date, repayment_cycle)

        # data collection

        if (
            curr_interest is not None
            or curr_redraw is not None
            or curr_repayment is not None
            or maturity_is_today is True
        ):
            schedule.append(
                (
                    curr_date,
                    (curr_date - loan_start).days / 365,
                    relativedelta(curr_date, loan_start),
                    (curr_date - schedule_start).days / 365,
                    relativedelta(curr_date, schedule_start),
                    curr_interest,
                    curr_redraw,
                    curr_repayment,
                    principal,
                )
            )

        # maturity

        if maturity_is_today:
            break

        # safety check

        if curr_date - schedule_start > timedelta(days=100 * 365):
            raise RuntimeError("Repayments did not finish within 100 years")

    # return result

    return pd.DataFrame(
        schedule,
        columns=[
            "Date",
            "LoanYears",
            "LoanDuration",
            "ScheduleYears",
            "ScheduleDuration",
            "Interest",
            "Redraw",
            "Repayment",
            "Principal",
        ],
    )
