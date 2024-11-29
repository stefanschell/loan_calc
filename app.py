import pandas as pd
import plotly.express as px
import streamlit as st
import account_reader
import account_interpreter
import home_loan_simulator
from datetime import timedelta

# get data

loan_start = pd.to_datetime("2024-09-16")
loan_end = loan_start + timedelta(days=365 * 5)

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

col1, col2 = st.columns(2)

with col1:

    # Fixed

    st.write("### Fixed")

    st.write("Balance: " + str(balance_fixed))
    st.write("Repayment (every 14 days): " + str(repayment_fixed))

    with st.expander("Override interest rate"):

        toggle_interest_fixed = st.toggle("Override interest rate", False, key="k1a")

        if toggle_interest_fixed:
            interest_fixed = float(
                st.number_input("Interest rate override: ", 0.0, 15.0, 5.74, key="k1b")
            )

    st.write("Interest: " + str(interest_fixed))
    st.write("Offset: None")

    extra_slider_fixed = st.slider(
        "Extra-Repayment (every 30 days), limited to AUD 10000 per year, i.e. AUD 800 every 30 days: ",
        0,
        800,
        800,
        200,
        key="k1c",
    )

    repayment_extra_fixed = extra_slider_fixed / 30 * 14

    st.write("Extra-Repayment (every 14 days) " + str(repayment_extra_fixed))

    df_schedule_fixed = home_loan_simulator.simulate(
        balance_fixed,
        0,
        interest_fixed,
        30,
        repayment_fixed + repayment_extra_fixed,
        14,
        simulation_start,
    )

    df_schedule_fixed_wo_extra = home_loan_simulator.simulate(
        balance_fixed,
        0,
        interest_fixed,
        30,
        repayment_fixed,
        14,
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

    end_of_fixed_loan_balance = df_schedule_fixed[df_schedule_fixed["Date"] >= loan_end]

    if len(end_of_fixed_loan_balance) > 0:
        end_of_fixed_loan_balance = end_of_fixed_loan_balance.iloc[0]["Principal"]
        st.write(
            "Balance at end of fixed loan ("
            + str(loan_end)
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

    st.write("Balance: " + str(balance_variable))
    st.write("Repayment (every 14 days) " + str(repayment_variable))

    with st.expander("Override interest and/or offset"):

        toggle_interest_variable = st.toggle("Override interest rate", False, key="k2a")

        if toggle_interest_variable:
            interest_variable = float(
                st.number_input("Interest rate override: ", 0.0, 15.0, 6.14, key="k2b")
            )

        toggle_offset = st.toggle("Override offset", False, key="k2c")

        if toggle_offset:
            balance_offset = st.number_input(
                "Offset overide: ", 0, 300000, 100000, 1000, key="k2d"
            )

    st.write("Interest: " + str(interest_variable))
    st.write("Offset: " + str(balance_offset))

    extra_slider_variable = st.slider(
        "Extra-Repayment (every 30 days): ", 0, 10000, 3000, 500, key="k2e"
    )

    repayment_extra_variable = extra_slider_variable / 30 * 14

    st.write("Extra-Repayment (every 14 days) " + str(repayment_extra_variable))

    df_schedule_variable = home_loan_simulator.simulate(
        balance_variable,
        balance_offset,
        interest_variable,
        30,
        repayment_variable + repayment_extra_variable,
        14,
        simulation_start,
    )

    df_schedule_variable_wo_extra = home_loan_simulator.simulate(
        balance_variable,
        balance_offset,
        interest_variable,
        30,
        repayment_variable,
        14,
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
        df_schedule_variable["Date"] >= loan_end
    ]

    if len(end_of_fixed_loan_balance) > 0:
        end_of_fixed_loan_balance = end_of_fixed_loan_balance.iloc[0]["Principal"]
        st.write(
            "Balance at end of fixed loan ("
            + str(loan_end)
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

total_wo_extra = (30 / 14) * (repayment_fixed + repayment_variable)
total_extra = (30 / 14) * (repayment_extra_fixed + repayment_extra_variable)
total = total_wo_extra + total_extra

st.write("Total base payment (every 30 days): " + str(total_wo_extra))
st.write("Total extra payment (every 30 days): " + str(total_extra))
st.write("Total payment (every 30 days): " + str(total))
