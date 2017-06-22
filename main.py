import os
from flask import Flask, render_template, request, jsonify, flash

import random
from pprint import pprint
import json
import hashlib

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


@app.route('/create')
def create():
    return render_template('create.html')


@app.route('/numbers', methods=['POST'])
def numbers():
    if request.method == 'POST':
        # The request form is a ImmutableMultiDict
        data = request.form

        # Extract each required parameter
        base = data['base'].lower()
        nr_cols = int(data['nr_cols'])
        nr_rows = int(data['nr_rows'])
        recall_time = int(data['recall_time'])
        correction = data['correction'].lower()

        # Compute the numbers that will be memorized
        N = nr_cols*nr_rows
        if base == 'binary':
            max_ = 1
        elif base == 'decimal':
            max_ = 9
        numbers = [random.randint(0, max_) for _ in range(N)]

        # Package all data in a dictionary
        blob = {
            'discipline': base,
            'nr_cols': nr_cols,
            'nr_rows': nr_rows,
            'recall_time': recall_time,
            'correction': correction,
            'data': tuple(numbers)
        }

        h = add_to_database(blob)
        app.logger.info(f'Created blob for numbers: {h}')

        return jsonify(blob)


@app.route('/words', methods=['POST'])
def words():
    if request.method == 'POST':
        # The request form is a ImmutableMultiDict
        data = request.form

        # Extract each required parameter
        nr_rows = int(data['nr_rows'])
        recall_time = int(data['recall_time'])
        correction = data['correction'].lower()

        # Make everything lowercase
        words = data['data'].lower()
        # Split by newline
        words = words.split('\n')
        # Make sure to strip extra whitespace
        words = [word.strip() for word in words]
        # Drop empty words
        words = [word for word in words if word]
        # Shuffle the words randomly
        random.shuffle(words)

        # Package all data in a dictionary
        blob = {
            'discipline': 'words',
            'nr_rows': nr_rows,
            'recall_time': recall_time,
            'correction': correction,
            'data': tuple(words)
        }

        h = add_to_database(blob)
        app.logger.info(f'Created blob for words: {h}')

        return jsonify(blob)

@app.route('/dates', methods=['POST'])
def dates():
    if request.method == 'POST':
        # The request form is a ImmutableMultiDict
        data = request.form

        # Extract each required parameter
        recall_time = int(data['recall_time'])
        correction = data['correction'].lower()

        # Make everything lowercase
        stories = data['data'].lower()
        # Split by newline
        stories = stories.split('\n')
        # Make sure to strip extra whitespace
        stories = [story.strip() for story in stories]
        # Drop empty stories
        stories = [story for story in stories if story]

        # How many dates were found?
        N = len(stories)
        dates = [random.randint(1000, 2099) for _ in range(N)]

        historical_dates = list(zip(stories, dates))
        random.shuffle(historical_dates)

        # Package all data in a dictionary
        blob = {
            'discipline': 'dates',
            'recall_time': recall_time,
            'correction': correction,
            'data': tuple(historical_dates)
        }

        h = add_to_database(blob)
        app.logger.info(f'Created blob for historical dates: {h}')

        return jsonify(blob)

@app.route('/recall/<string:key>')
def recall(key):
    key_file = f'database/{key}.txt'
    if not os.path.isfile(key_file):
        return f'No such key exsists: {key}'
    data = [str(random.randint(0, 9)) for _ in range(5*10)]
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