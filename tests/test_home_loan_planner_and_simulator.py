import pandas as pd
import pytest

import home_loan_planner as hlp
import home_loan_simulator as hls


@pytest.mark.parametrize(
    "N, k, P, R0, c0",
    [
        (15, 365 / 14, 500000, 5.0 / 100, 1819),
        (20, 12, 2000000, 8.0 / 100, 16729),
        (25, 12, 1000000, 6.0 / 100, 6443),
    ],
)
def test_planner(N, k, P, R0, c0):
    planner = hlp.HomeLoanPlanner(
        "TestLoan",
        N=N,
        k=k,
        P=P,
        R0=R0,
    )
    assert round(planner.c0) == c0


@pytest.mark.parametrize(
    "N, P, R0, c0, cycle",
    [
        (15, 500000, 5.0 / 100, 1819, hls.Cycle.FORTNIGHTLY),
        (20, 2000000, 8.0 / 100, 16729, hls.Cycle.MONTHLY_AVERAGE),
        (25, 1000000, 6.0 / 100, 6443, hls.Cycle.MONTHLY_AVERAGE),
    ],
)
def test_planner_and_simulator(N, P, R0, c0, cycle):
    allowed_cycles = [item for item in hls.Cycle if item != hls.Cycle.YEARLY]
    assert cycle in allowed_cycles

    planner = hlp.HomeLoanPlanner(
        "TestLoan",
        N=N,
        k=(365 / 14) if cycle == hls.Cycle.FORTNIGHTLY else 12,
        P=P,
        R0=R0,
    )
    assert round(planner.c0) == c0

    today = pd.to_datetime("today")

    df_simulated = hls.simulate(
        loan_start=today,
        principal=P,
        offset=0,
        schedule_start=today,
        interest_rate=R0 * 100,
        prev_interest_date=today,
        interest_cycle=cycle,
        repayment=planner.c0,
        prev_repayment_date=today,
        repayment_cycle=cycle,
        repayment_use_stash=False,
    )

    loan_years = df_simulated.iloc[-1]["LoanYears"]
    total_interest = df_simulated["Interest"].sum()
    total_repayment = df_simulated["Repayment"].sum()

    assert round(loan_years) == N
    assert total_interest > 0
    assert total_repayment > P

    df_simulated_offset = hls.simulate(
        loan_start=today,
        principal=P,
        offset=100000,
        schedule_start=today,
        interest_rate=R0 * 100,
        prev_interest_date=today,
        interest_cycle=cycle,
        repayment=planner.c0,
        prev_repayment_date=today,
        repayment_cycle=cycle,
        repayment_use_stash=False,
    )

    assert df_simulated_offset.iloc[-1]["LoanYears"] < loan_years
    assert df_simulated_offset["Interest"].sum() < total_interest
    assert df_simulated_offset["Repayment"].sum() < total_repayment

    df_simulated_repayment_use_stash = hls.simulate(
        loan_start=today,
        principal=P,
        offset=0,
        schedule_start=today,
        interest_rate=R0 * 100,
        prev_interest_date=today,
        interest_cycle=cycle,
        repayment=planner.c0,
        prev_repayment_date=today,
        repayment_cycle=cycle,
        repayment_use_stash=True,
    )

    assert df_simulated_repayment_use_stash.iloc[-1]["LoanYears"] == loan_years
    assert df_simulated_repayment_use_stash["Interest"].sum() == total_interest
    assert df_simulated_repayment_use_stash["Repayment"].sum() == total_repayment
