from common import ColName, CategoryName, SummarizeName
from loader import load, list_ranges, range_query

'''
Handle banking data (checking and saving accounts) for display.
'''
class Banking:
    def __init__(self, querystr: str = None) -> None:
        self._query_str = range_query(querystr, ColName.DATE) if querystr else None

    @property
    def transactions(self):
        if not hasattr(self, '_transactions'):
            self.load_transactions()
        return self._transactions

    @property
    def income_count(self):
        querystr = '{0} >= 0 and {1} != "{2}"'.format(ColName.AMOUNT, ColName.CATEGORY, CategoryName.INTERNAL)
        return len(self.transactions.query(querystr))

    @property
    def expense_count(self):
        querystr = '{0} < 0 and {1} != "{2}"'.format(ColName.AMOUNT, ColName.CATEGORY, CategoryName.INTERNAL)
        return len(self.transactions.query(querystr))

    @property
    def ranges(self):
        if not hasattr(self, '_ranges'):
            self.load_transactions()
        return self._ranges

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

    def load_transactions(self) -> None:
        self._transactions = load()
        self._ranges = list_ranges(self._transactions.iloc[0, 0], self._transactions.iloc[-1, 0])
        if self._query_str:
            self._transactions = self._transactions.query(self._query_str)

    '''
    Load balances by date and account, also aggregate the running total balances
    '''
    def load_balances(self) -> None:
        bacols = [ColName.DATE, ColName.ACCOUNT, ColName.BALANCE, ColName.AMOUNT]
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
                open_balances[acct] = bal - row[ColName.AMOUNT]
            for rs in results:
                if rs[0] == 'x':
                    rs.append(datestr)
                elif rs[0] == acct:
                    spots = len(results[0]) - len(rs)
                    for i in range(spots - 1):
                        rs.append(rs[-1] if len(rs) > 1 else open_balances[acct])
                    rs.append(bal)
                elif len(rs) > 1:
                    rs.append(rs[-1])
        for i in range(1, len(results[0])):
            sumamt = sum([rs[i] for rs in results if rs[0] != 'x'])
            basum.append(sumamt)
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