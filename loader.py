from datetime import datetime
from common import ColName, CategoryName, SummarizeName
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


'''
Set transaction category to new value in batch. targets is a list of transaction Id to update.
'''
def update_category(targets: list, newCat: str) -> pd.DataFrame:
    cats = [getattr(CategoryName, x) for x in dir(CategoryName) if not x.startswith('__')]
    if newCat not in cats:
        print('Unsupported category: {}'.format(newCat))
        return None
    df = load()
    if df is None or len(df) == 0:
        return None
    df.loc[df[ColName.ID].isin(targets), ColName.CATEGORY] = newCat
    df.to_pickle(os.path.join(DATA_DIR, RESULT_FILE_NAME))
    print('Transactions in return have been updated with new category.')
    return df[df[ColName.ID].isin(targets)]


'''
Convert range query name to dataframe query condition: 2021 -> entire calendar year of 2021; 2021Q2 -> 2021 Quarter 2; 2021-10 -> Octorber of 2021
'''
def range_query(query_raw: str, colname: str) -> str:
    query_raw = query_raw.strip()
    if query_raw == SummarizeName.ALL:
        return None
    if re.search('^\d{4}$', query_raw):
        return "{0} >= '{1}-01-01' and {0} <= '{1}-12-31'".format(colname, query_raw)
    elif re.search('^\d{4}Q[1-4]$', query_raw):
        qdata = query_raw.split('Q')
        qnum = int(qdata[1]) - 1
        qtomon = [ "{0} >= '{1}-01-01' and {0} <= '{1}-03-31'",
                   "{0} >= '{1}-04-01' and {0} <= '{1}-06-30'", 
                   "{0} >= '{1}-07-01' and {0} <= '{1}-09-30'",
                   "{0} >= '{1}-10-01' and {0} <= '{1}-12-31'"]
        return qtomon[qnum].format(colname, qdata[0])
    elif re.search('^\d{4}-(0[1-9]|1[0-2])$', query_raw):
        mdata = query_raw.split('-')
        myear = int(mdata[0])
        mmonth = int(mdata[1])
        if mmonth == 12:
            return "{0} >= '{1}-12-01' and {0} < '{2}-01-01'".format(colname, myear, myear + 1)
        else:
            return "{0} >= '{1}-{2:02d}-01' and {0} < '{1}-{3:02d}-01'".format(colname, myear, mmonth, mmonth + 1)
    elif re.search('^\d{4}-(0[1-9]|1[0-2])-[0-3][0-9]$', query_raw):
        try:
            datetime.strptime(query_raw, '%Y-%m-%d')
            return("{0} == '{1}'".format(colname, query_raw))
        except ValueError:
            pass
    return query_raw


'''
List available range queries (year, quarter, and month) between two timestamps
'''
def list_ranges(start_date : pd.Timestamp, end_date: pd.Timestamp) -> list:
    results = list(reversed(range(start_date.year, end_date.year + 1)))
    qres = []
    mres = []
    for yr in results:
        startq = (end_date.month - 1) // 3 + 1 if yr == end_date.year else 4
        endq = (start_date.month - 1) // 3 if yr == start_date.year else 0
        for x in range(startq, endq, -1):
            qres.append('{0}Q{1}'.format(yr, x))
        startm = end_date.month if yr == end_date.year else 12
        endm = start_date.month - 1 if yr == start_date.year else 0
        for x in range(startm, endm, -1):
            mres.append('{0}-{1:02d}'.format(yr, x))
    results = [SummarizeName.ALL] + [str(x) for x in results]
    results.extend(qres)
    results.extend(mres)
    return results
