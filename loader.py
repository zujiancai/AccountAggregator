from common import ColName, CategoryName
from config import LoaderSettings, CategoryMapping, DATA_DIR, RESULT_FILE_NAME
import os
import pandas as pd
import re


### Ingest and retrieve all data from backend


'''
Sort transaction in time order, aggregate amounts to verify balances being updated correctly.
'''
def sort_and_verify(df: pd.DataFrame):
    errors = []
    if len(df) > 1:
        # ensure rows are in time order
        if df[ColName.DATE][0] == df[ColName.DATE][1]:
            if df[ColName.BALANCE][0] - df[ColName.AMOUNT][0] == df[ColName.BALANCE][1]:
                df = df.iloc[::-1].reset_index(drop=True)
        elif df[ColName.DATE][0] > df[ColName.DATE][1]:
            df = df.iloc[::-1].reset_index(drop=True)
        current_bal = df[ColName.BALANCE][0] - df[ColName.AMOUNT][0]
        for idx, row in df.iterrows():
            if row[ColName.BALANCE] - row[ColName.AMOUNT] != current_bal:
                errors.append('Unexpected balance {} for {} (amount: {}, balance: {}) at {}.'.format(
                    current_bal, row[ColName.DESCRIPTION], row[ColName.AMOUNT], row[ColName.BALANCE], idx))
            current_bal = row[ColName.BALANCE]
    return df, errors


'''
Use description or category column value to determine internal category name by config
'''
def resolve_category(desc: str) -> str:
    if not desc:
        return CategoryName.OTHER
    for mapping in CategoryMapping:
        if re.search(mapping[0], desc):
            return mapping[1]
    return CategoryName.OTHER


'''
Ingest transactions from raw files by config
'''
def ingest(overwrite = False) -> None:
    if overwrite:
        df = pd.DataFrame()
    else:
        df = load(default = pd.DataFrame())
    for filename in sorted(os.listdir(DATA_DIR)):
        filename = filename.upper()
        filepath = os.path.join(DATA_DIR, filename)
        if re.search('^.*_.+\.CSV$', filename):
            prefix = filename[:filename.index('_')]
            if prefix in LoaderSettings:
                settings = LoaderSettings[prefix]
                columns, converters, results = settings.prepare_read()
                res = pd.read_csv(filepath, names=columns, skiprows=settings.skip_rows, converters=converters, usecols=results, index_col=False, 
                                  on_bad_lines='warn', keep_default_na=False)
                if settings.post_action:
                    res = settings.post_action(res)
                print('Read {} records from file: {}'.format(len(res), filename))
                if res is not None and len(res) > 0:
                    if ColName.BALANCE in res.columns:
                        (res, err) = sort_and_verify(res)
                        if len(err) > 0:
                            print('Found {} errors when aggregating balance!'.format(len(err)))
                            for oe in err:
                                print(' - {}'.format(oe))
                            print('File is not merged to result due to error!')
                            return
                        print('Sorted and verified balances.')
                    res[ColName.ACCOUNT] = settings.name
                    res[ColName.TYPE] = settings.type
                    res[ColName.ID] = range(1, len(res) + 1)
                    res[ColName.ID] = res.apply(lambda x: x[ColName.DATE].strftime('%Y%m%d') + '{0:04d}{1}'.format(x[ColName.ID], settings.suffix), axis=1)
                    if not ColName.CATEGORY in res.columns:
                        res[ColName.CATEGORY] = res.apply(lambda x: resolve_category(x[ColName.DESCRIPTION]), axis=1)
                    else:
                        res[ColName.CATEGORY] = res.apply(lambda x: resolve_category(x[ColName.CATEGORY]), axis=1)
                    if not ColName.BALANCE in res.columns:
                        res[ColName.BALANCE] = 0
                    df = pd.concat([df, res], ignore_index=True, sort=False).drop_duplicates(subset=[ColName.DATE, ColName.DESCRIPTION, ColName.AMOUNT])
    df.sort_values(by=[ColName.ID], ignore_index=True, inplace=True)
    df.to_pickle(os.path.join(DATA_DIR, RESULT_FILE_NAME))
    print('Written results to {}'.format(RESULT_FILE_NAME))


'''
Load vanilla dataframe from result file
'''
def load(default = None) -> pd.DataFrame:
    resultpath = os.path.join(DATA_DIR, RESULT_FILE_NAME)
    if os.path.exists(resultpath):
        return pd.read_pickle(resultpath)
    else:
        return default


'''
Set internal transfers for transactions that have additive inverse amount. They should not be counted as income nor expense.
    - dry_run: when it is set, only return the potential transactions, but no updates. Default is false.
'''
def resolve_internal(dry_run = False) -> pd.DataFrame:
    df = load()
    if df is None or len(df) == 0:
        return None
    df = df[df[ColName.CATEGORY] != CategoryName.INTERNAL]
    results = []
    for idx, row in df.iterrows():
        targets = df[(df[ColName.AMOUNT] == -row[ColName.AMOUNT]) & (df[ColName.ACCOUNT] != row[ColName.ACCOUNT])][ColName.ID].tolist()
        if len(targets) > 0:
            results.extend(targets)
    results = list(dict.fromkeys(results)) # Dedupe the result list
    if not dry_run:
        df.loc[df[ColName.ID].isin(results), ColName.CATEGORY] = CategoryName.INTERNAL
        df.to_pickle(os.path.join(DATA_DIR, RESULT_FILE_NAME))
        print('Transactions in return have been updated with new category.')
    else:
        print('No change has been made for dry-run. Please check return for potential internal transfers.')
    return df[df[ColName.ID].isin(results)]
