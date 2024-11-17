import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import bank
import home_loan

df = bank.get_dataframe()

dates = df["Date"].drop_duplicates().tolist()

st.dataframe(df)

selected_date = st.selectbox("Select a row:", dates)

selected_row = df[df["Date"] == selected_date].iloc[0]

balance = int(-selected_row["Balance"])

print(balance)

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
