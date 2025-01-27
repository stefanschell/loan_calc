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
fixed_loan_length = timedelta(days=365 * 5)

fixed_loan_end = loan_start + fixed_loan_length

# helper

transaction_format = {
    "Credit": "${:,.0f}",
    "Debit": "${:,.0f}",
    "Balance": "${:,.0f}",
    "ApproxInterest": "{:,.3f}%",
    "InterestPeriod": lambda x: (
        str(x.days + (x.seconds / (60 * 60 * 24))) + " days" if not pd.isnull(x) else ""
    ),
    "DateSeries": lambda x: x.strftime("%d/%m/%Y"),
}

schedule_format = {
    "Date": lambda x: x.strftime("%d/%m/%Y"),
    "LoanYears": "{:,.2f}",
    "LoanDuration": lambda x: (
        str(x.years) + "y-" + str(x.months) + "m-" + str(x.days) + "d"
    ),
    "ScheduleYears": "{:,.2f}",
    "ScheduleDuration": lambda x: (
        str(x.years) + "y-" + str(x.months) + "m-" + str(x.days) + "d"
    ),
    "Interest": "${:,.0f}",
    "Redraw": "${:,.0f}",
    "Repayment": "${:,.0f}",
    "ExtraCostOrWin": "${:,.0f}",
    "Principal": "${:,.0f}",
}

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

# Retrospective

st.write("## Retrospective")

st.write(
    "Data shown in this section uses the account statements and displays information about the past only."
)

with st.expander("Transactions"):

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

    st.dataframe(df_table.style.format(transaction_format))

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

df_balance_total_fitted = account_interpreter.fit_balance(df_balance_total)

with st.expander("Balance over time"):

    df_plot = pd.concat(
        [
            df_balance_fixed,
            df_balance_variable,
            df_balance_offset,
            df_balance_total,
            df_balance_total_fitted,
        ]
    )

    fig = px.line(
        df_plot, x="DateSeries", y="Balance", color="AccountName", symbol="AccountName"
    )
    fig.update_layout(
        title={"text": "Balance over time", "x": 0.5, "xanchor": "center"}
    )
    fig.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
    fig.update_yaxes(title_text="Balance ($)")

    st.plotly_chart(fig)

df_change_fixed = account_interpreter.get_change_over_time(
    df_in,
    "Fixed",
    exclude_up_to_date=loan_start,  # excludes initial transactions on day of settlement
)

df_change_fixed = account_interpreter.add_interpolated_value(
    df_change_fixed,
    "Interest",
    "Change",
    timespan_search=timedelta(days=35),
    timespan_include=timedelta(days=20),
    timespane_normalize=timedelta(days=365 / 12),
    drop_original=False,
    is_first_call=True,
)

df_change_fixed = account_interpreter.add_interpolated_value(
    df_change_fixed,
    "Repayment",
    "Change",
    timespan_search=timedelta(days=20),
    timespan_include=timedelta(days=20),
    timespane_normalize=timedelta(days=365 / 12),
    drop_original=False,
)

df_change_variable = account_interpreter.get_change_over_time(
    df_in,
    "Variable",
    exclude_up_to_date=loan_start,  # excludes initial transactions on day of settlement
)

df_change_variable = account_interpreter.add_interpolated_value(
    df_change_variable,
    "Interest",
    "Change",
    timespan_search=timedelta(days=35),
    timespan_include=timedelta(days=20),
    timespane_normalize=timedelta(days=365 / 12),
    drop_original=False,
    is_first_call=True,
)

df_change_variable = account_interpreter.add_interpolated_value(
    df_change_variable,
    "Repayment",
    "Change",
    timespan_search=timedelta(days=20),
    timespan_include=timedelta(days=20),
    timespane_normalize=timedelta(days=365 / 12),
    drop_original=False,
)

df_change_variable = account_interpreter.add_interpolated_value(
    df_change_variable,
    "Extrarepayment",
    "Change",
    timespan_search=timedelta(days=35),
    timespan_include=timedelta(days=20),
    timespane_normalize=timedelta(days=365 / 12),
    drop_original=False,
)


total_interest_so_far_fixed = df_change_fixed[
    (df_change_fixed["Label"] == "Interest")
    & (df_change_fixed["interpolated"] == False)
]["Change"].sum()

base_repayment_so_far_fixed = df_change_fixed[
    (df_change_fixed["Label"] == "Repayment")
    & (df_change_fixed["interpolated"] == False)
]["Change"].sum()

extra_repayment_so_far_fixed = df_change_fixed[
    (df_change_fixed["Label"] == "Extrarepayment")
    & (df_change_fixed["interpolated"] == False)
]["Change"].sum()

total_repayments_so_far_fixed = (
    base_repayment_so_far_fixed + extra_repayment_so_far_fixed
)

total_interest_so_far_variable = df_change_variable[
    (df_change_variable["Label"] == "Interest")
    & (df_change_variable["interpolated"] == False)
]["Change"].sum()

base_repayment_so_far_variable = df_change_variable[
    (df_change_variable["Label"] == "Repayment")
    & (df_change_variable["interpolated"] == False)
]["Change"].sum()

extra_repayment_so_far_variable = df_change_variable[
    (df_change_variable["Label"] == "Extrarepayment")
    & (df_change_variable["interpolated"] == False)
]["Change"].sum()

total_repayments_so_far_variable = (
    base_repayment_so_far_variable + extra_repayment_so_far_variable
)

total_interest_so_far = total_interest_so_far_fixed + total_interest_so_far_variable

base_repayment_so_far = base_repayment_so_far_fixed + base_repayment_so_far_variable

extra_repayment_so_far = extra_repayment_so_far_fixed + extra_repayment_so_far_variable

total_repayments_so_far = (
    total_repayments_so_far_fixed + total_repayments_so_far_variable
)

col1, col2 = st.columns(2)

with col1:
    st.write("#### Fixed")

    with st.expander("Change of balance over time"):

        fig = px.line(
            df_change_fixed[df_change_fixed["interpolated"] == False],
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
            df_change_fixed[df_change_fixed["interpolated"] == True],
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

    with st.expander("Change of balance over time"):

        fig = px.line(
            df_change_variable[df_change_variable["interpolated"] == False],
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
            df_change_variable[df_change_variable["interpolated"] == True],
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

    prev_extrarepayment_interpolated = df_change_variable[
        (df_change_variable["interpolated"] == True)
        & (df_change_variable["Label"] == "Extrarepayment")
    ].iloc[-1]["Change"]

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.write("Extra repayment data extracted from variable loan account only.")

with col2:
    st.write(
        "Latest extracted extra repayment (monthly): "
        + f"${prev_extrarepayment_interpolated:,.0f}"
    )

_, col2, _ = st.columns(3)

with col2:

    st.write("Thus, we assume the following default future extra repayments:")

    round_to_hundred = lambda x: int(round(x / 100) * 100)
    default_extrarepayment_fixed = round_to_hundred(800)
    default_extrarepayment_variable = round_to_hundred(
        prev_extrarepayment_interpolated - default_extrarepayment_fixed
    )

col1, col2 = st.columns(2)

with col1:
    st.write(
        ":green[Fixed loan extra repayment (monthly): "
        + f"${round(default_extrarepayment_fixed / 100) * 100:,.0f}]"
    )

with col2:
    st.write(
        ":green[Variable loan extra repayment (monthly): "
        + f"${round(default_extrarepayment_variable / 100) * 100:,.0f}]"
    )

st.divider()

col1, col2 = st.columns(2)

with col1:

    st.write(":red[Interest so far: " + f"${total_interest_so_far_fixed:,.0f}]")
    st.write(
        ":orange[Base repayment so far: " + f"${base_repayment_so_far_fixed:,.0f}]"
    )
    st.write(
        ":green[Extra repayment so far: " + f"${extra_repayment_so_far_fixed:,.0f}]"
    )
    st.write(
        ":blue[Total repayment so far: " + f"${total_repayments_so_far_fixed:,.0f}]"
    )

with col2:

    st.write(":red[Interest so far: " + f"${total_interest_so_far_variable:,.0f}]")
    st.write(
        ":orange[Base repayment so far: " + f"${base_repayment_so_far_variable:,.0f}]"
    )
    st.write(
        ":green[Extra repayment so far: " + f"${extra_repayment_so_far_variable:,.0f}]"
    )
    st.write(
        ":blue[Total repayment so far: " + f"${total_repayments_so_far_variable:,.0f}]"
    )

_, col2, _ = st.columns(3)

with col2:
    st.write("#### Fixed & Variable")
    st.write(":red[Interest so far: " + f"${total_interest_so_far:,.0f}]")
    st.write(":orange[Base repayment so far: " + f"${base_repayment_so_far:,.0f}]")
    st.write(":green[Extra repayment so far: " + f"${extra_repayment_so_far:,.0f}]")
    st.write(":blue[Total repayment so far: " + f"${total_repayments_so_far:,.0f}]")

# Prospective

st.write("## Prospective")

st.write(
    "Data shown in this section uses the account statements to extract balances, base repayments, extra repayments and interest rates. It then projects the accounts into the future. For this extra repayments can be adjusted by the user."
)

prev_interest_date = df_in[df_in["Label"] == "Interest"]["DateSeries"].iloc[-1]
prev_repayment_date = df_in[df_in["Label"] == "Repayment"]["DateSeries"].iloc[-1]
schedule_start = max(prev_interest_date, prev_repayment_date)

years_so_far = (schedule_start - loan_start).days / 365

balance_fixed = account_interpreter.find_balance(df_balance_fixed, schedule_start)
repayment_fixed = df_in[
    (df_in["AccountName"] == "Fixed") & (df_in["Label"] == "Repayment")
].iloc[-1]["Credit"]
interest_fixed = df_in[
    (df_in["AccountName"] == "Fixed") & (df_in["Label"] == "Interest")
].iloc[-1]["ApproxInterest"]

balance_variable = account_interpreter.find_balance(df_balance_variable, schedule_start)
repayment_variable = df_in[
    (df_in["AccountName"] == "Variable") & (df_in["Label"] == "Repayment")
].iloc[-1]["Credit"]
interest_variable = df_in[
    (df_in["AccountName"] == "Variable") & (df_in["Label"] == "Interest")
].iloc[-1]["ApproxInterest"]

balance_offset = account_interpreter.find_balance(df_balance_offset, schedule_start)

repayment_cycle = home_loan_simulator.Cycle.FORTNIGHTLY
interest_cycle = home_loan_simulator.Cycle.MONTHLY_END_OF_MONTH

_, col2, _ = st.columns(3)

with col2:
    st.write("##### Settings")

    with st.expander("Override settings"):

        restart_loan_today = st.toggle("Restart loan today", False)

        if restart_loan_today:
            loan_start = pd.to_datetime("today")
            fixed_loan_end = loan_start + fixed_loan_length
            schedule_start = loan_start
            prev_interest_date = schedule_start
            prev_repayment_date = schedule_start

        show_so_far_information = not st.toggle(
            "Hide 'so far' information", False, disabled=restart_loan_today
        )

        if restart_loan_today:
            show_so_far_information = False

        show_schedules_wo_extra = st.toggle("Show schedules wo/ extra repayment", False)

        show_alternative_scheduless = st.toggle(
            "Show schedules for save now, spend now and invest now", False
        )

    st.divider()
    st.write("##### Dates")

    st.write("Start of loan:", loan_start.strftime("%d/%m/%Y"))
    st.write("Last retrospective interest:", prev_interest_date.strftime("%d/%m/%Y"))
    st.write("Last retrospective repayment:", prev_repayment_date.strftime("%d/%m/%Y"))
    st.write("Start of schedule:", schedule_start.strftime("%d/%m/%Y"))
    st.write("End of fixed loan term:", fixed_loan_end.strftime("%d/%m/%Y"))

    st.divider()
    st.write("##### Interest and repayment cycle")

    with st.expander("Override variables"):
        allowed_cycles = [
            item
            for item in home_loan_simulator.Cycle
            if item != home_loan_simulator.Cycle.YEARLY
        ]

        interest_cycle = st.selectbox(
            "Interest cycle override",
            allowed_cycles,
            index=3,
            format_func=home_loan_simulator.Cycle.complex_str,
        )

        repayment_cycle = st.selectbox(
            "Repayment cycle override",
            allowed_cycles,
            index=0,
            format_func=home_loan_simulator.Cycle.complex_str,
        )

    st.write("Interest cycle: " + interest_cycle.complex_str())
    st.write("Repayment cycle: " + repayment_cycle.complex_str())

    st.divider()
    st.write("##### Save now, spend now and invest now")

    show_save_spend_invest_information = not st.toggle(
        "Hide 'save now', 'spend now', 'invest now' information", False
    )

    if show_save_spend_invest_information:
        with st.expander("Override variables"):

            st.write("Save now: one time saving of an additional amount of money")
            st.write("Spend now: one time spending of an additional amount of money")
            st.write(
                "Invest now: one time investment of a certain amount of money, then regular gain of money"
            )

            save_now_amount = st.number_input(
                "Save now amount override ($)",
                0,
                1000000,
                3000,
            )

            spend_now_amount = st.number_input(
                "Spend now amount override ($)",
                0,
                1000000,
                10000,
            )

            invest_now_cost_amount = st.number_input(
                "Invest now cost amount override ($)",
                0,
                1000000,
                5000,
            )

            invest_now_win_amount = st.number_input(
                "Invest now win amount override ($)",
                0,
                1000000,
                75,
            )

            invest_now_win_cycle = st.selectbox(
                "Invest now win cycle override",
                home_loan_simulator.Cycle,
                index=1,
                format_func=home_loan_simulator.Cycle.complex_str,
            )

        st.write("Save now amount: " + f"${save_now_amount:,.0f}")
        st.write("Spend now amount: " + f"${spend_now_amount:,.0f}")
        st.write("Invest now cost amount: " + f"${invest_now_cost_amount:,.0f}")
        st.write("Invest now win amount: " + f"${invest_now_win_amount:,.0f}")
        st.write("Invest now win cycle: " + invest_now_win_cycle.complex_str())
    else:
        save_now_amount = 0
        spend_now_amount = 0
        invest_now_cost_amount = None
        invest_now_win_amount = None
        invest_now_win_cycle = None

col1, col2 = st.columns(2)

with col1:

    # - Fixed

    st.write("#### Fixed")

    st.write("##### Config")

    with st.expander("Override variables"):

        toggle_balance_fixed = st.toggle("Override balance", False, key="k1a")

        if toggle_balance_fixed:
            balance_fixed = st.number_input(
                "Balance override ($)", 0, 2000000, 625000, 1000, key="k1b"
            )

        toggle_interest_fixed = st.toggle("Override interest rate", False, key="k1e")

        if toggle_interest_fixed:
            interest_fixed = st.number_input(
                ":red[Interest rate override (%)]", 0.1, 15.0, 5.74, key="k1f"
            )

        toggle_repayment_fixed = st.toggle("Override base repayment", False, key="k1c")

        if toggle_repayment_fixed:
            repayment_fixed = st.number_input(
                ":orange[Base repayment override ("
                + repayment_cycle.simple_str()
                + ", $)]",
                0.0,
                10000.0,
                1812.84,
                50.0,
                key="k1d",
            )

    st.write("Balance: " + f"${balance_fixed:,.0f}")

    st.write(":red[Interest: " + f"{interest_fixed:.3f}%]")

    st.write(
        ":orange[Base repayment ("
        + repayment_cycle.simple_str()
        + "): "
        + f"${repayment_fixed:,.0f}]"
    )

    if repayment_cycle.is_fortnightly():
        st.write(
            ":orange[Base repayment (monthly): "
            + f"${(repayment_fixed / 14 * (365 / 12)):,.0f}]"
        )

    st.write("Offset: None")

    with st.expander("Theoretical schedule (for information only, not used)"):
        years_planner_fixed = st.number_input("Years", 1, 40, 25, 1, key="k1g")

        planner_fixed = home_loan_planner.HomeLoanPlanner(
            "Fixed",
            N=years_planner_fixed,
            k=((365 / 14) if repayment_cycle.is_fortnightly() else 12),
            P=balance_fixed,
            R0=interest_fixed / 100,
        )

        st.write(
            "Repayment ("
            + repayment_cycle.simple_str()
            + "), for identical repayment and interest cycles: "
            + f"${planner_fixed.c0:,.0f}"
        )

    st.divider()
    st.write("##### Schedule")

    extra_slider_fixed = st.slider(
        ":green[Extra repayment (monthly), limited to \\$10000 yearly, i.e. \\$800 monthly]",
        0,
        800,
        default_extrarepayment_fixed,
        100,
        key="k1i",
    )

    repayment_extra_fixed = extra_slider_fixed
    if repayment_cycle.is_fortnightly():
        repayment_extra_fixed = repayment_extra_fixed / (365 / 12) * 14
        st.write(
            ":green[Extra repayment (fortnightly): " + f"${repayment_extra_fixed:,.0f}]"
        )

    repayment_total_fixed = repayment_fixed + repayment_extra_fixed

    st.write(
        ":blue[Total repayment ("
        + repayment_cycle.simple_str()
        + "): "
        + f"${repayment_total_fixed:,.0f}]"
    )

    if repayment_cycle.is_fortnightly():
        st.write(
            ":blue[Total repayment (monthly): "
            + f"${(repayment_total_fixed / 14 * (365 / 12)):,.0f}]"
        )

    df_schedule_fixed = home_loan_simulator.simulate(
        loan_start=loan_start,
        principal=balance_fixed,
        offset=0,
        schedule_start=schedule_start,
        interest_rate=interest_fixed,
        prev_interest_date=prev_interest_date,
        interest_cycle=interest_cycle,
        repayment=repayment_total_fixed,
        prev_repayment_date=prev_repayment_date,
        repayment_cycle=repayment_cycle,
        schedule_end=fixed_loan_end,
    )

    df_schedule_fixed_wo_extra = home_loan_simulator.simulate(
        loan_start=loan_start,
        principal=balance_fixed,
        offset=0,
        schedule_start=schedule_start,
        interest_rate=interest_fixed,
        prev_interest_date=prev_interest_date,
        interest_cycle=interest_cycle,
        repayment=repayment_fixed,
        prev_repayment_date=prev_repayment_date,
        repayment_cycle=repayment_cycle,
        schedule_end=fixed_loan_end,
    )

    with st.expander("Detailed schedule"):
        st.write(df_schedule_fixed.style.format(schedule_format))

    total_years_fixed = df_schedule_fixed.iloc[-1]["ScheduleYears"]
    total_repayments_fixed = df_schedule_fixed["Repayment"].sum()
    total_interest_fixed = df_schedule_fixed["Interest"].sum()

    interest_per_month_fixed = (
        df_schedule_fixed.iloc[0]["Principal"] * (interest_fixed / 100) / 12
    )

    st.write(
        ":red[Initial interest: "
        + f"\\${interest_per_month_fixed:,.0f}"
        + "/m = "
        + f"\\${interest_per_month_fixed * (12 / 365):,.0f}"
        + "/d = "
        + f"\\${interest_per_month_fixed * (12 / (365 * 24)):,.1f}"
        + "/h]"
    )

    if show_so_far_information:
        st.write("Time so far: " + f"{years_so_far:.2f} yrs")
    st.write("Time to go: " + f"{total_years_fixed:.2f} yrs")
    if show_so_far_information:
        st.write(
            "Time so far & to go: " + f"{(years_so_far + total_years_fixed):.2f} yrs"
        )

    if show_schedules_wo_extra:
        st.divider()
        st.write("##### Other schedules")

        with st.expander("Detailed schedule: w/o extra repayment"):
            st.write(df_schedule_fixed_wo_extra.style.format(schedule_format))

    st.divider()
    st.write("##### Sums")

    if show_so_far_information:
        st.write(":red[Interest so far: " + f"${total_interest_so_far_fixed:,.0f}]")
    st.write(
        ":red[Interest to go: "
        + f"${total_interest_fixed:,.0f}"
        + " ("
        + f"{(100 * total_interest_fixed / total_repayments_fixed):.1f}%"
        + ")]"
    )
    if show_so_far_information:
        st.write(
            ":red[Interest so far & to go: "
            + f"${total_interest_so_far_fixed + total_interest_fixed:,.0f}"
            + " ("
            + f"{(100 * (total_interest_so_far_fixed + total_interest_fixed) / (total_repayments_so_far_fixed + total_repayments_fixed)):.1f}%"
            + ")]"
        )
        st.write(
            ":blue[Total repayment so far: " + f"${total_repayments_so_far_fixed:,.0f}]"
        )
    st.write(":blue[Total repayment to go: " + f"${total_repayments_fixed:,.0f}]")
    if show_so_far_information:
        st.write(
            ":blue[Total repayment so far & to go: "
            + f"${total_repayments_so_far_fixed + total_repayments_fixed:,.0f}]"
        )

    end_of_fixed_loan_balance = df_schedule_fixed.iloc[-1]["Principal"]
    end_of_fixed_loan_balance_wo_extra = df_schedule_fixed_wo_extra.iloc[-1][
        "Principal"
    ]

    st.write("End of fixed loan term: " + fixed_loan_end.strftime("%d/%m/%Y"))

    st.write(
        "Balance at the end of fixed loan term: " + f"${end_of_fixed_loan_balance:,.0f}"
    )

    st.write("Afterwards the remaining balance is moved to the variable loan account.")

    df_schedule_fixed["Schedule"] = "default"
    df_schedule_fixed_wo_extra["Schedule"] = "wo/ extra repayment"
    df_schedule_fixed_merged = (
        pd.concat([df_schedule_fixed, df_schedule_fixed_wo_extra])
        if show_schedules_wo_extra
        else df_schedule_fixed
    )

    with st.expander("Principal over time"):

        fig1 = px.scatter(
            df_schedule_fixed_merged,
            x="Date",
            y="Principal",
            color="Schedule" if show_schedules_wo_extra else None,
        )
        fig1.update_layout(
            title={"text": "Principal / Fixed", "x": 0.5, "xanchor": "center"}
        )
        fig1.update_traces(marker=dict(size=3))
        fig1.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
        fig1.update_yaxes(title_text="Principal ($)")

        st.plotly_chart(fig1)

    interest_plot_fixed = pd.DataFrame(df_schedule_fixed)
    interest_plot_fixed = interest_plot_fixed[
        (interest_plot_fixed["Interest"] >= 0)
        & (interest_plot_fixed["Date"] > schedule_start)
    ]

    interest_plot_fixed_wo_extra = pd.DataFrame(df_schedule_fixed_wo_extra)
    interest_plot_fixed_wo_extra = interest_plot_fixed_wo_extra[
        (interest_plot_fixed_wo_extra["Interest"] >= 0)
        & (interest_plot_fixed_wo_extra["Date"] > schedule_start)
    ]

    interest_plot_fixed["Schedule"] = "default"
    interest_plot_fixed_wo_extra["Schedule"] = "wo/ extra repayment"
    interest_plot_fixed_merged = (
        pd.concat([interest_plot_fixed, interest_plot_fixed_wo_extra])
        if show_schedules_wo_extra
        else interest_plot_fixed
    )

    with st.expander("Interest over time"):
        fig2 = px.scatter(
            interest_plot_fixed_merged,
            x="ScheduleYears",
            y="Interest",
            color="Schedule" if show_schedules_wo_extra else None,
        )
        fig2.update_layout(
            title={"text": "Interest / Fixed", "x": 0.5, "xanchor": "center"}
        )
        fig2.update_traces(marker=dict(size=3))
        fig2.update_xaxes(title_text="ScheduleYears")
        fig2.update_yaxes(title_text="Interest ($, monthly)")

        st.plotly_chart(fig2)

    repayment_plot_fixed = pd.DataFrame(df_schedule_fixed)
    repayment_plot_fixed = repayment_plot_fixed[
        (repayment_plot_fixed["Repayment"] >= 0)
        & (repayment_plot_fixed["Date"] > schedule_start)
    ]

    repayment_plot_fixed_wo_extra = pd.DataFrame(df_schedule_fixed_wo_extra)
    repayment_plot_fixed_wo_extra = repayment_plot_fixed_wo_extra[
        (repayment_plot_fixed_wo_extra["Repayment"] >= 0)
        & (repayment_plot_fixed_wo_extra["Date"] > schedule_start)
    ]

    repayment_plot_fixed["Schedule"] = "default"
    repayment_plot_fixed_wo_extra["Schedule"] = "wo/ extra repayment"
    repayment_plot_fixed_merged = (
        pd.concat([repayment_plot_fixed, repayment_plot_fixed_wo_extra])
        if show_schedules_wo_extra
        else repayment_plot_fixed
    )

    if repayment_cycle.is_fortnightly():
        repayment_plot_fixed_merged["Repayment"] = (
            repayment_plot_fixed_merged["Repayment"] / 14 * (365 / 12)
        )

    with st.expander("Repayment over time"):

        fig3 = px.scatter(
            repayment_plot_fixed_merged,
            x="ScheduleYears",
            y="Repayment",
            color="Schedule" if show_schedules_wo_extra else None,
        )
        fig3.update_layout(
            title={"text": "Total Repayment / Variable", "x": 0.5, "xanchor": "center"}
        )
        fig3.update_traces(marker=dict(size=3))
        fig3.update_xaxes(title_text="ScheduleYears")
        fig3.update_yaxes(title_text="Total Repayment ($, monthly)")

        st.plotly_chart(fig3)

with col2:

    # - Variable

    st.write("#### Variable")

    st.write("##### Config")

    with st.expander("Override variables"):

        toggle_balance_variable = st.toggle("Override balance", False, key="k2a")

        if toggle_balance_variable:
            balance_variable = st.number_input(
                "Balance override ($): ", 0, 2000000, 625000, 1000, key="k2b"
            )

        toggle_interest_variable = st.toggle("Override interest rate", False, key="k2e")

        if toggle_interest_variable:
            interest_variable = st.number_input(
                ":red[Interest rate override (%)]", 0.1, 15.0, 6.14, key="k2f"
            )

        toggle_repayment_variable = st.toggle(
            "Override base repayment", False, key="k2c"
        )

        if toggle_repayment_variable:
            repayment_variable = st.number_input(
                ":orange[Base repayment override ("
                + repayment_cycle.simple_str()
                + ", $)]",
                0.0,
                10000.0,
                1883.17,
                50.0,
                key="k2d",
            )

        toggle_offset = st.toggle("Override offset", False, key="k2g")

        if toggle_offset:
            balance_offset = st.number_input(
                "Offset override ($)", 0, 300000, 100000, 1000, key="k2h"
            )

    st.write("Balance: " + f"${balance_variable:,.0f}")

    st.write(":red[Interest: " + f"{interest_variable:.3f}%]")

    st.write(
        ":orange[Base repayment ("
        + repayment_cycle.simple_str()
        + "): "
        + f"${repayment_variable:,.0f}"
        + " (plus fixed after "
        + fixed_loan_end.strftime("%d/%m/%Y")
        + ")]"
    )

    if repayment_cycle.is_fortnightly():
        st.write(
            ":orange[Base repayment (monthly): "
            + f"${(repayment_variable / 14 * (365 / 12)):,.0f}"
            + " (plus fixed after "
            + fixed_loan_end.strftime("%d/%m/%Y")
            + ")]"
        )

    st.write("Offset: " + f"${balance_offset:,.0f}")

    with st.expander("Theoretical schedule (for information only, not used)"):
        years_planner_variable = st.number_input("Years", 1, 40, 25, 1, key="k2i")

        planner_variable = home_loan_planner.HomeLoanPlanner(
            "Fixed",
            N=years_planner_variable,
            k=((365 / 14) if repayment_cycle.is_fortnightly() else 12),
            P=balance_variable - balance_offset,
            R0=interest_variable / 100,
        )

        st.write(
            "Repayment ("
            + repayment_cycle.simple_str()
            + "), for identical repayment and interest cycles: "
            + f"${planner_variable.c0:,.0f}"
        )

    st.divider()
    st.write("##### Schedule")

    extra_slider_variable = st.slider(
        ":green[Extra repayment (monthly, plus fixed after "
        + fixed_loan_end.strftime("%d/%m/%Y")
        + ")]",
        0,
        20000,
        default_extrarepayment_variable,
        100,
        key="k2j",
    )

    repayment_extra_variable = extra_slider_variable
    if repayment_cycle.is_fortnightly():
        repayment_extra_variable = repayment_extra_variable / (365 / 12) * 14
        st.write(
            ":green[Extra repayment (fortnightly): "
            + f"${repayment_extra_variable:,.0f}"
            + " (plus fixed after "
            + fixed_loan_end.strftime("%d/%m/%Y")
            + ")]"
        )

    repayment_total_variable = repayment_variable + repayment_extra_variable

    st.write(
        ":blue[Total repayment ("
        + repayment_cycle.simple_str()
        + "): "
        + f"${repayment_total_variable:,.0f}"
        + " (plus fixed after "
        + fixed_loan_end.strftime("%d/%m/%Y")
        + ")]"
    )

    if repayment_cycle.is_fortnightly():
        st.write(
            ":blue[Total repayment (monthly): "
            + f"${(repayment_total_variable / 14 * (365 / 12)):,.0f}"
            + " (plus fixed after "
            + fixed_loan_end.strftime("%d/%m/%Y")
            + ")]"
        )

    df_schedule_variable = home_loan_simulator.simulate(
        loan_start=loan_start,
        principal=balance_variable,
        offset=balance_offset,
        schedule_start=schedule_start,
        interest_rate=interest_variable,
        prev_interest_date=prev_interest_date,
        interest_cycle=interest_cycle,
        repayment=repayment_total_variable,
        prev_repayment_date=prev_repayment_date,
        repayment_cycle=repayment_cycle,
        schedule_end=None,
        leftover_incoming=fixed_loan_end,
        leftover_amount=end_of_fixed_loan_balance,
        leftover_repayment=repayment_total_fixed,
    )

    df_schedule_variable_wo_extra = home_loan_simulator.simulate(
        loan_start=loan_start,
        principal=balance_variable,
        offset=balance_offset,
        schedule_start=schedule_start,
        interest_rate=interest_variable,
        prev_interest_date=prev_interest_date,
        interest_cycle=interest_cycle,
        repayment=repayment_variable,
        prev_repayment_date=prev_repayment_date,
        repayment_cycle=repayment_cycle,
        schedule_end=None,
        leftover_incoming=fixed_loan_end,
        leftover_amount=end_of_fixed_loan_balance_wo_extra,
        leftover_repayment=repayment_fixed,
    )

    df_schedule_variable_save = home_loan_simulator.simulate(
        loan_start=loan_start,
        principal=balance_variable - save_now_amount,
        offset=balance_offset,
        schedule_start=schedule_start,
        interest_rate=interest_variable,
        prev_interest_date=prev_interest_date,
        interest_cycle=interest_cycle,
        repayment=repayment_total_variable,
        prev_repayment_date=prev_repayment_date,
        repayment_cycle=repayment_cycle,
        schedule_end=None,
        leftover_incoming=fixed_loan_end,
        leftover_amount=end_of_fixed_loan_balance,
        leftover_repayment=repayment_total_fixed,
    )

    df_schedule_variable_spend = home_loan_simulator.simulate(
        loan_start=loan_start,
        principal=balance_variable + spend_now_amount,
        offset=balance_offset,
        schedule_start=schedule_start,
        interest_rate=interest_variable,
        prev_interest_date=prev_interest_date,
        interest_cycle=interest_cycle,
        repayment=repayment_total_variable,
        prev_repayment_date=prev_repayment_date,
        repayment_cycle=repayment_cycle,
        schedule_end=None,
        leftover_incoming=fixed_loan_end,
        leftover_amount=end_of_fixed_loan_balance,
        leftover_repayment=repayment_total_fixed,
    )

    df_schedule_variable_invest = home_loan_simulator.simulate(
        loan_start=loan_start,
        principal=balance_variable,
        offset=balance_offset,
        schedule_start=schedule_start,
        interest_rate=interest_variable,
        prev_interest_date=prev_interest_date,
        interest_cycle=interest_cycle,
        repayment=repayment_total_variable,
        prev_repayment_date=prev_repayment_date,
        repayment_cycle=repayment_cycle,
        schedule_end=None,
        leftover_incoming=fixed_loan_end,
        leftover_amount=end_of_fixed_loan_balance,
        leftover_repayment=repayment_total_fixed,
        extra_cost_amount=invest_now_cost_amount,
        extra_win_amount=invest_now_win_amount,
        extra_win_cycle=invest_now_win_cycle,
    )

    with st.expander("Detailed schedule"):
        st.write(df_schedule_variable.style.format(schedule_format))

    total_years_variable = df_schedule_variable.iloc[-1]["ScheduleYears"]
    total_repayments_variable = df_schedule_variable["Repayment"].sum()
    total_interest_variable = df_schedule_variable["Interest"].sum()

    total_repayments_variable_save = df_schedule_variable_save["Repayment"].sum()
    total_repayments_variable_spend = df_schedule_variable_spend["Repayment"].sum()
    total_repayments_variable_invest = df_schedule_variable_invest["Repayment"].sum()

    interest_per_month_variable = (
        (df_schedule_variable.iloc[0]["Principal"] - balance_offset)
        * (interest_variable / 100)
        / 12
    )

    st.write(
        ":red[Initial interest: "
        + f"\\${interest_per_month_variable:,.0f}"
        + "/m = "
        + f"\\${interest_per_month_variable * (12 / 365):,.0f}"
        + "/d = "
        + f"\\${interest_per_month_variable * (12 / (365 * 24)):,.1f}"
        + "/h]"
    )

    if show_so_far_information:
        st.write("Time so far: " + f"{years_so_far:.2f} yrs")
    st.write("Time to go: " + f"{total_years_variable:.2f} yrs")
    if show_so_far_information:
        st.write(
            "Time so far & to go: " + f"{(years_so_far + total_years_variable):.2f} yrs"
        )

    if show_schedules_wo_extra or show_alternative_scheduless:
        st.divider()
        st.write("##### Other Schedules")

    if show_schedules_wo_extra:
        with st.expander("Detailed schedule: w/o extra repayment"):
            st.write(df_schedule_variable_wo_extra.style.format(schedule_format))

    if show_alternative_scheduless:
        with st.expander("Detailed schedule: save now"):
            st.write(df_schedule_variable_save.style.format(schedule_format))

        with st.expander("Detailed schedule: spend now"):
            st.write(df_schedule_variable_spend.style.format(schedule_format))

        with st.expander("Detailed schedule: invest now"):
            st.write(df_schedule_variable_invest.style.format(schedule_format))

    st.divider()
    st.write("##### Sums")

    if show_so_far_information:
        st.write(":red[Interest so far: " + f"${total_interest_so_far_variable:,.0f}]")
    st.write(
        ":red[Interest to go: "
        + f"${total_interest_variable:,.0f}"
        + " ("
        + f"{(100 * total_interest_variable / total_repayments_variable):.1f}"
        + "%)]"
    )
    if show_so_far_information:
        st.write(
            ":red[Interest so far & to go: "
            + f"${total_interest_so_far_variable + total_interest_variable:,.0f}"
            + " ("
            + f"{(100 * (total_interest_so_far_variable + total_interest_variable) / (total_repayments_so_far_variable + total_repayments_variable)):.1f}"
            + "%)]"
        )

        st.write(
            ":blue[Total repayment so far: "
            + f"${total_repayments_so_far_variable:,.0f}]"
        )
    st.write(":blue[Total repayment to go: " + f"${total_repayments_variable:,.0f}]")
    if show_so_far_information:
        st.write(
            ":blue[Total repayment so far & to go: "
            + f"${total_repayments_so_far_variable + total_repayments_variable:,.0f}]"
        )

    before_end_of_fixed_loan_balance = df_schedule_variable[
        df_schedule_variable["Date"] <= fixed_loan_end
    ]

    before_end_of_fixed_loan_balance = before_end_of_fixed_loan_balance.iloc[-2][
        "Principal"
    ]
    st.write(
        "Variable loan balance shortly before end of fixed loan term: "
        + f"${before_end_of_fixed_loan_balance:,.0f}"
    )

    principal_smaller_offset = df_schedule_variable[
        df_schedule_variable["Principal"] <= balance_offset
    ]

    if len(principal_smaller_offset) > 0:
        principal_smaller_offset_first_date = principal_smaller_offset.iloc[0]["Date"]
        st.write(
            "Date when principal smaller than offset for the first time: "
            + principal_smaller_offset_first_date.strftime("%d/%m/%Y")
        )

        if principal_smaller_offset_first_date < fixed_loan_end:
            principal_smaller_offset_second_date = df_schedule_variable[
                (df_schedule_variable["Principal"] <= balance_offset)
                & (df_schedule_variable["Date"] > fixed_loan_end)
            ].iloc[0]["Date"]
            st.write(
                "Date when principal smaller than offset for the second time: "
                + principal_smaller_offset_second_date.strftime("%d/%m/%Y")
            )

    df_schedule_variable["Schedule"] = "default"
    df_schedule_variable_wo_extra["Schedule"] = "wo/ extra repayment"
    df_schedule_variable_merged = (
        pd.concat([df_schedule_variable, df_schedule_variable_wo_extra])
        if show_schedules_wo_extra
        else df_schedule_variable
    )

    with st.expander("Principal over time"):

        fig1 = px.scatter(
            df_schedule_variable_merged,
            x="Date",
            y="Principal",
            color="Schedule" if show_schedules_wo_extra else None,
        )
        fig1.update_layout(
            title={"text": "Principal / Variable", "x": 0.5, "xanchor": "center"}
        )
        fig1.update_traces(marker=dict(size=3))
        fig1.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
        fig1.update_yaxes(title_text="Principal ($)")

        st.plotly_chart(fig1)

    interest_plot_variable = pd.DataFrame(df_schedule_variable)
    interest_plot_variable = interest_plot_variable[
        (interest_plot_variable["Interest"] >= 0)
        & (interest_plot_variable["Date"] > schedule_start)
    ]

    interest_plot_variable_wo_extra = pd.DataFrame(df_schedule_variable_wo_extra)
    interest_plot_variable_wo_extra = interest_plot_variable_wo_extra[
        (interest_plot_variable_wo_extra["Interest"] >= 0)
        & (interest_plot_variable_wo_extra["Date"] > schedule_start)
    ]

    interest_plot_variable["Schedule"] = "default"
    interest_plot_variable_wo_extra["Schedule"] = "wo/ extra repayment"
    interest_plot_variable_merged = (
        pd.concat([interest_plot_variable, interest_plot_variable_wo_extra])
        if show_schedules_wo_extra
        else interest_plot_variable
    )

    with st.expander("Interest over time"):

        fig2 = px.scatter(
            interest_plot_variable_merged,
            x="ScheduleYears",
            y="Interest",
            color="Schedule" if show_schedules_wo_extra else None,
        )
        fig2.update_layout(
            title={"text": "Interest / Variable", "x": 0.5, "xanchor": "center"}
        )
        fig2.update_traces(marker=dict(size=3))
        fig2.update_xaxes(title_text="ScheduleYears")
        fig2.update_yaxes(title_text="Interest ($, monthly)")

        st.plotly_chart(fig2)

    repayment_plot_variable = pd.DataFrame(df_schedule_variable)
    repayment_plot_variable = repayment_plot_variable[
        (repayment_plot_variable["Repayment"] >= 0)
        & (repayment_plot_variable["Date"] > schedule_start)
    ]

    repayment_plot_variable_wo_extra = pd.DataFrame(df_schedule_variable_wo_extra)
    repayment_plot_variable_wo_extra = repayment_plot_variable_wo_extra[
        (repayment_plot_variable_wo_extra["Repayment"] >= 0)
        & (repayment_plot_variable_wo_extra["Date"] > schedule_start)
    ]

    repayment_plot_variable["Schedule"] = "default"
    repayment_plot_variable_wo_extra["Schedule"] = "wo/ extra repayment"
    repayment_plot_variable_merged = (
        pd.concat([repayment_plot_variable, repayment_plot_variable_wo_extra])
        if show_schedules_wo_extra
        else repayment_plot_variable
    )

    if repayment_cycle.is_fortnightly():
        repayment_plot_variable_merged["Repayment"] = (
            repayment_plot_variable_merged["Repayment"] / 14 * (365 / 12)
        )

    with st.expander("Repayment over time"):

        fig3 = px.scatter(
            repayment_plot_variable_merged,
            x="ScheduleYears",
            y="Repayment",
            color="Schedule" if show_schedules_wo_extra else None,
        )
        fig3.update_layout(
            title={"text": "Total Repayment / Variable", "x": 0.5, "xanchor": "center"}
        )
        fig3.update_traces(marker=dict(size=3))
        fig3.update_xaxes(title_text="ScheduleYears")
        fig3.update_yaxes(title_text="Total Repayment ($, monthly)")

        st.plotly_chart(fig3)

# - Fixed & Variable

_, col2, _ = st.columns(3)

with col2:

    st.write("### Fixed & Variable")

    total_wo_extra = repayment_fixed + repayment_variable
    total_extra = repayment_extra_fixed + repayment_extra_variable

    if repayment_cycle.is_fortnightly():
        total_wo_extra = total_wo_extra / 14 * (365 / 12)
        total_extra = total_extra / 14 * (365 / 12)

    total = total_wo_extra + total_extra

    st.write("##### Config")

    st.write(":orange[Base repayment (monthly): " + f"${total_wo_extra:,.0f}]")

    st.divider()
    st.write("##### Schedule")

    st.write(":green[Extra repayment (monthly): " + f"${total_extra:,.0f}]")
    st.write(":blue[Total repayment (monthly): " + f"${total:,.0f}]")

    if show_so_far_information:
        st.write("Time so far: " + f"{years_so_far:.2f} yrs")
    st.write("Time to go: " + f"{total_years_variable:.2f} yrs")
    if show_so_far_information:
        st.write(
            "Time so far & to go: " + f"{years_so_far + total_years_variable:.2f} yrs"
        )

    interest_per_month = interest_per_month_fixed + interest_per_month_variable

    st.write(
        ":red[Initial interest: "
        + f"\\${interest_per_month:,.0f}"
        + "/m = "
        + f"\\${interest_per_month * (12 / 365):,.0f}"
        + "/d = "
        + f"\\${interest_per_month * (12 / (365 * 24)):,.1f}"
        + "/h]"
    )

    st.divider()
    st.write("##### Sums")

    effective_loan_amount = (
        df_balance_total.iloc[0]["Balance"] + df_balance_offset.iloc[0]["Balance"]
    )

    st.write("Effective loan amount: " + f"${effective_loan_amount:,.0f}")

    if show_so_far_information:
        st.write(
            ":red[Interest so far: "
            + f"${(total_interest_so_far_fixed + total_interest_so_far_variable):,.0f}]"
        )
    st.write(
        ":red[Interest to go: "
        + f"${(total_interest_fixed + total_interest_variable):,.0f}]"
    )
    if show_so_far_information:
        st.write(
            ":red[Interest so far & to go: "
            + f"${(
            total_interest_so_far_fixed + total_interest_fixed +
            total_interest_so_far_variable + total_interest_variable):,.0f}]"
        )

        st.write(
            ":blue[Total repayment so far: "
            + f"${(total_repayments_so_far_fixed + total_repayments_so_far_variable):,.0f}]"
        )
    st.write(
        ":blue[Total repayment to go: "
        + f"${(total_repayments_fixed + total_repayments_variable):,.0f}]"
    )
    if show_save_spend_invest_information:
        st.write(
            ":blue[... save "
            + f"\\${save_now_amount:,.0f}"
            + " now: "
            + f"Δ=${(total_repayments_variable_save - total_repayments_variable):,.0f}]"
        )
        st.write(
            ":blue[... spend "
            + f"\\${spend_now_amount:,.0f}"
            + " now: "
            + f"Δ=${(total_repayments_variable_spend - total_repayments_variable):,.0f}]"
        )
        st.write(
            ":blue[... invest "
            + f"\\${invest_now_cost_amount:,.0f}"
            + " now, gain "
            + f"\\${invest_now_win_amount:,.0f}"
            + " "
            + invest_now_win_cycle.simple_str()
            + ": "
            + f"Δ=${(total_repayments_variable_invest - total_repayments_variable):,.0f}]"
        )
    if show_so_far_information:
        st.write(
            ":blue[Total repayment so far & to go: "
            + f"${(
            total_repayments_so_far_fixed + total_repayments_fixed +
            total_repayments_so_far_variable + total_repayments_variable):,.0f}]"
        )
