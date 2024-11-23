import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st
import account_reader
import account_interpreter
import home_loan

# get data

df_in = account_reader.get_dataframe()

# filters for accounts

st.set_page_config(layout="wide")

col1, col2, col3 = st.columns(3)
with col1:
    toggleFixed = st.toggle("Fixed", True)
with col2:
    toggleVariable = st.toggle("Variable", True)
with col3:
    toggleOffset = st.toggle("Offset", False)

df = pd.DataFrame(df_in)
if not toggleFixed:
    df = df[df["AccountName"] != "Fixed"]
if not toggleVariable:
    df = df[df["AccountName"] != "Variable"]
if not toggleOffset:
    df = df[df["AccountName"] != "Offset"]

dates = df["DateSeries"].drop_duplicates().tolist()

# dataframe as a table

st.dataframe(df)

# balance over time

df_balance_fixed = account_interpreter.get_balance_over_time(
    df, "Fixed", add_col_with_account_name=True, return_positive_balance=True
)
df_balance_variable = account_interpreter.get_balance_over_time(
    df, "Variable", add_col_with_account_name=True, return_positive_balance=True
)
df_balance_offset = account_interpreter.get_balance_over_time(
    df, "Offset", add_col_with_account_name=True, return_positive_balance=True
)

df_plot = pd.concat([df_balance_fixed, df_balance_variable, df_balance_offset])

fig = px.scatter(df_plot, x="DateSeries", y="Balance", color="Account")
fig.update_xaxes(title_text="Date", tickformat="%Y-%m-%d")
fig.update_yaxes(title_text="Balance")

st.plotly_chart(fig)

# data selectiom

selected_date = st.selectbox("Select a row:", dates)

selected_row = df[df["DateSeries"] == selected_date].iloc[0]

balance = abs(selected_row["Balance"])

st.text(balance)

print(balance)

# plot

P = balance
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
