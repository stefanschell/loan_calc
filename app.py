import pandas as pd
import plotly.express as px
import streamlit as st
import account_demo
import account_reader
import account_interpreter
import home_loan_simulator
import home_loan_planner
from datetime import timedelta
import math
import os
import shutil
import zipfile

# config

loan_start = pd.to_datetime("2024-10-16")

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
    "Stashed": "${:,.0f}",
    "ExtraWinForLoan": "${:,.0f}",
    "ExtraWinForUs": "${:,.0f}",
    "Principal": "${:,.0f}",
    "Stash": "${:,.0f}",
}

# setup

st.set_page_config(layout="wide")
st.title("Home Loan")

# aquire data

data_folder = None
data_text = None
data_color = None

# option 1: using uploaded/external data
browser_file = st.file_uploader("Upload account statements")

if browser_file is not None:
    data_folder_test = "external_data"
    if os.path.isdir(data_folder_test):
        shutil.rmtree(data_folder_test)
    with zipfile.ZipFile(browser_file, "r") as zip_file:
        zip_file.extractall(data_folder_test)
    if os.path.isdir(data_folder_test) and len(os.listdir(data_folder_test)) > 0:
        data_folder = data_folder_test
        data_text = "Using uploaded data."
        data_color = "green"

# option 2: using internal data
else:
    data_folder_test = "internal_data"
    if os.path.isdir(data_folder_test):
        data_folder = data_folder_test
        data_text = "Using internal data."
        data_color = "yellow"

# option 3: using demo data
create_demo_data = st.toggle(
    "Use demo data",
    value=data_folder is None,
    disabled=data_folder is None,
)

if create_demo_data:
    data_text = "Using demo data."
    data_color = "purple"

# get data

st.markdown(
    "<h3 style='text-align: center; color: "
    + data_color
    + "; border: 5px solid "
    + data_color
    + "; padding: 10px; margin: 20px; border-radius: 100px;'>"
    + data_text
    + "</div>",
    unsafe_allow_html=True,
)

df_in = (
    account_reader.get_dataframe(data_folder, date_from=loan_start)
    if not create_demo_data
    else account_demo.create_demo_account(
        demo_start=loan_start, demo_end=pd.to_datetime("today")
    )
)

df_in = account_interpreter.add_interest_information(df_in)

# Retrospective

st.write("# Retrospective")

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


with st.expander("Balance over time"):

    extrapolation_length = st.slider("Extrapolation length", 0.0, 10.0, 0.5, 0.5)
    df_balance_total_fitted = account_interpreter.fit_balance(
        df_balance_total, extrapolation_length
    )

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

col1, col2 = st.columns(2)

with col1:

    with st.expander("Interest, base, extra and total repayment so far"):
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
    with st.expander("Interest, base, extra and total repayment so far"):
        st.write(":red[Interest so far: " + f"${total_interest_so_far_variable:,.0f}]")
        st.write(
            ":orange[Base repayment so far: "
            + f"${base_repayment_so_far_variable:,.0f}]"
        )
        st.write(
            ":green[Extra repayment so far: "
            + f"${extra_repayment_so_far_variable:,.0f}]"
        )
        st.write(
            ":blue[Total repayment so far: "
            + f"${total_repayments_so_far_variable:,.0f}]"
        )

_, col2, _ = st.columns(3)

with col2:
    st.write("#### Fixed & Variable")
    st.write(":red[Interest so far: " + f"${total_interest_so_far:,.0f}]")
    st.write(":orange[Base repayment so far: " + f"${base_repayment_so_far:,.0f}]")
    st.write(":green[Extra repayment so far: " + f"${extra_repayment_so_far:,.0f}]")
    st.write(":blue[Total repayment so far: " + f"${total_repayments_so_far:,.0f}]")

# Prospective

st.write("# Prospective")

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

repayment_cycle = home_loan_simulator.Cycle.FORTNIGHTLY
interest_cycle = home_loan_simulator.Cycle.MONTHLY_END_OF_MONTH

_, col2, _ = st.columns(3)

with col2:
    st.write("#### Fixed & Variable")

    with st.expander("Override settings"):

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

        repayment_use_stash = not st.toggle(
            "Do not use stashed money for repayment", False
        )

        st.divider()

        restart_loan_today = st.toggle("Restart loan today", False)

        toggle_override_fixed_loan_years = st.toggle("Override fixed loan term", False)
        fixed_loan_years = 5
        if toggle_override_fixed_loan_years:
            fixed_loan_years = st.number_input(
                "Fixed loan term override (yrs)", 1, 15, 5, 1
            )
        fixed_loan_length = timedelta(days=365 * fixed_loan_years)
        fixed_loan_end = loan_start + fixed_loan_length

        if restart_loan_today:
            loan_start = pd.to_datetime("today")
            fixed_loan_end = loan_start + fixed_loan_length
            schedule_start = loan_start
            prev_interest_date = schedule_start
            prev_repayment_date = schedule_start

        show_so_far_information = not restart_loan_today

        st.write("Start of loan:", loan_start.strftime("%d/%m/%Y"))
        st.write(
            "Last retrospective interest:", prev_interest_date.strftime("%d/%m/%Y")
        )
        st.write(
            "Last retrospective repayment:", prev_repayment_date.strftime("%d/%m/%Y")
        )
        st.write("Start of schedule:", schedule_start.strftime("%d/%m/%Y"))
        st.write("End of fixed loan term:", fixed_loan_end.strftime("%d/%m/%Y"))

        st.divider()

        show_other_schedules = st.toggle("Show other schedules", False)

        show_fear_save_spend_invest_information = st.toggle(
            "Show hope, fear, save, spend, and invest", False
        )

        if show_fear_save_spend_invest_information:
            st.write("Hope: interest decrease (variable only)")

            hope_interest_change = st.number_input(
                "Interest decrease (%)",
                0.0,
                10.0,
                1.0,
            )

            st.write("Fear: interest increase (variable only)")

            fear_interest_change = st.number_input(
                "Interest increase (%)",
                0.0,
                10.0,
                2.0,
            )

            st.write("Save: one time saving of an amount of money")

            save_amount = st.number_input(
                "Amount ($)",
                0,
                100000,
                3000,
            )

            st.write("Spend: one time spending of an amount of money")

            spend_amount = st.number_input(
                "Amount ($)",
                0,
                100000,
                10000,
            )

            st.write(
                "Invest: one time investment of an amount of money, regular gain of money for a duration"
            )

            invest_cost_amount = st.number_input(
                "Cost amount ($)",
                0,
                100000,
                5000,
            )

            invest_win_amount = st.number_input(
                "Win amount ($)",
                0,
                10000,
                54,
            )

            invest_win_cycle = st.selectbox(
                "Win cycle",
                home_loan_simulator.Cycle,
                index=1,
                format_func=home_loan_simulator.Cycle.complex_str,
            )

            invest_win_duration = timedelta(
                days=365 * st.number_input("Duration (yrs)", 0, 99, 10),
            )
        else:
            hope_interest_change = 0
            fear_interest_change = 0
            save_amount = 0
            spend_amount = 0
            invest_cost_amount = 0
            invest_win_amount = None
            invest_win_cycle = None
            invest_win_duration = None

_, col2, _ = st.columns(3)

with col2:

    st.write("##### Config")

    history_length_days = math.ceil(
        (df_in["DateSeries"].iloc[-1] - df_in["DateSeries"].iloc[0]).days
    )

    history_length_days_used = st.slider(
        "Days for extraction of offset and extra repayment:",
        1,
        history_length_days,
        history_length_days,
        10,
    )

    history_cutoff_date = df_in["DateSeries"].iloc[-1] - timedelta(
        days=history_length_days_used
    )

    extracted_offset = df_balance_offset[
        df_balance_offset["DateSeries"] >= history_cutoff_date
    ]["Balance"].mean()

    extracted_extra_repayment = (
        df_change_variable[
            (df_change_variable["interpolated"] == True)
            & (df_change_variable["Label"] == "Extrarepayment")
            & (df_change_variable["DateSeries"] >= history_cutoff_date)
        ]["Change"]
        .dropna()
        .mean()
    )

    round_to_hundred = lambda x: int(round(x / 100) * 100)

    extracted_offset = round_to_hundred(extracted_offset)
    extracted_extra_repayment = round_to_hundred(extracted_extra_repayment)

    st.write("Extracted offset: " + f"\\${extracted_offset:,.0f}")

    st.write(
        "Extracted extra repayment (monthly): " + f"\\${extracted_extra_repayment:,.0f}"
    )

    extracted_extra_repayment = st.slider(
        ":green[Extra repayment (monthly, $)]",
        0,
        20800,
        5000,
        100,
    )

    default_extra_repayment_variable = max(0, extracted_extra_repayment - 800)
    default_extra_repayment_fixed = (
        extracted_extra_repayment - default_extra_repayment_variable
    )

col1, col2 = st.columns(2)

with col1:

    # - Fixed

    st.write("#### Fixed")

    st.write("##### Config")

    with st.expander("Override config"):

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

    if show_other_schedules:
        with st.expander("Calculate theoretical schedule"):
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
        ":green[Extra repayment (monthly, \\$, limited to \\$10000 yearly, i.e. \\$800 monthly)]",
        0,
        800,
        default_extra_repayment_fixed,
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
        repayment_use_stash=repayment_use_stash,
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
        repayment_use_stash=repayment_use_stash,
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
    st.write(
        "Time to go: "
        + f"{total_years_fixed:.2f} yrs, till "
        + fixed_loan_end.strftime("%d/%m/%Y")
        + ", fixed loan term ends"
    )
    if show_so_far_information:
        st.write(
            "Time so far & to go: " + f"{(years_so_far + total_years_fixed):.2f} yrs"
        )

    if show_other_schedules:
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

    st.write(
        "Principal at the end of fixed loan term: "
        + f"${end_of_fixed_loan_balance:,.0f}"
    )

    df_schedule_fixed["Schedule"] = "default"
    df_schedule_fixed_wo_extra["Schedule"] = "wo/ extra repayment"
    df_schedule_fixed_merged = (
        pd.concat([df_schedule_fixed, df_schedule_fixed_wo_extra])
        if show_other_schedules
        else df_schedule_fixed
    )

    with st.expander("Principal and Stash over time"):

        fig1a = px.scatter(
            df_schedule_fixed_merged,
            x="Date",
            y="Principal",
            color="Schedule" if show_other_schedules else None,
        )
        fig1a.update_layout(
            title={"text": "Principal / Fixed", "x": 0.5, "xanchor": "center"}
        )
        fig1a.update_traces(marker=dict(size=3))
        fig1a.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
        fig1a.update_yaxes(title_text="Principal ($)")

        st.plotly_chart(fig1a, key="1af")

        fig1b = px.scatter(
            df_schedule_fixed_merged,
            x="Date",
            y="Stash",
            color="Schedule" if show_other_schedules else None,
        )
        fig1b.update_layout(
            title={"text": "Stash / Fixed", "x": 0.5, "xanchor": "center"}
        )
        fig1b.update_traces(marker=dict(size=3))
        fig1b.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
        fig1b.update_yaxes(title_text="Principal ($)")

        st.plotly_chart(fig1b, key="1bf")

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
        if show_other_schedules
        else interest_plot_fixed
    )

    with st.expander("Interest over time"):
        fig2 = px.scatter(
            interest_plot_fixed_merged,
            x="ScheduleYears",
            y="Interest",
            color="Schedule" if show_other_schedules else None,
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
        if show_other_schedules
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
            color="Schedule" if show_other_schedules else None,
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

    with st.expander("Override config"):

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
            extracted_offset = st.number_input(
                "Offset override ($)", 0, 300000, 100000, 1000, key="k2h"
            )

    st.write(
        "Balance: "
        + f"${balance_variable:,.0f} (plus fixed after "
        + fixed_loan_end.strftime("%d/%m/%Y")
        + ")"
    )

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

    st.write("Offset: " + f"${extracted_offset:,.0f}")

    if show_other_schedules:
        with st.expander("Calculate theoretical schedule"):
            years_planner_variable = st.number_input("Years", 1, 99, 25, 1, key="k2i")

            planner_variable = home_loan_planner.HomeLoanPlanner(
                "Fixed",
                N=years_planner_variable,
                k=((365 / 14) if repayment_cycle.is_fortnightly() else 12),
                P=balance_variable - extracted_offset,
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
        ":green[Extra repayment (monthly, $, plus fixed after "
        + fixed_loan_end.strftime("%d/%m/%Y")
        + ")]",
        0,
        20000,
        default_extra_repayment_variable,
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
        offset=extracted_offset,
        schedule_start=schedule_start,
        interest_rate=interest_variable,
        prev_interest_date=prev_interest_date,
        interest_cycle=interest_cycle,
        repayment=repayment_total_variable,
        prev_repayment_date=prev_repayment_date,
        repayment_cycle=repayment_cycle,
        repayment_use_stash=repayment_use_stash,
        schedule_end=None,
        leftover_incoming=fixed_loan_end,
        leftover_amount=end_of_fixed_loan_balance,
        leftover_repayment=repayment_total_fixed,
    )

    df_schedule_variable_wo_extra = home_loan_simulator.simulate(
        loan_start=loan_start,
        principal=balance_variable,
        offset=extracted_offset,
        schedule_start=schedule_start,
        interest_rate=interest_variable,
        prev_interest_date=prev_interest_date,
        interest_cycle=interest_cycle,
        repayment=repayment_variable,
        prev_repayment_date=prev_repayment_date,
        repayment_cycle=repayment_cycle,
        repayment_use_stash=repayment_use_stash,
        schedule_end=None,
        leftover_incoming=fixed_loan_end,
        leftover_amount=end_of_fixed_loan_balance_wo_extra,
        leftover_repayment=repayment_fixed,
    )

    df_schedule_variable_hope = home_loan_simulator.simulate(
        loan_start=loan_start,
        principal=balance_variable,
        offset=extracted_offset,
        schedule_start=schedule_start,
        interest_rate=interest_variable - hope_interest_change,
        prev_interest_date=prev_interest_date,
        interest_cycle=interest_cycle,
        repayment=repayment_total_variable,
        prev_repayment_date=prev_repayment_date,
        repayment_cycle=repayment_cycle,
        repayment_use_stash=repayment_use_stash,
        schedule_end=None,
        leftover_incoming=fixed_loan_end,
        leftover_amount=end_of_fixed_loan_balance,
        leftover_repayment=repayment_total_fixed,
    )

    df_schedule_variable_fear = home_loan_simulator.simulate(
        loan_start=loan_start,
        principal=balance_variable,
        offset=extracted_offset,
        schedule_start=schedule_start,
        interest_rate=interest_variable + fear_interest_change,
        prev_interest_date=prev_interest_date,
        interest_cycle=interest_cycle,
        repayment=repayment_total_variable,
        prev_repayment_date=prev_repayment_date,
        repayment_cycle=repayment_cycle,
        repayment_use_stash=repayment_use_stash,
        schedule_end=None,
        leftover_incoming=fixed_loan_end,
        leftover_amount=end_of_fixed_loan_balance,
        leftover_repayment=repayment_total_fixed,
    )

    df_schedule_variable_save = home_loan_simulator.simulate(
        loan_start=loan_start,
        principal=balance_variable - save_amount,
        offset=extracted_offset,
        schedule_start=schedule_start,
        interest_rate=interest_variable,
        prev_interest_date=prev_interest_date,
        interest_cycle=interest_cycle,
        repayment=repayment_total_variable,
        prev_repayment_date=prev_repayment_date,
        repayment_cycle=repayment_cycle,
        repayment_use_stash=repayment_use_stash,
        schedule_end=None,
        leftover_incoming=fixed_loan_end,
        leftover_amount=end_of_fixed_loan_balance,
        leftover_repayment=repayment_total_fixed,
    )

    df_schedule_variable_spend = home_loan_simulator.simulate(
        loan_start=loan_start,
        principal=balance_variable + spend_amount,
        offset=extracted_offset,
        schedule_start=schedule_start,
        interest_rate=interest_variable,
        prev_interest_date=prev_interest_date,
        interest_cycle=interest_cycle,
        repayment=repayment_total_variable,
        prev_repayment_date=prev_repayment_date,
        repayment_cycle=repayment_cycle,
        repayment_use_stash=repayment_use_stash,
        schedule_end=None,
        leftover_incoming=fixed_loan_end,
        leftover_amount=end_of_fixed_loan_balance,
        leftover_repayment=repayment_total_fixed,
    )

    df_schedule_variable_invest = home_loan_simulator.simulate(
        loan_start=loan_start,
        principal=balance_variable + invest_cost_amount,
        offset=extracted_offset,
        schedule_start=schedule_start,
        interest_rate=interest_variable,
        prev_interest_date=prev_interest_date,
        interest_cycle=interest_cycle,
        repayment=repayment_total_variable,
        prev_repayment_date=prev_repayment_date,
        repayment_cycle=repayment_cycle,
        repayment_use_stash=repayment_use_stash,
        schedule_end=None,
        leftover_incoming=fixed_loan_end,
        leftover_amount=end_of_fixed_loan_balance,
        leftover_repayment=repayment_total_fixed,
        extra_win_amount=invest_win_amount,
        extra_win_cycle=invest_win_cycle,
        extra_win_duration=invest_win_duration,
    )

    with st.expander("Detailed schedule"):
        st.write(df_schedule_variable.style.format(schedule_format))

    total_years_variable = df_schedule_variable.iloc[-1]["ScheduleYears"]
    variable_loan_end = df_schedule_variable.iloc[-1]["Date"]
    total_repayments_variable = df_schedule_variable["Repayment"].sum()
    total_interest_variable = df_schedule_variable["Interest"].sum()

    total_years_variable_hope = df_schedule_variable_hope.iloc[-1]["ScheduleYears"]
    total_years_variable_fear = df_schedule_variable_fear.iloc[-1]["ScheduleYears"]
    total_repayments_variable_hope = df_schedule_variable_hope["Repayment"].sum()
    total_repayments_variable_fear = df_schedule_variable_fear["Repayment"].sum()
    total_repayments_variable_save = df_schedule_variable_save["Repayment"].sum()
    total_repayments_variable_spend = df_schedule_variable_spend["Repayment"].sum()
    total_repayments_variable_invest = df_schedule_variable_invest["Repayment"].sum()
    extra_win_for_us_invest = df_schedule_variable_invest["ExtraWinForUs"].sum()

    interest_per_month_variable = (
        (df_schedule_variable.iloc[0]["Principal"] - extracted_offset)
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
    st.write(
        "Time to go: "
        + f"{total_years_variable:.2f} yrs, till "
        + variable_loan_end.strftime("%d/%m/%Y")
    )
    if show_so_far_information:
        st.write(
            "Time so far & to go: " + f"{(years_so_far + total_years_variable):.2f} yrs"
        )

    if show_other_schedules:
        st.divider()
        st.write("##### Other Schedules")

        with st.expander("Detailed schedule: w/o extra repayment"):
            st.write(df_schedule_variable_wo_extra.style.format(schedule_format))

        if show_fear_save_spend_invest_information:
            with st.expander("Detailed schedule: hope"):
                st.write(df_schedule_variable_hope.style.format(schedule_format))

            with st.expander("Detailed schedule: fear"):
                st.write(df_schedule_variable_fear.style.format(schedule_format))

            with st.expander("Detailed schedule: save"):
                st.write(df_schedule_variable_save.style.format(schedule_format))

            with st.expander("Detailed schedule: spend"):
                st.write(df_schedule_variable_spend.style.format(schedule_format))

            with st.expander("Detailed schedule: invest"):
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

    df_schedule_variable_before_end_of_fixed_loan = df_schedule_variable[
        df_schedule_variable["Date"] <= fixed_loan_end
    ]

    before_end_of_fixed_loan_balance = (
        df_schedule_variable_before_end_of_fixed_loan.iloc[-2]["Principal"]
    )
    before_end_of_fixed_loan_stash = df_schedule_variable_before_end_of_fixed_loan.iloc[
        -2
    ]["Stash"]
    st.write(
        "Principal & Stash at end of fixed loan term: "
        + f"\\${before_end_of_fixed_loan_balance:,.0f}"
        + " & "
        + f"\\${before_end_of_fixed_loan_stash:,.0f}"
    )

    df_schedule_variable["Schedule"] = "default"
    df_schedule_variable_wo_extra["Schedule"] = "wo/ extra repayment"
    df_schedule_variable_merged = (
        pd.concat([df_schedule_variable, df_schedule_variable_wo_extra])
        if show_other_schedules
        else df_schedule_variable
    )

    with st.expander("Principal and Stash over time"):

        fig1a = px.scatter(
            df_schedule_variable_merged,
            x="Date",
            y="Principal",
            color="Schedule" if show_other_schedules else None,
        )
        fig1a.update_layout(
            title={"text": "Principal / Variable", "x": 0.5, "xanchor": "center"}
        )
        fig1a.update_traces(marker=dict(size=3))
        fig1a.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
        fig1a.update_yaxes(title_text="Principal ($)")

        st.plotly_chart(fig1a, key="1av")

        principal_smaller_offset = df_schedule_variable[
            df_schedule_variable["Principal"] <= extracted_offset
        ]

        fig1b = px.scatter(
            df_schedule_variable_merged,
            x="Date",
            y="Stash",
            color="Schedule" if show_other_schedules else None,
        )
        fig1b.update_layout(
            title={"text": "Stash / Variable", "x": 0.5, "xanchor": "center"}
        )
        fig1b.update_traces(marker=dict(size=3))
        fig1b.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
        fig1b.update_yaxes(title_text="Stash ($)")

        st.plotly_chart(fig1b, key="1bv")

        if len(principal_smaller_offset) > 0:
            principal_smaller_offset_first_date = principal_smaller_offset.iloc[0][
                "Date"
            ]
            st.write(
                "Date when principal smaller than offset for the first time: "
                + principal_smaller_offset_first_date.strftime("%d/%m/%Y")
            )

            if principal_smaller_offset_first_date < fixed_loan_end:
                principal_smaller_offset_second_date = df_schedule_variable[
                    (df_schedule_variable["Principal"] <= extracted_offset)
                    & (df_schedule_variable["Date"] > fixed_loan_end)
                ].iloc[0]["Date"]
                st.write(
                    "Date when principal smaller than offset for the second time: "
                    + principal_smaller_offset_second_date.strftime("%d/%m/%Y")
                )

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
        if show_other_schedules
        else interest_plot_variable
    )

    with st.expander("Interest over time"):

        fig2 = px.scatter(
            interest_plot_variable_merged,
            x="ScheduleYears",
            y="Interest",
            color="Schedule" if show_other_schedules else None,
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
        if show_other_schedules
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
            color="Schedule" if show_other_schedules else None,
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

    st.write("#### Fixed & Variable")

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
    st.write(
        "Time to go: "
        + f"{total_years_variable:.2f} yrs, till "
        + variable_loan_end.strftime("%d/%m/%Y")
    )
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

    if show_so_far_information:
        st.write("Effective loan amount: " + f"${effective_loan_amount:,.0f}")

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
            + f"${(total_repayments_so_far_fixed + total_repayments_so_far_variable):,.0f}"
            + f" ({(total_repayments_so_far_fixed + total_repayments_so_far_variable) /
                   (total_repayments_so_far_fixed + total_repayments_fixed +
                    total_repayments_so_far_variable + total_repayments_variable) * 100:,.1f}%)]"
        )
    percentage = f" ({(total_repayments_fixed + total_repayments_variable) /
                     (total_repayments_so_far_fixed + total_repayments_fixed +
                      total_repayments_so_far_variable + total_repayments_variable) * 100:,.1f}%)"
    st.write(
        ":blue[Total repayment to go: "
        + f"${(total_repayments_fixed + total_repayments_variable):,.0f}"
        + (percentage if show_so_far_information else "")
        + "]"
    )

    if show_fear_save_spend_invest_information:
        st.write(
            "--- hope -"
            + f"{hope_interest_change:,.2f}%"
            + " -> "
            + f"Δ=${(total_repayments_fixed + total_repayments_variable_hope
                     - total_repayments_fixed - total_repayments_variable):,.0f}"
            + f" (-{total_years_variable - total_years_variable_hope:.2f} yrs)"
        )
        st.write(
            "--- fear +"
            + f"{fear_interest_change:,.2f}%"
            + " -> "
            + f"Δ=${(total_repayments_fixed + total_repayments_variable_fear 
                     - total_repayments_fixed - total_repayments_variable):,.0f}"
            + f" (+{total_years_variable_fear - total_years_variable:.2f} yrs)"
        )
        st.write(
            "--- save "
            + f"\\${save_amount:,.0f}"
            + " -> "
            + f"Δ=${(total_repayments_variable_save - total_repayments_variable):,.0f}"
        )
        st.write(
            "--- spend "
            + f"\\${spend_amount:,.0f}"
            + " -> "
            + f"Δ=${(total_repayments_variable_spend - total_repayments_variable):,.0f}"
        )
        st.write(
            "--- invest "
            + f"\\${invest_cost_amount:,.0f}"
            + ", win "
            + f"\\${invest_win_amount:,.0f}"
            + " "
            + invest_win_cycle.simple_str()
            + ", "
            + str(int(invest_win_duration.days / 365))
            + " yrs"
        )
        investment_result = (
            total_repayments_variable_invest
            - total_repayments_variable
            - extra_win_for_us_invest
        )
        st.write(
            f"... -> Δ=${(investment_result):,.0f} ("
            + ("profit" if investment_result < 0 else "loss")
            + ")"
        )
    if show_so_far_information:
        st.write(
            ":blue[Total repayment so far & to go: "
            + f"${(
            total_repayments_so_far_fixed + total_repayments_fixed +
            total_repayments_so_far_variable + total_repayments_variable):,.0f}]"
        )
