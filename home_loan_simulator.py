from datetime import timedelta
import pandas as pd


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

    while principal > 0:
        curr_date = curr_date + timedelta(days=1)

        curr_interest = 0
        curr_repayment = 0

        # interest: assuming that nothing was repaid in the previous interest period,
        #           since in general there were repayments, the interest charged here is too low

        if curr_date == prev_interest_date + interest_period:
            curr_interest = (
                max(0, principal - offset)
                * (interest_period.days / 365)
                * (interest / 100)
            )

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
        columns=["Month", "Years", "Date", "Repayment", "Interest", "Principal"],
    )
