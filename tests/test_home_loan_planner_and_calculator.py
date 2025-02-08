import pytest

import home_loan_planner
import home_loan_simulator


def test_basics():
    planner = home_loan_planner.HomeLoanPlanner(
        "Fixed",
        N=25,
        k=12,
        P=1000000,
        R0=6.0,
    )

    assert planner.c0 > 0
