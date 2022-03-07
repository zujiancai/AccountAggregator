from common import AccountSettings, TypeName, CategoryName, ColName
import pandas as pd


### All configuration comes here


DATA_DIR = '..\TestData\AccountActivities' # Directory for raw files and results
RESULT_FILE_NAME = 'Aggregated.pkl' # Result file name for bank accounts


def merge_debit_credit(df: pd.DataFrame) -> pd.DataFrame:
    df[ColName.AMOUNT] = df.apply(lambda x: x[ColName.AMOUNT] - x[ColName.AMOUNT2], axis=1)
    return df[[ColName.DATE, ColName.DESCRIPTION, ColName.AMOUNT, ColName.BALANCE]]


# Raw file format configuration for loading transactions
#    Use the file name prefix as key. E.g. file name ABC_EFG.csv will use prefix ABC.
#    AccountSettings parameters:
#        1. Friendly name of the account which will be added to the transaction row.
#        2. Transaction Id suffix
#        3. Account type
#        4. Rows to skip from the top of raw file
#        5. Columns count in raw file
#        6. Columns mapping from result as [date, description, amount, balance, category, amount2] to raw file.
#            - E.g. [3, 2, 1, 4, -1, -1] means result's date (first one) is mapped to raw file's fourth column (offset is 3 as 0-based).
#            - '-1' means no column to map, first 4 columns are required and cannot be -1.
#            - amount2 is for banks that use two columns for amount: one as credit and the other debit. Please see DISCOVERSAV for how it is used.
LoaderSettings = {
    "CHASE7475": AccountSettings('Chase Checking', 'JPMCHK', TypeName.CHECKING, 1, 7, [1, 2, 3, 5, -1, -1]),
    "CHASE2724": AccountSettings('Chase Saving', 'JPMSAV', TypeName.SAVING, 1, 7, [1, 2, 3, 5, -1, -1]),
    #"CHASE2604": AccountSettings('Chase Freedom CC', 'JPM1CC', TypeName.CREDIT_CARD, 1, 7, [1, 2, 5, -1, 3, -1]),
    "BACCHK": AccountSettings('BOA Checking', 'BACCHK', TypeName.CHECKING, 7, 4, [0, 1, 2, 3, -1, -1]),
    "BACSAV": AccountSettings('BOA Saving', 'BACSAV', TypeName.SAVING, 7, 4, [0, 1, 2, 3, -1, -1]),
    "1STTECHCHK": AccountSettings('FirstTech Checking', '1TCCHK', TypeName.CHECKING, 1, 13, [2, 7, 4, 10, -1, -1]),
    "1STTECHSAV": AccountSettings('FirstTech Saving', '1TCSAV', TypeName.SAVING, 1, 13, [2, 7, 4, 10, -1, -1]),
    "DISCOVERSAV": AccountSettings('Discover Saving', 'DISCVS', TypeName.SAVING, 1, 6, [0, 1, 4, 5, -1, 3], merge_debit_credit),
}


# Category mapping from description. Regular expression are checked in array index order.
CategoryMapping = [
    ('EDIPAYMENT', CategoryName.SALARY),
    ('CHASE CREDIT CRD|TARGET CARD|DISCOVER         E-PAYMENT|BANK OF AMERICA CREDIT CARD|CITI AUTOPAY|AMERICAN EXPRESS', CategoryName.CREDIT_CARD),
    ('EXTRNLTFR|ZELLE', CategoryName.TRANSFER),
    ('IRS TREAS', CategoryName.TAX_REFUND),
    ('MORTGAGE', CategoryName.MORTGAGE),
    ('PUGET SOUND ENER|Bills & Utilities', CategoryName.UTILITY),
    ('INTEREST|^CREDIT$|^CREDIT DIVIDEND$', CategoryName.INTEREST),
    ('KIDDIE ACADEMY', CategoryName.CARE_SERVICE)
]
