import pandas as pd
import plotly.express as px
import streamlit as st
import account_reader
import account_interpreter
import home_loan_simulator
import home_loan_planner
from datetime import timedelta
import zipfile
import os
import shutil

# config

loan_start = pd.to_datetime("2024-10-16")
fixed_loan_end = loan_start + timedelta(days=365 * 5)

# setup

st.set_page_config(layout="wide")
st.title("Home Loan")

# load files

st.write("## Data")

browser_file = st.file_uploader("Upload account statements")

if browser_file is not None:
    data_folder = "external_data"
    if os.path.isdir(data_folder):
        shutil.rmtree(data_folder)
    with zipfile.ZipFile(browser_file, "r") as zip_file:
        zip_file.extractall(data_folder)
    st.write("Using uploaded account statements.")
else:
    data_folder = "internal_data"
    if not os.path.isdir(data_folder):
        st.write(
            "No internal account statements available, please upload account statements instead."
        )
        st.stop()
    else:
        st.write("Using internal account statements because none were uploaded.")

# get data

df_in = account_reader.get_dataframe(data_folder, date_from=loan_start)
df_in = account_interpreter.add_interest_information(df_in)

# assuming that the last interest or repayment event is the start of the simulation
simulation_start = df_in[
    ((df_in["AccountName"] == "Fixed") | (df_in["AccountName"] == "Variable"))
    & ((df_in["Label"] == "Interest") | (df_in["Label"] == "Repayment"))
]["DateSeries"].iloc[-1]

# Retrospective

st.write("## Retrospective")

st.write(
    "Data shown in this section uses the account statements and displays information about the past only."
)

# - Transactions

st.write("### Transactions")

st.write("Transactions to and from the accounts: Fixed, Variable, Offset")

with st.expander("View transactions"):

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

    st.dataframe(
        df_table.style.format(
            {
                "Credit": "${:,.0f}",
                "Debit": "${:,.0f}",
                "Balance": "${:,.0f}",
                "ApproxInterest": "{:,.3f}%",
                "InterestPeriod": lambda x: (
                    str(x.days + (x.seconds / (60 * 60 * 24))) + " days"
                    if not pd.isnull(x)
                    else ""
                ),
                "DateSeries": lambda x: x.strftime("%d/%m/%Y"),
            }
        )
    )

# - Balance over time

st.write("### Balance over time")

st.write("Accounts from beginning of loan till now.")

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

fig = px.line(
    df_plot, x="DateSeries", y="Balance", color="AccountName", symbol="AccountName"
)
fig.update_layout(title={"text": "Balance over time", "x": 0.5, "xanchor": "center"})
fig.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
fig.update_yaxes(title_text="Balance ($)")

st.plotly_chart(fig)

# - Change of balance over time

st.write("### Change of balance over time")

st.write("Accounts from beginning of loan till now.")

col1, col2 = st.columns(2)

with col1:
    st.write("#### Fixed")

    df_change = account_interpreter.get_change_overt_time(df_in, "Fixed", loan_start)

    df_change = account_interpreter.add_interpolated_value(
        df_change,
        "Interest",
        "Change",
        timespan_search=timedelta(days=35),
        timespan_include=timedelta(days=20),
        timespane_normalize=timedelta(days=365 / 12),
        drop_original=False,
        is_first_call=True,
    )

    df_change = account_interpreter.add_interpolated_value(
        df_change,
        "Repayment",
        "Change",
        timespan_search=timedelta(days=20),
        timespan_include=timedelta(days=20),
        timespane_normalize=timedelta(days=365 / 12),
        drop_original=False,
    )

    fig = px.line(
        df_change[df_change["interpolated"] == False],
        x="DateSeries",
        y=["Change"],
        color="Label",
        symbol="Label",
    )
    fig.update_layout(
        title={"text": "Raw change / Fixed", "x": 0.5, "xanchor": "center"}
    )
    fig.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
    fig.update_yaxes(title_text="Change ($)")

    st.plotly_chart(fig, key="p1")

    fig = px.line(
        df_change[df_change["interpolated"] == True],
        x="DateSeries",
        y=["Change"],
        color="Label",
        symbol="Label",
    )
    fig.update_layout(
        title={
            "text": "Interpolated change (monthly) / Fixed",
            "x": 0.5,
            "xanchor": "center",
        }
    )
    fig.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
    fig.update_yaxes(title_text="Change ($)")

    st.plotly_chart(fig, key="p2")

with col2:
    st.write("#### Variable")

    df_change = account_interpreter.get_change_overt_time(df_in, "Variable", loan_start)

    df_change = account_interpreter.add_interpolated_value(
        df_change,
        "Interest",
        "Change",
        timespan_search=timedelta(days=35),
        timespan_include=timedelta(days=20),
        timespane_normalize=timedelta(days=365 / 12),
        drop_original=False,
        is_first_call=True,
    )

    df_change = account_interpreter.add_interpolated_value(
        df_change,
        "Repayment",
        "Change",
        timespan_search=timedelta(days=20),
        timespan_include=timedelta(days=20),
        timespane_normalize=timedelta(days=365 / 12),
        drop_original=False,
    )

    df_change = account_interpreter.add_interpolated_value(
        df_change,
        "Extrarepayment",
        "Change",
        timespan_search=timedelta(days=35),
        timespan_include=timedelta(days=20),
        timespane_normalize=timedelta(days=365 / 12),
        drop_original=False,
    )

    fig = px.line(
        df_change[df_change["interpolated"] == False],
        x="DateSeries",
        y=["Change"],
        color="Label",
        symbol="Label",
    )
    fig.update_layout(
        title={"text": "Raw change / Variable", "x": 0.5, "xanchor": "center"}
    )
    fig.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
    fig.update_yaxes(title_text="Change ($)")

    st.plotly_chart(fig, key="p3")

    fig = px.line(
        df_change[df_change["interpolated"] == True],
        x="DateSeries",
        y=["Change"],
        color="Label",
        symbol="Label",
    )
    fig.update_layout(
        title={
            "text": "Interpolated change (monthly) / Variable",
            "x": 0.5,
            "xanchor": "center",
        }
    )
    fig.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
    fig.update_yaxes(title_text="Change ($)")

    st.plotly_chart(fig, key="p4")

# Prospective

st.write("## Prospective")

st.write(
    "Data shown in this section uses the account statements to extract balances, base repayments and interest rates. It then projects the accounts into the future, based on extra repayments adjustable by the user."
)

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

_, col2, _ = st.columns(3)

with col2:

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

    # - Fixed

    st.write("#### Fixed")

    with st.expander("Override variables"):

        toggle_balance_fixed = st.toggle("Override balance", False, key="k1a")

        if toggle_balance_fixed:
            balance_fixed = st.number_input(
                "Balance override ($)", 0, 2000000, 625000, 1000, key="k1b"
            )

        toggle_repayment_fixed = st.toggle("Override base repayment", False, key="k1c")

        if toggle_repayment_fixed:
            repayment_fixed = st.number_input(
                ":orange[Base repayment override (" + repayment_cycle + ", $)]",
                0.0,
                10000.0,
                1812.84,
                50.0,
                key="k1d",
            )

        toggle_interest_fixed = st.toggle("Override interest rate", False, key="k1e")

        if toggle_interest_fixed:
            interest_fixed = st.number_input(
                ":red[Interest rate override (%)]", 0.1, 15.0, 5.74, key="k1f"
            )

    st.write("Balance: " + f"${balance_fixed:,.0f}")
    st.write(
        ":orange[Base repayment ("
        + repayment_cycle
        + "): "
        + f"${repayment_fixed:,.0f}]"
    )

    if repayment_cycle == "fortnightly":
        st.write(
            ":orange[Base repayment (monthly): "
            + f"${(repayment_fixed / 14 * (365 / 12)):,.0f}]"
        )

    st.write(":red[Interest: " + f"{interest_fixed:.3f}%]")
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
            + f"${planner_fixed.c0:,.0f}"
        )

    extra_slider_fixed = st.slider(
        ":green[Extra repayment (monthly), limited to \\$10000 yearly, i.e. \\$800 monthly]",
        0,
        800,
        800,
        200,
        key="k1i",
    )

    repayment_extra_fixed = extra_slider_fixed
    if repayment_cycle == "fortnightly":
        repayment_extra_fixed = repayment_extra_fixed / (365 / 12) * 14
        st.write(
            ":green[Extra repayment (fortnightly): " + f"${repayment_extra_fixed:,.0f}]"
        )

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

    with st.expander("View payment schedule"):

        st.write(
            df_schedule_fixed.style.format(
                {
                    "Months": "{:,.2f}",
                    "Years": "{:,.2f}",
                    "Date": lambda x: x.strftime("%d/%m/%Y"),
                    "Repayment": "${:,.0f}",
                    "Interest": "${:,.0f}",
                    "Principal": "${:,.0f}",
                }
            )
        )

    total_years_fixed = df_schedule_fixed.iloc[-1]["Years"]
    total_repayments_fixed = df_schedule_fixed["Repayment"].sum()
    total_interest_fixed = df_schedule_fixed["Interest"].sum()

    st.write("Years to go: " + f"{total_years_fixed:.2f}")
    st.write(":blue[Total repayment to go: " + f"${total_repayments_fixed:,.0f}]")
    st.write(
        ":red[Interest to go: "
        + f"${total_interest_fixed:,.0f}"
        + " ("
        + f"{(100 * total_interest_fixed / total_repayments_fixed):.1f}%"
        + ")]"
    )

    end_of_fixed_loan_balance = df_schedule_fixed[
        df_schedule_fixed["Date"] >= fixed_loan_end
    ]

    if len(end_of_fixed_loan_balance) > 0:
        end_of_fixed_loan_balance = end_of_fixed_loan_balance.iloc[0]["Principal"]
        st.write(
            "Fixed loan balance at end of fixed loan term ("
            + fixed_loan_end.strftime("%d/%m/%Y")
            + "): "
            + f"${end_of_fixed_loan_balance:,.0f}"
        )
    else:
        st.write("Principal reached zero before end of fixed loan.")

    st.write(".")

    df_schedule_fixed["Schedule"] = "Fast"
    df_schedule_fixed_wo_extra["Schedule"] = "Slow"
    df_schedule_fixed_merged = pd.concat(
        [df_schedule_fixed, df_schedule_fixed_wo_extra]
    )

    fig1 = px.line(df_schedule_fixed_merged, x="Date", y="Principal", color="Schedule")
    fig1.update_layout(
        title={"text": "Principal / Fixed", "x": 0.5, "xanchor": "center"}
    )
    fig1.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
    fig1.update_yaxes(title_text="Principal ($)")

    st.plotly_chart(fig1)

    interest_plot_fixed = pd.DataFrame(df_schedule_fixed)
    interest_plot_fixed = interest_plot_fixed[interest_plot_fixed["Interest"] > 0]

    interest_plot_fixed_wo_extra = pd.DataFrame(df_schedule_fixed_wo_extra)
    interest_plot_fixed_wo_extra = interest_plot_fixed_wo_extra[
        interest_plot_fixed_wo_extra["Interest"] > 0
    ]

    interest_plot_fixed["Schedule"] = "Fast"
    interest_plot_fixed_wo_extra["Schedule"] = "Slow"
    interest_plot_fixed_merged = pd.concat(
        [interest_plot_fixed, interest_plot_fixed_wo_extra]
    )

    fig2 = px.line(
        interest_plot_fixed_merged, x="Years", y="Interest", color="Schedule"
    )
    fig2.update_layout(
        title={"text": "Interest / Fixed", "x": 0.5, "xanchor": "center"}
    )
    fig2.update_xaxes(title_text="Years")
    fig2.update_yaxes(title_text="Interest ($)")

    st.plotly_chart(fig2)

with col2:

    # - Variable

    st.write("#### Variable")

    with st.expander("Override variables"):

        toggle_balance_variable = st.toggle("Override balance", False, key="k2a")

        if toggle_balance_variable:
            balance_variable = st.number_input(
                "Balance override ($): ", 0, 2000000, 625000, 1000, key="k2b"
            )

        toggle_repayment_variable = st.toggle(
            "Override base repayment", False, key="k2c"
        )

        if toggle_repayment_variable:
            repayment_variable = st.number_input(
                ":orange[Base repayment override (" + repayment_cycle + ", $)]",
                0.0,
                10000.0,
                1883.17,
                50.0,
                key="k2d",
            )

        toggle_interest_variable = st.toggle("Override interest rate", False, key="k2e")

        if toggle_interest_variable:
            interest_variable = st.number_input(
                ":red[Interest rate override (%)]", 0.1, 15.0, 6.14, key="k2f"
            )

        toggle_offset = st.toggle("Override offset", False, key="k2g")

        if toggle_offset:
            balance_offset = st.number_input(
                "Offset overide ($)", 0, 300000, 100000, 1000, key="k2h"
            )

    st.write("Balance: " + f"${balance_variable:,.0f}")
    st.write(
        ":orange[Base repayment ("
        + repayment_cycle
        + "): "
        + f"${repayment_variable:,.0f}]"
    )

    if repayment_cycle == "fortnightly":
        st.write(
            ":orange[Base repayment (monthly): "
            + f"${(repayment_variable / 14 * (365 / 12)):,.0f}]"
        )

    st.write(":red[Interest: " + f"{interest_variable:.3f}%]")
    st.write("Offset: " + f"${balance_offset:,.0f}")

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
            + f"${planner_variable.c0:,.0f}"
        )

    extra_slider_variable = st.slider(
        ":green[Extra repayment (monthly)]", 0, 10000, 3000, 500, key="k2j"
    )

    repayment_extra_variable = extra_slider_variable
    if repayment_cycle == "fortnightly":
        repayment_extra_variable = repayment_extra_variable / (365 / 12) * 14
        st.write(
            ":green[Extra repayment (fortnightly): "
            + f"${repayment_extra_variable:,.0f}]"
        )

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

    with st.expander("View payment schedule"):

        st.write(
            df_schedule_variable.style.format(
                {
                    "Months": "{:,.2f}",
                    "Years": "{:,.2f}",
                    "Date": lambda x: x.strftime("%d/%m/%Y"),
                    "Repayment": "${:,.0f}",
                    "Interest": "${:,.0f}",
                    "Principal": "${:,.0f}",
                }
            )
        )

    total_years_variable = df_schedule_variable.iloc[-1]["Years"]
    total_repayments_variable = df_schedule_variable["Repayment"].sum()
    total_interest_variable = df_schedule_variable["Interest"].sum()

    st.write("Years to go: " + f"{total_years_variable:.2f}")
    st.write(":blue[Total repayment to go: " + f"${total_repayments_variable:,.2f}]")
    st.write(
        ":red[Interest to go: "
        + f"${total_interest_variable:,.0f}"
        + " ("
        + f"{(100 * total_interest_variable / total_repayments_variable):.1f}"
        + "%)]"
    )

    end_of_fixed_loan_balance = df_schedule_variable[
        df_schedule_variable["Date"] >= fixed_loan_end
    ]

    if len(end_of_fixed_loan_balance) > 0:
        end_of_fixed_loan_balance = end_of_fixed_loan_balance.iloc[0]["Principal"]
        st.write(
            "Variable loan balance at end of fixed loan term ("
            + fixed_loan_end.strftime("%d/%m/%Y")
            + "): "
            + f"${end_of_fixed_loan_balance:,.0f}"
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
            + principal_smaller_offset["Date"].strftime("%d/%m/%Y")
        )

    df_schedule_variable["Schedule"] = "Fast"
    df_schedule_variable_wo_extra["Schedule"] = "Slow"
    df_schedule_variable_merged = pd.concat(
        [df_schedule_variable, df_schedule_variable_wo_extra]
    )

    fig1 = px.line(
        df_schedule_variable_merged, x="Date", y="Principal", color="Schedule"
    )
    fig1.update_layout(
        title={"text": "Principal / Variable", "x": 0.5, "xanchor": "center"}
    )
    fig1.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
    fig1.update_yaxes(title_text="Principal ($)")

    st.plotly_chart(fig1)

    interest_plot_variable = pd.DataFrame(df_schedule_variable)
    interest_plot_variable = interest_plot_variable[
        interest_plot_variable["Interest"] > 0
    ]

    interest_plot_variable_wo_extra = pd.DataFrame(df_schedule_variable_wo_extra)
    interest_plot_variable_wo_extra = interest_plot_variable_wo_extra[
        interest_plot_variable_wo_extra["Interest"] > 0
    ]

    interest_plot_variable["Schedule"] = "Fast"
    interest_plot_variable_wo_extra["Schedule"] = "Slow"
    interest_plot_variable_merged = pd.concat(
        [interest_plot_variable, interest_plot_variable_wo_extra]
    )

    fig2 = px.line(
        interest_plot_variable_merged, x="Years", y="Interest", color="Schedule"
    )
    fig2.update_layout(
        title={"text": "Interest / Variable", "x": 0.5, "xanchor": "center"}
    )
    fig2.update_xaxes(title_text="Years")
    fig2.update_yaxes(title_text="Interest($)")

    st.plotly_chart(fig2)

# - total

_, col2, _ = st.columns(3)

with col2:

    st.write("### Fixed and Variable combined")

    total_wo_extra = repayment_fixed + repayment_variable
    total_extra = repayment_extra_fixed + repayment_extra_variable

    if repayment_cycle == "fortnightly":
        total_wo_extra = total_wo_extra / 14 * (365 / 12)
        total_extra = total_extra / 14 * (365 / 12)

    total = total_wo_extra + total_extra

    st.write(":orange[Base repayment (monthly): " + f"${total_wo_extra:,.0f}]")
    st.write(":green[Extra repayment (monthly): " + f"${total_extra:,.0f}]")
    st.write(":blue[Total repayment (monthly): " + f"${total:,.0f}]")

    st.write(
        ":blue[Total repayment to go: "
        + f"${(total_repayments_fixed + total_repayments_variable):,.0f}]"
    )
    st.write(
        ":red[Interest to go: "
        + f"${(total_interest_fixed+total_interest_variable):,.0f}]"
    )
