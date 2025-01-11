class HomeLoanPlanner:

    @staticmethod
    def get_recurring_payment_c(*, n, p, r):
        if p <= 0 or n == 0:
            return None
        return p * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

    def __init__(self, label, *, N, k, P, R0):
        self.label = label
        self.N = N
        self.k = k
        self.P = P
        self.R0 = R0

        self.n = self.N * self.k
        self.r0 = self.R0 / self.k
        self.c0 = self.get_recurring_payment_c(n=self.n, p=self.P, r=self.r0)
        self.m0 = self.c0 * self.k / 12
