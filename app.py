import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st
import account_reader
import account_interpreter
import home_loan

# get data

df_in = account_reader.get_dataframe(date_from=pd.to_datetime("2024-09-16"))
df_in = account_interpreter.add_interest_information(df_in)

dates_in = df_in["DateSeries"].drop_duplicates().tolist()

# setup

st.set_page_config(layout="wide")

st.write("# Home Loan")

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

selected_date = st.selectbox("Select a day:", dates_in)

selected_balance = account_interpreter.get_total_balance_over_time(
    df_in,
    selected_dates=[selected_date],
    add_col_with_account_name=True,
    return_positive_balance=True,
)["Balance"].iloc[0]

# plot

P = selected_balance
N = 25
k = 12
R0 = 0.062

Rs = []
# Rs.append((24, 0.085))
# Rs.append((48, 0.065))
Rs = pd.DataFrame(Rs, columns=["month", "rate"])
Rs.set_index("month", drop=False, inplace=True)

Os = []
Os.append((0, 200000))
# for month in range(1, N * 12):
#    Os.append((month, 2000))
Os = pd.DataFrame(Os, columns=["month", "amount"])
Os.set_index("month", drop=False, inplace=True)

myLoan1 = home_loan.HomeLoan("Loan 1", N=N, k=k, P=P, R0=R0)
myLoan1.print()
plan1 = myLoan1.simulate()

fig, ax = plt.subplots()
home_loan.plot(ax, myLoan1.label, plan1)
st.pyplot(fig)
