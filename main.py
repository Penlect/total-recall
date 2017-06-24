
import os
import re
from flask import Flask, render_template, request, jsonify, flash

import random
from pprint import pprint
import json
import hashlib

import xls

app = Flask(__name__)
app.secret_key = 'some_secret'


def sha(string):
    h = hashlib.sha1(string.encode())
    h.update(str(random.random()).encode())
    return h.hexdigest()[0:6]


def add_to_database(blob):
    hash_candidate = str(blob)
    while True:
        h = sha(hash_candidate)
        output_file = f'database/{h[0:2]}/{h[2:6]}.json'
        if os.path.isfile(output_file):
            hash_candidate = h
        else:
            break
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as file:
        json.dump(blob, file)
    return h


@app.route('/generate')
def generate():
    return render_template('generate.html')


@app.route('/create')
def create():
    return render_template('create.html')


@app.route('/numbers', methods=['POST'])
def numbers():
    if request.method == 'POST':
        # The request form is a ImmutableMultiDict
        form = request.form
        if 'data' in form:
            blob = {
                'discipline': form['base'].lower(),
                'recall_time': int(form['recall_time']),
                'correction': form['correction'].lower(),
                # Use a regular expression to yield all numbers found
                # in the input data string.
                'data': tuple(int(digit) for digit in
                              re.findall('\d', form['data']))
            }
            if blob['discipline'] == 'binary' and len(set(blob['data'])) > 2:
                return 'ERROR binary but decimal?'

            h = add_to_database(blob)
            app.logger.info(f'Created blob for numbers: {h}')

            w = xls.NumberTable(name='Numbers', recall_key=h.upper(),
                                recall_time=blob['recall_time'],
                                language=blob['discipline'])

            for n in blob['data']:
                w.add_item(n)
            w.save(blob['discipline'] + '.xls')

            return str(blob)


@app.route('/words', methods=['POST'])
def words():
    if request.method == 'POST':
        # The request form is a ImmutableMultiDict
        form = request.form
        if 'data' in form:
            blob = {
                'discipline': 'words',
                'recall_time': int(form['recall_time']),
                'correction': form['correction'].lower(),
                'data': tuple(
                    word.strip() for word in form['data'].lower().split('\n')
                    if word.strip())
            }

            h = add_to_database(blob)
            app.logger.info(f'Created blob for words: {h}')

            w = xls.WordTable(name='Words', recall_key=h.upper(),
                                recall_time=blob['recall_time'],
                                language=blob['discipline'])

            for n in blob['data']:
                w.add_item(n)
            w.save(blob['discipline'] + '.xls')

            return str(blob)


@app.route('/dates', methods=['POST'])
def dates():
    if request.method == 'POST':
        # The request form is a ImmutableMultiDict
        form = request.form
        if 'data' in form:
            historical_dates = list()
            for line in form['data'].split('\n'):
                if line.strip():
                    date, story = line.split(maxsplit=1)
                    historical_dates.append((date.strip(), story.strip()))
            blob = {
                'discipline': 'dates',
                'recall_time': int(form['recall_time']),
                'correction': form['correction'].lower(),
                'data': tuple(historical_dates)
            }

            h = add_to_database(blob)
            app.logger.info(f'Created blob for words: {h}')

            w = xls.DatesTable(name='Dates', recall_key=h.upper(),
                                recall_time=blob['recall_time'],
                                language=blob['discipline'])

            for n in blob['data']:
                w.add_item(n)
            w.save(blob['discipline'] + '.xls')

            return str(blob)


@app.route('/recall/<string:key>')
def recall(key):
    blob_file = f'database/{key[0:2]}/{key[2:6]}.json'
    if not os.path.isfile(blob_file):
        return f'No such key exsists: {key}'
    with open(blob_file, 'r') as file:
        blob = json.load(file)
    return render_template('numbers.html', key=key, blob=blob)


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