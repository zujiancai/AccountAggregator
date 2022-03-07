from decimal import Decimal
from flask import Flask, render_template
import json

from banking import Banking


app = Flask(__name__)


@app.template_filter()
def dectojson(input):
    def decimal_default(data):
        if isinstance(data, Decimal):
            return float(data)
        raise TypeError
    return json.dumps(input, default=decimal_default)


@app.route('/')
def banking():
    return render_template('banking.html', bkg=Banking())


@app.route('/about')
def about():
    return render_template('about.html')
