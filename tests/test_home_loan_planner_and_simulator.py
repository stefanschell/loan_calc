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
    "N, cycle, P, R0",
    [
        (15, hls.Cycle.FORTNIGHTLY, 500000, 5.0 / 100),
        (20, hls.Cycle.MONTHLY_AVERAGE, 2000000, 8.0 / 100),
        (25, hls.Cycle.MONTHLY_AVERAGE, 1000000, 6.0 / 100),
        (30, hls.Cycle.FORTNIGHTLY, 1000000, 4.0 / 100),
        (35, hls.Cycle.MONTHLY_AVERAGE, 1000000, 5.0 / 100),
        (40, hls.Cycle.MONTHLY_END_OF_MONTH, 1000000, 3.0 / 100),
    ],
)
def test_planner_and_simulator(N, cycle, P, R0):
    # check params

    allowed_cycles = [item for item in hls.Cycle if item != hls.Cycle.YEARLY]
    assert cycle in allowed_cycles

    # setup loan using HomeLoanPlanner

    planner = hlp.HomeLoanPlanner(
        "TestLoan",
        N=N,
        k=(365 / 14) if cycle == hls.Cycle.FORTNIGHTLY else 12,
        P=P,
        R0=R0,
    )

    # run base simulation using Home Loan Simulator

    today = pd.to_datetime("today")

    df_base = hls.simulate(
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

    # check base simulation

    loan_years = df_base.iloc[-1]["LoanYears"]
    total_interest = df_base["Interest"].sum()
    total_repayment = df_base["Repayment"].sum()

    assert round(loan_years) == N
    assert total_interest > 0
    assert total_repayment > P
    assert round((P + total_interest) - total_repayment) == 0

    # run and check modified simulation: with offset

    df_with_offset = hls.simulate(
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

    assert df_with_offset.iloc[-1]["LoanYears"] < loan_years
    assert df_with_offset["Interest"].sum() < total_interest
    assert df_with_offset["Repayment"].sum() < total_repayment
    assert (
        round(
            (P + df_with_offset["Interest"].sum()) - df_with_offset["Repayment"].sum()
        )
        == 0
    )

    # run and check modified simulation: with increased interest

    df_increased_interest = hls.simulate(
        loan_start=today,
        principal=P,
        offset=0,
        schedule_start=today,
        interest_rate=(R0 + 0.01) * 100,
        prev_interest_date=today,
        interest_cycle=cycle,
        repayment=planner.c0,
        prev_repayment_date=today,
        repayment_cycle=cycle,
        repayment_use_stash=False,
    )

    assert df_increased_interest.iloc[-1]["LoanYears"] > loan_years
    assert df_increased_interest["Interest"].sum() > total_interest
    assert df_increased_interest["Repayment"].sum() > total_repayment
    assert (
        round(
            (P + df_increased_interest["Interest"].sum())
            - df_increased_interest["Repayment"].sum()
        )
        == 0
    )

    # run and check modified simulation: with activated usage of stash

    df_with_use_stash = hls.simulate(
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

    assert df_with_use_stash.iloc[-1]["LoanYears"] == loan_years
    assert df_with_use_stash["Interest"].sum() == total_interest
    assert df_with_use_stash["Repayment"].sum() == total_repayment
    assert (
        round(
            (P + df_with_use_stash["Interest"].sum())
            - df_with_use_stash["Repayment"].sum()
        )
        == 0
    )
