import pandas as pd
import pytest

import home_loan_planner
import home_loan_simulator


@pytest.mark.parametrize(
    "N, k, P, R0, c0",
    [
        (15, 365 / 14, 500000, 5.0 / 100, 1819),
        (20, 12, 2000000, 8.0 / 100, 16729),
        (25, 12, 1000000, 6.0 / 100, 6443),
    ],
)
def test_planner(N, k, P, R0, c0):
    planner = home_loan_planner.HomeLoanPlanner(
        "TestLoan",
        N=N,
        k=k,
        P=P,
        R0=R0,
    )
    assert round(planner.c0) == c0


@pytest.mark.parametrize(
    "N, P, R0, c0",
    [
        (20, 2000000, 8.0 / 100, 16729),
        (25, 1000000, 6.0 / 100, 6443),
    ],
)
def test_planner_and_simulator(N, P, R0, c0):
    planner = home_loan_planner.HomeLoanPlanner(
        "TestLoan",
        N=N,
        k=12,
        P=P,
        R0=R0,
    )
    assert round(planner.c0) == c0

    today = pd.to_datetime("today")

    df_simulated = home_loan_simulator.simulate(
        loan_start=today,
        principal=P,
        offset=0,
        schedule_start=today,
        interest_rate=R0 * 100,
        prev_interest_date=today,
        interest_cycle=home_loan_simulator.Cycle.MONTHLY_AVERAGE,
        repayment=planner.c0,
        prev_repayment_date=today,
        repayment_cycle=home_loan_simulator.Cycle.MONTHLY_AVERAGE,
        repayment_use_stash=False,
        schedule_end=None,
    )

    assert round(df_simulated.iloc[-1]["LoanYears"]) == N
