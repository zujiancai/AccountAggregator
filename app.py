from decimal import Decimal
from flask import Flask, request, render_template
import json

from numpy import isin

from banking import Banking
from common import ColName


app = Flask(__name__)


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
    return render_template('banking.html', bkg=Banking())


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
    if query_str and len(query_str) > 0:
        trx = Banking(query_str).transactions
    else:
        trx = Banking().transactions
    trx = trx.sort_values(by=[sort_by], ascending=sort_asc, ignore_index=True)
    result_count = len(trx)
    if show_rows > 0 and result_count > show_rows:
        trx = trx.head(show_rows)
    return render_template('records.html', cols=list(trx), data=list(trx.values), query=query_str, sortby=sort_by, asc=sort_asc, rows=show_rows, total=result_count, showed=len(trx))


@app.route('/about')
def about():
    return render_template('about.html')
