from decimal import Decimal
from flask import Flask, request, render_template
import json

from banking import Banking
from common import ColName, SummarizeName, CategoryName
from loader import range_query


app = Flask(__name__)


def error_response(message: str, error: int):
    return render_template('error.html', code=error, desc=message), error


@app.template_filter()
def dectojson(input):
    def decimal_default(data):
        if isinstance(data, Decimal):
            return float(data)
        raise TypeError
    return json.dumps(input, default=decimal_default)


@app.route('/')
@app.route('/banking')
def banking():
    rg = request.args.get('date')
    data = Banking(rg) if rg and len(rg) > 0 else Banking()
    print('[{0}]'.format(rg if rg and len(rg) > 0 else SummarizeName.ALL))
    return render_template('banking.html', bkg=data, curr=(rg if rg and len(rg) > 0 else SummarizeName.ALL))


@app.route('/records', methods=['GET', 'POST'])
def records():
    query_str = ''
    sort_by = ColName.ID
    sort_asc = True
    show_rows = 20
    if request.method == 'POST':
        query_str = request.form['querystr']
        sort_by = request.form.get('sortby')
        sort_asc = bool(request.form.getlist('sortasc'))
        show_rows = int(request.form.get('showrows'))
    else:
        datestr = request.args.get('date')
        category = request.args.get('cat')
        iostr = request.args.get('type')
        if datestr and len(datestr) > 0:
            date_query = range_query(datestr, ColName.DATE)
            if date_query == datestr:
                return error_response('Cannot parse as date or time period: {}.'.format(datestr), 400)
            else:
                query_str = date_query
        if category and len(category) > 0:
            cats = [getattr(CategoryName, x) for x in dir(CategoryName) if not x.startswith('__')]
            if query_str and len(query_str) > 0:
                query_str += ' and ' 
            else:
                query_str = ''
            category = category.lower()
            if category in cats:
                query_str += '{0} == "{1}"'.format(ColName.CATEGORY, category)
            else:
                return error_response('Unsupported category name: {}.'.format(category), 400)
        if iostr and len(iostr) > 0:
            if query_str and len(query_str) > 0:
                query_str += ' and ' 
            else:
                query_str = ''
            iostr = iostr.lower()
            if iostr.lower() == 'income':
                query_str += '{0} >= 0'.format(ColName.AMOUNT)
            elif iostr.lower() == 'expense':
                query_str += '{0} < 0'.format(ColName.AMOUNT)
            else:
                return error_response('Unsupported type name: {}. Please use income or expense.'.format(iostr), 400)
        show_rows = 0 if len(query_str) > 0 else 20
    if query_str and len(query_str) > 0:
        trx = Banking(query_str).transactions
    else:
        trx = Banking().transactions
    trx = trx.sort_values(by=[sort_by], ascending=sort_asc, ignore_index=True)
    result_count = len(trx)
    if show_rows > 0 and result_count > show_rows:
        trx = trx.head(show_rows)
    return render_template('records.html', cols=list(trx), data=list(trx.values), query=query_str.replace('"', "'"), sortby=sort_by, asc=sort_asc, \
                           rows=show_rows, total=result_count, showed=len(trx))


@app.route('/about')
def about():
    return render_template('about.html')
