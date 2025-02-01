from enum import Enum
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np


class Cycle(Enum):
    FORTNIGHTLY = "fortnightly"
    MONTHLY_AVERAGE = "monthly, every 365/12 days"
    MONTHLY_1ST_OF_MONTH = "monthly, 1st of every month"
    MONTHLY_END_OF_MONTH = "monthly, end of every month"
    YEARLY = "yearly, every 365 days"

    def complex_str(self):
        return str(self.value)

    def simple_str(self):
        if "," in self.value:
            return self.value.split(",")[0]
        else:
            return self.value

    def is_fortnightly(self):
        return self in [Cycle.FORTNIGHTLY]

    def is_monthly(self):
        return self in [
            Cycle.MONTHLY_AVERAGE,
            Cycle.MONTHLY_1ST_OF_MONTH,
            Cycle.MONTHLY_END_OF_MONTH,
        ]

    def is_yearly(self):
        return self in [Cycle.YEARLY]


def increment_date(date: pd.Timestamp, cycle: Cycle) -> pd.Timestamp:
    if cycle == Cycle.FORTNIGHTLY:
        date = date + timedelta(days=14)
        return date

    if cycle == Cycle.MONTHLY_AVERAGE:
        date = date + timedelta(days=365 / 12)
        return date

    if cycle == Cycle.MONTHLY_1ST_OF_MONTH:
        date = date.replace(day=1)  # first of current month
        date = (date + timedelta(days=31)).replace(day=1)  # first of next month
        return date

    if cycle == Cycle.MONTHLY_END_OF_MONTH:
        date_is_last_day_of_month = (date + timedelta(days=1)).month != date.month

        # normal behavior: we are calling this method with date being at the end of the month,
        #                  thus, we want the end of next month
        date = date.replace(day=1)  # first of current month
        date = (date + timedelta(days=31)).replace(day=1)  # first of next month
        date = (date + timedelta(days=31)).replace(day=1)  # first of month after next
        date = date - timedelta(days=1)  # end of next month
        if date_is_last_day_of_month:
            return date

        # special behavior: we are calling this method with date not being at the end of the month,
        #                   thus, we want the end of this month
        date = date.replace(day=1)  # first of current month
        date = (date + timedelta(days=31)).replace(day=1)  # first of next month
        date = date - timedelta(days=1)  # end of this month
        return date

    if cycle == Cycle.YEARLY:
        date = date + timedelta(days=365)
        return date

    raise ValueError("Invalid cycle")


def simulate(
    *,
    loan_start: pd.Timestamp,
    principal,
    offset,
    schedule_start: pd.Timestamp,
    interest_rate,
    prev_interest_date: pd.Timestamp,
    interest_cycle: Cycle,
    repayment,
    prev_repayment_date: pd.Timestamp,
    repayment_cycle: Cycle,
    schedule_end: pd.Timestamp = None,
    leftover_incoming: pd.Timestamp = None,
    leftover_amount=None,
    leftover_repayment=None,
    extra_win_amount=None,
    extra_win_cycle: Cycle = None,
    extra_win_duration=None,
) -> pd.DataFrame:
    curr_date = schedule_start

    if extra_win_duration is not None:
        extra_win_end = schedule_start + extra_win_duration
    else:
        extra_win_end = None

    prev_extra_win_date = None
    if extra_win_cycle is not None:
        prev_extra_win_date = curr_date

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
            0,
            0,
            principal,
        )
    )

    while (
        principal > 0
        or (leftover_incoming is not None and curr_date <= leftover_incoming)
        or (extra_win_end is not None and curr_date <= extra_win_end)
    ):
        curr_date = curr_date + timedelta(days=1)

        maturity_is_today = schedule_end is not None and curr_date >= schedule_end

        curr_interest = None
        curr_redraw = None
        curr_repayment = None
        curr_extra_win_for_loan = None
        curr_extra_win_for_us = None

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

            curr_interest_length = curr_interest_date - prev_interest_date

            curr_interest = (
                np.mean(owing_daily_hist)
                * (
                    (curr_interest_length.days / float(365))
                    + (curr_interest_length.seconds / float(60 * 60 * 24 * 365))
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

        # extra win

        if prev_extra_win_date is not None and extra_win_amount is not None:
            if curr_date >= increment_date(prev_extra_win_date, extra_win_cycle) and (
                extra_win_end is None or curr_date <= extra_win_end
            ):
                curr_extra_win_for_loan = min(principal, extra_win_amount)
                curr_extra_win_for_us = extra_win_amount - curr_extra_win_for_loan

                principal = principal - curr_extra_win_for_loan
                prev_extra_win_date = increment_date(
                    prev_extra_win_date, extra_win_cycle
                )

        # data collection

        if (
            curr_interest is not None
            or curr_redraw is not None
            or curr_repayment is not None
            or curr_extra_win_for_loan is not None
            or curr_extra_win_for_us is not None
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
                    curr_extra_win_for_loan,
                    curr_extra_win_for_us,
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
            "ExtraWinForLoan",
            "ExtraWinForUs",
            "Principal",
        ],
    )
