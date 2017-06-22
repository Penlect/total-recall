import os
from flask import Flask, render_template, request, jsonify

from random import randint
from pprint import pprint

app = Flask(__name__)


@app.route('/create')
def create():
    return render_template('create.html')

@app.route('/numbers', methods=['POST'])
def numbers():
    if request.method == 'POST':
        d = dict(request.form)
        return str(d)
    return 'Thanks!'

@app.route('/cards', methods=['POST'])
def cards():
    if request.method == 'POST':
        d = dict(request.form)
        return str(d)
    return 'Thanks!'

@app.route('/words', methods=['POST'])
def words():
    if request.method == 'POST':
        d = dict(request.form)
        return str(d)
    return 'Thanks!'

@app.route('/dates', methods=['POST'])
def dates():
    if request.method == 'POST':
        d = dict(request.form)
        return str(d)
    return 'Thanks!'

@app.route('/recall/<string:key>')
def recall(key):
    key_file = f'database/{key}.txt'
    if not os.path.isfile(key_file):
        return f'No such key exsists: {key}'
    data = [str(randint(0, 9)) for _ in range(5*10)]
    with open(key_file, 'w') as file:
        file.write(';'.join(data))
    return render_template('numbers.html', nr_rows=5, nr_cols=10, key=key)


def _arbeiter(key, dictionary):
    pass


@app.route('/arbeiter', methods=['POST'])
def arbeiter():
    if request.method == 'POST':
        d = dict(request.form)
        resp = dict()
        key = 'abc123'
        with open(f'database/{key}.txt', 'r') as file:
            data = file.read().split(';')
            for key in d:
                id_ = int(key.split('_')[-1].strip())
                if d[key][0].strip():
                    resp[key] = data[id_] == d[key][0]
                else:
                    resp[key] = None
        app.logger.info(resp)
        return jsonify(resp)
    else:
        print('Wrong method!')