from decimal import Decimal
import pandas as pd


### Shared constants and config type


def to_decimal(value: str):
    if value:
        return Decimal(value.replace(',', '').replace('$', ''))
    return Decimal(0)


class ColName:
    ID = 'tid'
    DATE = 'date'
    TYPE = 'type' # account/transaction type
    DESCRIPTION = 'description'
    AMOUNT = 'amount'
    BALANCE = 'balance'
    ACCOUNT = 'account'
    CATEGORY = 'category'
    AMOUNT2 = 'amount2'


class TypeName:
    CHECKING = 'checking'
    SAVING = 'saving'
    CREDIT_CARD = 'credit_card'
    INVESTMENT = 'investment'
    RETIREMENT = 'retirement'


class CategoryName:
    SALARY = 'salary'
    CREDIT_CARD = 'pay_credit_card'
    UTILITY = 'utility'
    INTEREST = 'interest'
    MORTGAGE = 'mortgage'
    TRANSFER = 'transfer'
    CASH_OUT = 'cash_out'
    CARE_SERVICE = 'care_service'
    TAX_REFUND = 'tax_refund'
    INTERNAL = 'internal_transfer'
    TRANSPORTATION = 'transportation'
    OTHER = 'other'


class SummarizeName:
    TOTAL = '[TOTAL]'
    INCOME = '[INCOME]'
    EXPENSE = '[EXPENSE]'
    ALL = '[ALL]'


class AccountSettings:
    def __init__(self, friendlyName, idSuffix, accountType, skipRows, colCount, colMapping, postAction = None) -> None:
        self.name = friendlyName
        self.suffix = idSuffix
        self.type = accountType
        self.skip_rows = skipRows
        self.columns = colCount
        self.mapping = colMapping # column offsets (0-base) for Date, Description, Amount, Balance, Category and Amount2. -1 for no mapping.
        self.post_action = postAction

    def prepare_read(self):
        colums = [ 'p' + str(num) for num in range(self.columns)]
        names = [ColName.DATE, ColName.DESCRIPTION, ColName.AMOUNT, ColName.BALANCE, ColName.CATEGORY, ColName.AMOUNT2]
        converters = { ColName.DATE: (lambda x: pd.to_datetime(x, format='%m/%d/%Y')), 
                       ColName.AMOUNT: to_decimal,
                       ColName.BALANCE: to_decimal,
                       ColName.AMOUNT2: to_decimal}
        results = []
        for id in range(len(self.mapping)):
            mapTo = self.mapping[id]
            if mapTo >= 0:
                colums[mapTo] = names[id]
                results.append(names[id])
            else:
                if id < 3:
                    raise ValueError('Missing mapping for required column {0}'.format(names[id]))
                if names[id] in converters:
                    converters.pop(names[id])
        return colums, converters, results