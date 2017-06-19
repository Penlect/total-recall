
from flask import Flask, render_template, request, jsonify

from random import randint

app = Flask(__name__)

@app.route('/numbers')
def numbers():
    return render_template('numbers.html', nr_rows=3, nr_cols=10)

@app.route('/arbeiter', methods=['POST'])
def arbeiter():
    if request.method == 'POST':

        d = dict(request.form)
        for key in d:
            d[key] = bool(randint(0, 1))
        return jsonify(d)
    else:
        print('Wrong method!')