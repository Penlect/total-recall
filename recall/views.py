
import os
import re
from flask import render_template, request, jsonify, url_for

import random
import time
from pprint import pprint
import json
import hashlib
from collections import namedtuple

from recall import app

# Todo: fix imports
import recall.xls

def sha(string):
    h = hashlib.sha1(string.encode())
    h.update(str(random.random()).encode())
    return h.hexdigest()[0:6]


DATABASE_WORDS = os.path.join(app.root_path, 'db_words.txt')
DATABASE_STORIES = os.path.join(app.root_path, 'db_stories.txt')
WordEntry = namedtuple('WordEntry', 'language value name date word_class')
StoryEntry = namedtuple('StoryEntry', 'language value name date')


def load_database(db_file, entry):
    with open(db_file, 'r', encoding='utf-8') as db_file:
        entries = set()
        for line in db_file:
            if line.strip():
                row_data = [x.strip() for x in line.split(';')]
                entries.add(entry(*row_data))
        return list(sorted(entries))


def save_database(db_file, entries):
    with open(db_file, 'w', encoding='utf-8') as db_file:
        lines = (';'.join(entry) for entry in sorted(entries))
        db_file.write('\n'.join(lines))


def unqiue_lines_in_textarea(data, lower=False):
    if lower:
        data = data.lower()
    return {line.strip() for line in data.split('\n') if line.strip()}


@app.route('/database/words', methods=['GET', 'POST'])
def manage_words_database():
    if request.method == 'GET':
        return render_template('db_words.html')


@app.route('/database/words/content', methods=['GET'])
def database_words_content():
    db_words = load_database(DATABASE_WORDS, WordEntry)
    return render_template('db_words_content.html', words=db_words)


@app.route('/database/words/modify', methods=['POST'])
def database_words_modify():
    """ Update word database and respond modifications table summary """
    modification_time = time.strftime('%Y-%m-%d %H:%M:%S')
    db_words = load_database(DATABASE_WORDS, WordEntry)
    if request.method == 'POST':
        form = request.form

        if form['pwd'].lower().strip() != 'minnsej':
            return 'Wrong password!'

        if not form['added_by'].strip():
            return 'Your name is mandatory!'

        if not form['data'].strip():
            return 'No words were added since Words input was empty!'

        # We can't check words in database only on the word value,
        # the language is needed as well. Two words might exists
        # with the same word value but different meaning in two
        # languages.
        db_lang_word = {f'{w.language};{w.value}':w for w in db_words}

        status = dict()
        data = unqiue_lines_in_textarea(form['data'], lower=True)
        for word in data:
            delete_me = word.startswith('delete:')
            w = WordEntry(
                language=form['language'].lower(),
                value=word.replace('delete:', ''),
                name=form['added_by'],
                date=modification_time,
                word_class=form['word_class'].lower()
            )
            lw = f'{w.language};{w.value}'
            if delete_me:
                if lw in db_lang_word:
                    status[db_lang_word[lw]] = 'deleted'
                    del db_lang_word[lw]
                else:
                    status[w] = 'failed_delete'
            elif lw in db_lang_word:
                if db_lang_word[lw].word_class != w.word_class:
                    db_lang_word[lw] = w
                    status[w] = 'updated'
                else:
                    status[db_lang_word[lw]] = 'already_exists'
            else:
                db_lang_word[lw] = w
                status[w] = 'added'

        new_words = list(sorted(set(db_lang_word.values())))
        save_database(DATABASE_WORDS, new_words)
        return render_template(
            'db_words_modification.html', words=new_words, status=status,
            modification_time=modification_time
        )


@app.route('/generate')
def generate():
    return render_template('generate.html')


@app.route('/create')
def create():
    return render_template('create.html')


class Blob:

    VALID_DISCIPLINES = {'binary', 'decimal', 'words', 'dates'}
    VALID_CORRECTIONS = {'kind', 'standard'}

    def __init__(self, *, discipline, memo_time, recall_time, correction, data: str,
                 language=None, nr_items=None, pattern=''):
        # Assign values and check for errors in input
        self.discipline = discipline.lower()
        if self.discipline not in self.VALID_DISCIPLINES:
            raise ValueError(f'Invalid discipline: "{discipline}". '
                             'Choose from ' + str(self.VALID_DISCIPLINES))
        self.recall_time = int(recall_time)
        if self.recall_time < 0:
            raise ValueError(f'Recall time cannot be negative: {self.recall_time}')
        self.correction = correction.lower()
        if self.correction not in self.VALID_CORRECTIONS:
            raise ValueError(f'Invalid correction: "{correction}". '
                             'Choose from ' + str(self.VALID_CORRECTIONS))

        self.memo_time = memo_time
        self.language = language.lower() if language is not None else None
        try:
            self.pattern = tuple(int(p) for p in pattern.split(','))
        except ValueError:
            self.pattern = None

        if data is None:
            # If data was not provided, we must generate it ourselves.
            # In order to do so we need to know how many items to
            # generate, + language if words or dates.
            assert nr_items is not None, 'Nr_items not provided to blob!'
            self.nr_items = int(nr_items)
            if self.discipline in {'words', 'dates'}:
                assert language is not None, 'Language not provided to blob!'

            if self.discipline == 'binary':
                self.data = tuple(random.randint(0, 1) for _ in range(self.nr_items))
            elif self.discipline == 'decimal':
                self.data = tuple(random.randint(0, 9) for _ in range(self.nr_items))
            elif self.discipline == 'words':
                words = [word.value for word in load_database(DATABASE_WORDS, WordEntry)]  # Language not yet supported
                random.shuffle(words)
                self.data = tuple(words[0:self.nr_items])
            elif self.discipline == 'dates':
                stories = [story.value for story in load_database(DATABASE_STORIES, StoryEntry)]  # Language not yet supported
                random.shuffle(stories)
                stories = stories[0:self.nr_items]
                dates = [random.randint(1000,2099) for _ in stories]
                self.data = tuple(zip(dates, stories))
            else:
                raise Exception(f'Data generation for discipline "{self.discipline}" not implemented.')

        else:
            # If data is provided, it's just a matter of parsing the data
            # from the string
            if self.discipline == 'binary':
                self.data = tuple(int(digit) for digit in re.findall('[01]', data))
            elif self.discipline == 'decimal':
                self.data = tuple(int(digit) for digit in re.findall('\d', data))
            elif self.discipline == 'words':
                self.data = tuple(word.strip() for word in data.lower().split('\n') if word.strip())
            elif self.discipline == 'dates':
                historical_dates = list()
                for line in data.split('\n'):
                    if line.strip():
                        date, story = line.split(maxsplit=1)
                        historical_dates.append((date.strip(), story.strip()))
                self.data = tuple(historical_dates)
            else:
                raise Exception(f'Data creation for discipline "{self.discipline}" not implemented.')

    def add_to_database(self):

        blob = { # Todo: add language
            'discipline': self.discipline,
            'recall_time': self.recall_time,
            'correction': self.correction,
            'pattern': self.pattern,
            'data': self.data
        }

        hash_candidate = str(blob)
        while True:
            h = sha(hash_candidate)
            output_file = os.path.join(app.root_path,
                                       f'database/{h[0:2]}/{h[2:6]}.json')
            if os.path.isfile(output_file):
                hash_candidate = h
            else:
                break
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as file:
            json.dump(blob, file)
        return h


@app.route('/numbers', methods=['POST'])
def numbers():
    if request.method == 'POST':
        # The request form is a ImmutableMultiDict
        form = request.form
        blob = Blob(
            discipline=form['base'],
            memo_time=form['memo_time'],
            recall_time=form['recall_time'],
            correction=form['correction'],
            data=form.get('data'),
            nr_items=form.get('nr_items'),
            pattern=form['pattern']
        )
        h = blob.add_to_database()
        app.logger.info(f'Created blob for numbers: {h}')

        # CREATE XLS DOCUMENT
        if blob.discipline == 'binary':
            table = recall.xls.get_binary_table
        elif blob.discipline == 'decimal':
            table = recall.xls.get_decimal_table
        else:
            raise ValueError('Invalid discipline for Numbers: "{blob.discipline}"')

        xls_filename = '{dis}_{nr}st_{mem_t}min_{rec_t}min_{pat}_{cor}.xls'.format(
            dis=blob.discipline.title(),
            nr=len(blob.data),
            mem_t=blob.memo_time,
            rec_t=blob.recall_time,
            pat=','.join([p.strip() for p in form['pattern'].split(',')]),
            cor=blob.correction.title()
        )
        t = table(
            title='Svenska Minnesförbundet',
            discipline=f'{blob.discipline.title()} Numbers, {len(blob.data)} st.',
            recall_key=h.upper(),
            memo_time=form['memo_time'],
            recall_time=blob.recall_time,
            pattern=form['pattern']
        )
        for n in blob.data:
            t.add_item(n)
        t.save(os.path.join(app.root_path, 'static/sheets/' + xls_filename))
        return render_template('memorize.html',
                               xls_download_link=url_for('static', filename='sheets/' + xls_filename),
                               xls_filename=xls_filename)


@app.route('/words', methods=['POST'])
def words():
    if request.method == 'POST':
        # The request form is a ImmutableMultiDict
        form = request.form
        blob = Blob(
            discipline='words',
            memo_time=form['memo_time'],
            recall_time=form['recall_time'],
            correction=form['correction'],
            data=form.get('data'),
            nr_items=form.get('nr_items'),
            language=form.get('language'),
            pattern=form['pattern']
        )
        h = blob.add_to_database()
        app.logger.info(f'Created blob for words: {h}')

        # CREATE XLS DOCUMENT
        xls_filename = '{dis}_{lang}_{nr}st_{mem_t}min_{rec_t}min_{pat}_{cor}.xls'.format(
            dis=blob.discipline.title(),
            lang=form['language'],
            nr=len(blob.data),
            mem_t=blob.memo_time,
            rec_t=blob.recall_time,
            pat=','.join([p.strip() for p in form['pattern'].split(',')]),
            cor=blob.correction.title()
        )
        t = recall.xls.get_words_table(
            title='Svenska Minnesförbundet',
            discipline=f'Words, {blob.language.title()}, {len(blob.data)} st.',
            recall_key=h.upper(),
            memo_time=form['memo_time'],
            recall_time=blob.recall_time,
            pattern=form['pattern']
        )
        for n in blob.data:
            t.add_item(n)
        t.save(os.path.join(app.root_path, 'static/sheets/' + xls_filename))
        return render_template('memorize.html',
                               xls_download_link=url_for('static', filename='sheets/' + xls_filename),
                               xls_filename=xls_filename)


@app.route('/dates', methods=['POST'])
def dates():
    if request.method == 'POST':
        # The request form is a ImmutableMultiDict
        form = request.form
        blob = Blob(
            discipline='dates',
            memo_time=form['memo_time'],
            recall_time=form['recall_time'],
            correction=form['correction'],
            data=form.get('data'),
            nr_items=form.get('nr_items'),
            language=form.get('language'),
            pattern=form['pattern']
        )
        h = blob.add_to_database()
        app.logger.info(f'Created blob for dates: {h}')

        # CREATE XLS DOCUMENT
        xls_filename = '{dis}_{lang}_{nr}st_{mem_t}min_{rec_t}min_{pat}_{cor}.xls'.format(
            dis=blob.discipline.title(),
            lang=form['language'],
            nr=len(blob.data),
            mem_t=blob.memo_time,
            rec_t=blob.recall_time,
            pat=','.join([p.strip() for p in form['pattern'].split(',')]),
            cor=blob.correction.title()
        )
        t = recall.xls.get_dates_table(
            title='Svenska Minnesförbundet',
            discipline=f'Historical Dates, {blob.language.title()}, {len(blob.data)} st.',
            recall_key=h.upper(),
            memo_time=form['memo_time'],
            recall_time=blob.recall_time,
            pattern=form['pattern']
        )
        for n in blob.data:
            t.add_item(n)
        t.save(os.path.join(app.root_path, 'static/sheets/' + xls_filename))
        return render_template('memorize.html',
                               xls_download_link=url_for('static', filename='sheets/' + xls_filename),
                               xls_filename=xls_filename)



@app.route('/recall/<string:key>')
def recall_(key):
    blob_file = os.path.join(app.root_path, f'database/{key[0:2]}/{key[2:6]}.json')
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

