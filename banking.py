from ast import Pass
from unittest import result
from common import ColName, CategoryName, SummarizeName
from loader import load

'''
Handle banking data (checking and saving accounts) for display.
'''
class Banking:
    def __init__(self, querystr = None) -> None:
        self._querystr = querystr

    @property
    def transactions(self):
        if not hasattr(self, '_transactions'):
            if self._querystr:
                self._transactions = load().query(self._query_str)
            else:
                self._transactions = load()
        return self._transactions

    @property
    def total_open(self):
        if not hasattr(self, '_total_open'):
            self.load_balances()
        return self._total_open

    @property
    def total_close(self):
        if not hasattr(self, '_total_close'):
            self.load_balances()
        return self._total_close

    @property
    def balances(self):
        if not hasattr(self, '_balances'):
            self.load_balances()
        return self._balances

    @property
    def total_income(self):
        if not hasattr(self, '_total_income'):
            self.load_income_expense()
        return self._total_income

    @property
    def total_expense(self):
        if not hasattr(self, '_total_expense'):
            self.load_income_expense()
        return self._total_expense

    @property
    def income_expense(self):
        if not hasattr(self, '_income_expense'):
            self.load_income_expense()
        return self._income_expense

    @property
    def income_categories(self):
        if not hasattr(self, '_income_categories'):
            self.load_categories()
        return self._income_categories

    @property
    def expense_categories(self):
        if not hasattr(self, '_expense_categories'):
            self.load_categories()
        return self._expense_categories

    '''
    Load balances by date and account, also aggregate the running total balances
    '''
    def load_balances(self) -> None:
        bacols = [ColName.DATE, ColName.ACCOUNT, ColName.BALANCE]
        if self.transactions is None or len(self.transactions) == 0:
            return
        df = self.transactions[bacols].drop_duplicates(subset=[ColName.DATE, ColName.ACCOUNT], keep='last')
        basum = [SummarizeName.TOTAL]
        results = [] # Expected output: [['x', '2021-10-01', '2021-10-08', '2021-11-20'], ['account1', 100, 120, 180], ['account2', 30, 25, 33]]
        results.append(['x'])
        open_balances = {} # Track open balances for all accounts
        for acct in df[ColName.ACCOUNT].drop_duplicates().tolist():
            results.append([acct])
        for idx, row in df.iterrows():
            datestr = row[ColName.DATE].strftime('%Y-%m-%d')
            acct = row[ColName.ACCOUNT]
            bal = row[ColName.BALANCE]
            if not acct in open_balances:
                open_balances[acct] = bal
            filled = sum(1 if len(x) > 1 else 0 for x in results if x[0] != 'x' and x[0] != acct)
            if filled < len(results) - 2: # Some account misses balance in the result
                for rs in results:
                    if rs[0] == acct:
                        if len(rs) > 1:
                            rs[-1] = bal
                        else:
                            rs.append(bal)
            else: # All accounts have balance in the result
                total_balance = 0
                overwrite = (results[0][-1] == datestr)
                for rs in results:
                    if rs[0] == 'x':
                        rs.append(datestr) if not overwrite else Pass
                    elif rs[0] == acct:
                        if overwrite:
                            rs[-1] = bal
                        else:
                            rs.append(bal)
                    elif len(rs) < len(results[0]):
                        rs.append(rs[-1])
                    if rs[0] != 'x':
                        total_balance += rs[-1]
                if overwrite:
                    basum[-1] = total_balance
                else:
                    basum.append(total_balance)
        if len(basum) > 1:
            self._total_open =  sum(open_balances.values())
            self._total_close = basum[-1]
        results.append(basum)
        self._balances = results

    '''
    Monthly income and expense comparison
    '''
    def load_income_expense(self) -> None:
        if self.transactions is None or len(self.transactions) == 0:
            return None
        df = self.transactions[self.transactions[ColName.CATEGORY] != CategoryName.INTERNAL].copy() # don't count internal transfers
        df[ColName.DESCRIPTION] = df.apply((lambda x: x[ColName.DATE].strftime('%Y-%m')), axis=1) # Reuse description for year-month
        df[ColName.TYPE] = df.apply((lambda x: SummarizeName.INCOME if x[ColName.AMOUNT] >= 0 else SummarizeName.EXPENSE), axis=1) # Reuse type for income or expense
        iot = df.groupby(by=[ColName.TYPE])[ColName.AMOUNT].sum()
        self._total_income = iot[SummarizeName.INCOME]
        self._total_expense = -iot[SummarizeName.EXPENSE]
        iom = df.groupby(by=[ColName.DESCRIPTION, ColName.TYPE])[ColName.AMOUNT].sum()
        results = []
        im = iom.loc[:, SummarizeName.INCOME]
        results.append(['x'] + im.index.tolist())
        results.append([SummarizeName.INCOME] + im.tolist())
        results.append([SummarizeName.EXPENSE] + [-val for val in iom.loc[:, SummarizeName.EXPENSE].tolist()])
        self._income_expense = results

    '''
    Overall comparison by category
    '''
    def load_categories(self) -> None:
        if self.transactions is None or len(self.transactions) == 0:
            return None
        df = self.transactions[self.transactions[ColName.CATEGORY] != CategoryName.INTERNAL].copy() # don't count internal transfers
        df[ColName.TYPE] = df.apply((lambda x: SummarizeName.INCOME if x[ColName.AMOUNT] >= 0 else SummarizeName.EXPENSE), axis=1) # Reuse type for income or expense
        ioc = df.groupby(by=[ColName.CATEGORY, ColName.TYPE])[ColName.AMOUNT].sum()
        ic = ioc.loc[:, SummarizeName.INCOME]
        self._income_categories = list(map(lambda x, y: [x, y], ic.index.tolist(), ic.tolist()))
        oc = ioc.loc[:, SummarizeName.EXPENSE]
        self._expense_categories = list(map(lambda x, y: [x, y], oc.index.tolist(), [-val for val in oc.tolist()]))