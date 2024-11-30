import pandas as pd
import plotly.express as px
import streamlit as st
import account_reader
import account_interpreter
import home_loan_simulator
import home_loan_planner
from datetime import timedelta

# get data

loan_start = pd.to_datetime("2024-09-16")
fixed_loan_end = loan_start + timedelta(days=365 * 5)

df_in = account_reader.get_dataframe(date_from=loan_start)
df_in = account_interpreter.add_interest_information(df_in)

# assuming that the last interest or repayment event is the start of the simulation
simulation_start = df_in[
    ((df_in["AccountName"] == "Fixed") | (df_in["AccountName"] == "Variable"))
    & ((df_in["Label"] == "Interest") | (df_in["Label"] == "Repayment"))
]["DateSeries"].iloc[-1]

# setup

st.set_page_config(layout="wide")
st.title("Home Loan")

# Transactions

st.write("## Transactions")

col1, col2, col3 = st.columns(3)
with col1:
    toggle_fixed = st.toggle("Fixed", True)
with col2:
    toggle_variable = st.toggle("Variable", True)
with col3:
    toggle_offset = st.toggle("Offset", True)

df_table = pd.DataFrame(df_in)
if not toggle_fixed:
    df_table = df_table[df_table["AccountName"] != "Fixed"]
if not toggle_variable:
    df_table = df_table[df_table["AccountName"] != "Variable"]
if not toggle_offset:
    df_table = df_table[df_table["AccountName"] != "Offset"]

st.dataframe(df_table)

# Over time

st.write("## Over time")

df_balance_fixed = account_interpreter.get_balance_over_time(
    df_in, "Fixed", add_col_with_account_name=True, return_positive_balance=True
)
df_balance_variable = account_interpreter.get_balance_over_time(
    df_in, "Variable", add_col_with_account_name=True, return_positive_balance=True
)
df_balance_offset = account_interpreter.get_balance_over_time(
    df_in, "Offset", add_col_with_account_name=True, return_positive_balance=True
)

df_balance_total = account_interpreter.get_total_balance_over_time(
    df_in, add_col_with_account_name=True, return_positive_balance=True
)

df_plot = pd.concat(
    [df_balance_fixed, df_balance_variable, df_balance_offset, df_balance_total]
)

fig = px.scatter(df_plot, x="DateSeries", y="Balance", color="AccountName")
fig.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
fig.update_yaxes(title_text="Balance")
fig.update_layout(yaxis_range=[0, 1.3 * df_balance_total["Balance"].max()])

st.plotly_chart(fig)

# Calculation

st.write("## Calculation")

balance_fixed = account_interpreter.find_balance(df_balance_fixed, simulation_start)
repayment_fixed = df_in[
    (df_in["AccountName"] == "Fixed") & (df_in["Label"] == "Repayment")
].iloc[-1]["Credit"]
interest_fixed = df_in[
    (df_in["AccountName"] == "Fixed") & (df_in["Label"] == "Interest")
].iloc[-1]["ApproxInterest"]

balance_variable = account_interpreter.find_balance(
    df_balance_variable, simulation_start
)
repayment_variable = df_in[
    (df_in["AccountName"] == "Variable") & (df_in["Label"] == "Repayment")
].iloc[-1]["Credit"]
interest_variable = df_in[
    (df_in["AccountName"] == "Variable") & (df_in["Label"] == "Interest")
].iloc[-1]["ApproxInterest"]

balance_offset = account_interpreter.find_balance(df_balance_offset, simulation_start)

repayment_cycle = "fortnightly"
interest_cycle = "monthly"

with st.expander("Overide interest and repayment cycle"):

    interest_cycle_sel = st.selectbox(
        "Interest cycle override", ("fortnightly", "monthly"), index=1
    )
    if interest_cycle_sel is not None:
        interest_cycle = interest_cycle_sel

    repayment_cycle_sel = st.selectbox(
        "Repayment cycle override", ("fortnightly", "monthly"), index=0
    )
    if repayment_cycle_sel is not None:
        repayment_cycle = repayment_cycle_sel

st.write("Interest cycle: " + interest_cycle)
st.write("Repayment cycle: " + repayment_cycle)

col1, col2 = st.columns(2)

with col1:

    # Fixed

    st.write("### Fixed")

    with st.expander("Override variables"):

        toggle_balance_fixed = st.toggle("Override balance", False, key="k1a")

        if toggle_balance_fixed:
            balance_fixed = st.number_input(
                "Balance override: ", 0, 2000000, 625000, 1000, key="k1b"
            )

        toggle_repayment_fixed = st.toggle("Override repayment", False, key="k1c")

        if toggle_repayment_fixed:
            repayment_fixed = st.number_input(
                "Repayment override (" + repayment_cycle + "): ",
                0.0,
                10000.0,
                1812.84,
                50.0,
                key="k1d",
            )

        toggle_interest_fixed = st.toggle("Override interest rate", False, key="k1e")

        if toggle_interest_fixed:
            interest_fixed = st.number_input(
                "Interest rate override: ", 0.1, 15.0, 5.74, key="k1f"
            )

    st.write("Balance: " + str(balance_fixed))
    st.write("Repayment (" + repayment_cycle + "): " + str(repayment_fixed))

    if repayment_cycle == "fortnightly":
        st.write("Repayment (monthly): " + str(repayment_fixed / 14 * (365 / 12)))

    st.write("Interest: " + str(interest_fixed))
    st.write("Offset: None")

    with st.expander("Theoretical plan (for information only, not used)"):
        years_planner_fixed = st.number_input("Years", 1, 40, 25, 1, key="k1g")

        planner_fixed = home_loan_planner.HomeLoanPlanner(
            "Fixed",
            N=years_planner_fixed,
            k=(365 / 14) if repayment_cycle == "fortnightly" else 12,
            P=balance_fixed,
            R0=interest_fixed / 100,
        )

        st.write(
            "Repayment ("
            + repayment_cycle
            + "), for identical repayment and interest cycles: "
            + str(planner_fixed.c0)
        )

    extra_slider_fixed = st.slider(
        "Extra-Repayment (monthly), limited to AUD 10000 yearly, i.e. AUD 800 monthly: ",
        0,
        800,
        800,
        200,
        key="k1i",
    )

    repayment_extra_fixed = extra_slider_fixed
    if repayment_cycle == "fortnightly":
        repayment_extra_fixed = repayment_extra_fixed / (365 / 12) * 14
        st.write("Extra-Repayment (fortnightly): " + str(repayment_extra_fixed))

    df_schedule_fixed = home_loan_simulator.simulate(
        balance_fixed,
        0,
        interest_fixed,
        14 if interest_cycle == "fortnightly" else (365 / 12),
        repayment_fixed + repayment_extra_fixed,
        14 if repayment_cycle == "fortnightly" else (365 / 12),
        simulation_start,
    )

    df_schedule_fixed_wo_extra = home_loan_simulator.simulate(
        balance_fixed,
        0,
        interest_fixed,
        14 if interest_cycle == "fortnightly" else (365 / 12),
        repayment_fixed,
        14 if repayment_cycle == "fortnightly" else (365 / 12),
        simulation_start,
    )

    st.write(df_schedule_fixed)

    total_years_fixed = df_schedule_fixed.iloc[-1]["Years"]
    total_repayments_fixed = df_schedule_fixed["Repayment"].sum()
    total_interest_fixed = df_schedule_fixed["Interest"].sum()

    st.write("Years to go: " + str(total_years_fixed))
    st.write("Total repayments to go: " + str(total_repayments_fixed))
    st.write(
        "Total interest to go: "
        + str(total_interest_fixed)
        + " ("
        + str(100 * total_interest_fixed / total_repayments_fixed)
        + "%)"
    )

    end_of_fixed_loan_balance = df_schedule_fixed[
        df_schedule_fixed["Date"] >= fixed_loan_end
    ]

    if len(end_of_fixed_loan_balance) > 0:
        end_of_fixed_loan_balance = end_of_fixed_loan_balance.iloc[0]["Principal"]
        st.write(
            "Balance at end of fixed loan ("
            + str(fixed_loan_end)
            + "): "
            + str(end_of_fixed_loan_balance)
        )
    else:
        st.write("Principal reached zero before end of fixed loan.")

    st.write(".")

    fig1 = px.line(df_schedule_fixed, x="Date", y="Principal")
    fig1.add_trace(px.line(df_schedule_fixed_wo_extra, x="Date", y="Principal").data[0])
    fig1.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
    fig1.update_yaxes(title_text="Principal")

    st.plotly_chart(fig1)

    interest_plot_fixed = pd.DataFrame(df_schedule_fixed)
    interest_plot_fixed = interest_plot_fixed[interest_plot_fixed["Interest"] > 0]

    interest_plot_fixed_wo_extra = pd.DataFrame(df_schedule_fixed_wo_extra)
    interest_plot_fixed_wo_extra = interest_plot_fixed_wo_extra[
        interest_plot_fixed_wo_extra["Interest"] > 0
    ]

    fig2 = px.line(interest_plot_fixed, x="Years", y="Interest")
    fig2.add_trace(
        px.line(interest_plot_fixed_wo_extra, x="Years", y="Interest").data[0]
    )
    fig2.update_xaxes(title_text="Years")
    fig2.update_yaxes(title_text="Interest")

    st.plotly_chart(fig2)

with col2:

    # Variable

    st.write("### Variable")

    with st.expander("Override variables"):

        toggle_balance_variable = st.toggle("Override balance", False, key="k2a")

        if toggle_balance_variable:
            balance_variable = st.number_input(
                "Balance override: ", 0, 2000000, 625000, 1000, key="k2b"
            )

        toggle_repayment_variable = st.toggle("Override repayment", False, key="k2c")

        if toggle_repayment_variable:
            repayment_variable = st.number_input(
                "Repayment override (" + repayment_cycle + "): ",
                0.0,
                10000.0,
                1883.17,
                50.0,
                key="k2d",
            )

        toggle_interest_variable = st.toggle("Override interest rate", False, key="k2e")

        if toggle_interest_variable:
            interest_variable = st.number_input(
                "Interest rate override: ", 0.1, 15.0, 6.14, key="k2f"
            )

        toggle_offset = st.toggle("Override offset", False, key="k2g")

        if toggle_offset:
            balance_offset = st.number_input(
                "Offset overide: ", 0, 300000, 100000, 1000, key="k2h"
            )

    st.write("Balance: " + str(balance_variable))
    st.write("Repayment (" + repayment_cycle + "): " + str(repayment_variable))

    if repayment_cycle == "fortnightly":
        st.write("Repayment (monthly): " + str(repayment_variable / 14 * (365 / 12)))

    st.write("Interest: " + str(interest_variable))
    st.write("Offset: " + str(balance_offset))

    with st.expander("Theoretical plan (for information only, not used)"):
        years_planner_variable = st.number_input("Years", 1, 40, 25, 1, key="k2i")

        planner_variable = home_loan_planner.HomeLoanPlanner(
            "Fixed",
            N=years_planner_variable,
            k=(365 / 14) if repayment_cycle == "fortnightly" else 12,
            P=balance_variable - balance_offset,
            R0=interest_variable / 100,
        )

        st.write(
            "Repayment ("
            + repayment_cycle
            + "), for identical repayment and interest cycles: "
            + str(planner_variable.c0)
        )

    extra_slider_variable = st.slider(
        "Extra-Repayment (monthly): ", 0, 10000, 3000, 500, key="k2j"
    )

    repayment_extra_variable = extra_slider_variable
    if repayment_cycle == "fortnightly":
        repayment_extra_variable = repayment_extra_variable / (365 / 12) * 14
        st.write("Extra-Repayment (fortnightly): " + str(repayment_extra_variable))

    df_schedule_variable = home_loan_simulator.simulate(
        balance_variable,
        balance_offset,
        interest_variable,
        14 if interest_cycle == "fortnightly" else (365 / 12),
        repayment_variable + repayment_extra_variable,
        14 if repayment_cycle == "fortnightly" else (365 / 12),
        simulation_start,
    )

    df_schedule_variable_wo_extra = home_loan_simulator.simulate(
        balance_variable,
        balance_offset,
        interest_variable,
        14 if interest_cycle == "fortnightly" else (365 / 12),
        repayment_variable,
        14 if repayment_cycle == "fortnightly" else (365 / 12),
        simulation_start,
    )

    st.write(df_schedule_variable)

    total_years_variable = df_schedule_variable.iloc[-1]["Years"]
    total_repayments_variable = df_schedule_variable["Repayment"].sum()
    total_interest_variable = df_schedule_variable["Interest"].sum()

    st.write("Years to go: " + str(total_years_variable))
    st.write("Total repayments to go: " + str(total_repayments_variable))
    st.write(
        "Total interest to go: "
        + str(total_interest_variable)
        + " ("
        + str(100 * total_interest_variable / total_repayments_variable)
        + "%)"
    )

    end_of_fixed_loan_balance = df_schedule_variable[
        df_schedule_variable["Date"] >= fixed_loan_end
    ]

    if len(end_of_fixed_loan_balance) > 0:
        end_of_fixed_loan_balance = end_of_fixed_loan_balance.iloc[0]["Principal"]
        st.write(
            "Balance at end of fixed loan ("
            + str(fixed_loan_end)
            + "): "
            + str(end_of_fixed_loan_balance)
        )
    else:
        st.write("Principal reached zero before end of fixed loan.")

    principal_smaller_offset = df_schedule_variable[
        df_schedule_variable["Principal"] <= balance_offset
    ]

    if len(principal_smaller_offset) > 0:
        principal_smaller_offset = principal_smaller_offset.iloc[0]
        st.write(
            "Date when principal smaller than offset for the first time: "
            + str(principal_smaller_offset["Date"])
        )

    fig1 = px.line(df_schedule_variable, x="Date", y="Principal")
    fig1.add_trace(
        px.line(df_schedule_variable_wo_extra, x="Date", y="Principal").data[0]
    )
    fig1.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
    fig1.update_yaxes(title_text="Principal")

    st.plotly_chart(fig1)

    interest_plot_variable = pd.DataFrame(df_schedule_variable)
    interest_plot_variable = interest_plot_variable[
        interest_plot_variable["Interest"] > 0
    ]

    interest_plot_variable_wo_extra = pd.DataFrame(df_schedule_variable_wo_extra)
    interest_plot_variable_wo_extra = interest_plot_variable_wo_extra[
        interest_plot_variable_wo_extra["Interest"] > 0
    ]

    fig2 = px.line(interest_plot_variable, x="Years", y="Interest")
    fig2.add_trace(
        px.line(interest_plot_variable_wo_extra, x="Years", y="Interest").data[0]
    )
    fig2.update_xaxes(title_text="Years")
    fig2.update_yaxes(title_text="Interest")

    st.plotly_chart(fig2)

# total

st.write("### Total")

total_wo_extra = repayment_fixed + repayment_variable
total_extra = repayment_extra_fixed + repayment_extra_variable

if repayment_cycle == "fortnightly":
    total_wo_extra = total_wo_extra / 14 * (365 / 12)
    total_extra = total_extra / 14 * (365 / 12)

total = total_wo_extra + total_extra

st.write("Total base payment (monthly): " + str(total_wo_extra))
st.write("Total extra payment (monthly): " + str(total_extra))
st.write("Total payment (monthly): " + str(total))
