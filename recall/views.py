
import os
import re
import flask
from flask import (render_template, request, jsonify, send_file, url_for,
                   flash, redirect)
from flask_login import login_user , logout_user , current_user , login_required
import random
import time
import math
from pprint import pprint
import json
import hashlib
from collections import namedtuple
import pickle
import functools
import collections
import io

import sqlalchemy.orm

from recall import app, db, login_manager
from recall import models

import recall.xls

import logging
handler = logging.FileHandler('flask.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
app.logger.addHandler(handler)


def sha(string):
    h = hashlib.sha1(string.encode())
    h.update(str(random.random()).encode())
    return h.hexdigest()[0:6]


DATABASE_WORDS = os.path.join(app.root_path, 'db_words.txt')
DATABASE_STORIES = os.path.join(app.root_path, 'db_stories.txt')
WordEntry = namedtuple('WordEntry', 'language value name date word_class')
StoryEntry = namedtuple('StoryEntry', 'language value name date')


def load_database(db_file, entry):
    """Load database entries"""
    with open(db_file, 'r', encoding='utf-8') as db_file:
        entries = set()
        for line in db_file:
            if line.strip():
                row_data = [x.strip() for x in line.split(';')]
                entries.add(entry(*row_data))
        return list(sorted(entries))


def save_database(db_file, entries):
    """Save database entries"""
    with open(db_file, 'w', encoding='utf-8') as db_file:
        lines = (';'.join(entry) for entry in sorted(entries))
        db_file.write('\n'.join(lines))


def unique_lines_in_textarea(data: str, lower=False):
    """Get unique nonempty lines in textarea"""
    if lower:
        data = data.lower()
    return {line.strip() for line in data.split('\n') if line.strip()}




@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
@login_required
def index():
    if request.method == 'GET':
        return render_template('index.html')


@login_manager.user_loader
def load_user(username):
    username = username.strip().lower()
    return models.User.query.filter_by(username=username).first()
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    user = models.User(
        # Todo: restrict username characters
        username=request.form['username'].strip().lower(),
        email=request.form['email'],
        real_name=request.form['real_name'],
        country=request.form['country']
    )
    db.session.add(user)
    db.session.commit()
    flash('User successfully registered', 'success')
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    username = request.form['username'].strip().lower()
    registered_user = models.User.query.filter_by(username=username).first()
    if registered_user is None:
        flash('Username or Password is invalid', 'danger')
        return redirect(url_for('login'))
    login_user(registered_user)
    flash('Logged in successfully', 'success')
    next = request.args.get('next')
    # is_safe_url should check if the url is safe for redirects.
    # See http://flask.pocoo.org/snippets/62/ for an example.
    if not True: #is_safe_url(next):
        return flask.abort(400)

    return flask.redirect(next or flask.url_for('index'))


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/delete/account')
@login_required
def delete_account():
    db.session.delete(current_user)
    db.session.commit()
    logout_user()
    return 'Account deleted.'

@app.route('/delete/memo/<int:id>')
@login_required
def delete_memo(id):
    memo = models.MemoData.query.get(id)
    if memo is None:
        return 'Can\'t delete memo, not found in database'
    if memo.user.id != current_user.id:
        return 'You can only delete your own memos'
    db.session.delete(memo)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/memo/<int:id>')
@login_required
def delete_recall(id):
    memo = models.MemoData.query.get(id)
    if memo is None:
        return 'Can\'t delete memo, not found in database'
    if memo.user.id != current_user.id:
        return 'You can only delete your own memos'
    db.session.delete(memo)
    db.session.commit()
    return redirect(url_for('index'))



def memo_from_request(request):
    form = request.form
    ip = request.remote_addr

    user_id = current_user.id
    key = sha(str(form))

    d = form['discipline'].strip().lower()
    if d == 'binary':
        discipline = models.Discipline.base2
    elif d == 'decimals':
        discipline = models.Discipline.base10
    elif d == 'words':
        discipline = models.Discipline.words
    elif d == 'dates':
        discipline = models.Discipline.dates
    else:
        raise ValueError(f'Invalid discipline form form: "{discipline}"')

    memo_time, recall_time = form['time'].strip().lower().split(',')
    memo_time, recall_time = int(memo_time), int(recall_time)

    language = form.get('language')

    data = form.get('data')
    nr_items = form.get('nr_items')
    assert data or nr_items, "data or nr_items must be provided!"

    if data is None:
        # If data was not provided, we must generate it ourselves.
        # In order to do so we need to know how many items to
        # generate, + language if words or dates.
        nr_items = int(nr_items)

        if d == 'binary':
            data = tuple(random.randint(0, 1) for _ in range(nr_items))
        elif d == 'decimals':
            data = tuple(random.randint(0, 9) for _ in range(nr_items))
        elif d == 'words':
            words = [word.value for word in
                     load_database(DATABASE_WORDS, WordEntry)
                     if word.language == language]
            random.shuffle(words)
            data = tuple(words[0:nr_items])
        elif d == 'dates':
            stories = [story.value for story in
                       load_database(DATABASE_STORIES, StoryEntry)
                       if story.language == language]
            random.shuffle(stories)
            stories = stories[0:nr_items]
            dates = [random.randint(1000, 2099) for _ in stories]
            data = tuple(zip(dates, stories))
            recall_data = list(data)
            random.shuffle(recall_data)
            _recall_data = tuple(recall_data)
        else:
            raise Exception('Data generation for discipline '
                            f'"{discipline}" not implemented.')
        generated = True
    else:
        # If data is provided, it's just a matter of parsing the data
        # from the string
        if d == 'binary':
            data = tuple(int(digit) for digit in re.findall('[01]', data))
        elif d == 'decimal':
            data = tuple(int(digit) for digit in re.findall('\d', data))
        elif d == 'words':
            data = tuple(unique_lines_in_textarea(data, lower=True))
        elif d == 'dates':
            lines = unique_lines_in_textarea(data, lower=False)
            historical_dates = []
            for line in lines:
                date, story = line.split(maxsplit=1)
                if not (1000 <= int(date) <= 2099):
                    raise ValueError(f'Date out of range: 1000 <= {date} <= 2099')
                historical_dates.append((date.strip(), story.strip()))
            data = tuple(historical_dates)
            recall_data = list(data)
            random.shuffle(recall_data)
            _recall_data = tuple(recall_data)
        else:
            raise Exception('Data creation for discipline '
                            f'"{discipline}" not implemented.')
        generated = False

    return models.MemoData(
        ip=ip,
        user_id=user_id,
        key=key,
        discipline=discipline,
        memo_time=memo_time,
        recall_time=recall_time,
        language=language,
        data=data,
        generated=generated
    )


def asdf(self):
    yield from (
        ('discipline', self.discipline),
        ('memo_time', self.memo_time),
        ('recall_time', self.recall_time),
        ('correction', self.correction),
        ('data', self.data),
        ('language', self.language),
        ('pattern', self.pattern),
        ('recall_key', self.recall_key),
        ('date_created', time.time()),
        ('_recall_data', self._recall_data)
    )


def alert(message):
    return f'<div class="alert alert-danger">{message}</div>'


@app.route('/database/words', methods=['GET', 'POST'])
def manage_words_database():
    """Words database dashboard"""
    if request.method == 'GET':
        return render_template('db_words.html')


@app.route('/database/words/content', methods=['GET'])
def database_words_content():
    """View whole word database in one big table"""
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
        data = unique_lines_in_textarea(form['data'], lower=True)
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

@app.route('/users')
@login_required
def users():
    users = models.User.query.all()
    return render_template('users.html', users=users)

@app.route('/user/<string:username>', methods=['GET', 'POST'])
@login_required
def user(username):
    username = username.strip().lower()
    memo_page = request.args.get('memo_page', 1)
    recall_page = request.args.get('recall_page', 1)
    try:
        user = models.User.query.filter_by(username=username).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return f'No such user "{username}"'

    if user.id != current_user.id:
        return render_template('user.html', user=user, logged_in=False)

    if request.method == 'POST':
        settings = dict(current_user.settings)  # Must have new id
        # Verify patterns
        for key in request.form:
            if key.startswith('pattern_'):
                pattern = request.form[key]
                try:
                    settings[key] = recall.xls.verify_and_clean_pattern(pattern)
                except ValueError as err:
                    flash(str(err) + ' Settings not saved.', 'danger')
                    break
        else:
            current_user.settings = settings
            db.session.commit()
            flash('Settings successfully updated', 'success')

    return render_template('user.html', user=current_user, logged_in=True,
                           memos=current_user.memos.paginate(int(memo_page), 10, False),
                           recalls=current_user.recalls.paginate(int(recall_page), 10, False))


@app.route('/generate')
@login_required
def generate():
    return render_template('make_generate.html')


@app.route('/create')
@login_required
def create():
    return render_template('make_create.html')


def blob_to_xls_filename(blob):
    """Create xls filename containing blob data"""
    XLS_FILENAME_FMT = '{discipline}_{nr}st_{language}_{memo_time}-{recall_time}min_p{pattern_str}_{correction}_{recall_key}'
    b = dict(blob)  # So we can unpack below
    xls_filename = XLS_FILENAME_FMT.format(
        nr=len(blob.data),
        pattern_str=','.join(str(p) for p in blob.pattern),
        **b
    ) + '.xls'
    return xls_filename


def memo_to_table(memo, pattern):
    """Take relevant data of blob and create table

    The table can later be saved to disk as .xls file.
    """

    # Depending on which discipline we have, we'll need discipline
    # specific table and description
    if memo.discipline == models.Discipline.base2:
        table = recall.xls.get_binary_table
    elif memo.discipline == models.Discipline.base10:
        table = recall.xls.get_decimal_table
    elif memo.discipline == models.Discipline.words:
        table = recall.xls.get_words_table
    elif memo.discipline == models.Discipline.dates:
        table = recall.xls.get_dates_table
    else:
        raise ValueError(
            f'Invalid discipline: "{memo.discipline}"'
        )

    nr_items = len(memo.data)
    if memo.language:
        description = f'{memo.discipline.value}, {memo.language.title()}, {nr_items} st.'
    else:
        description = f'{memo.discipline.value}, {nr_items} st.'

    # Create header
    header = recall.xls.Header(
        title='Svenska Minnesförbundet',
        description=description,
        recall_key=memo.key,
        memo_time=memo.memo_time,
        recall_time=memo.recall_time
    )
    # Create table
    t = table(header=header, pattern=pattern)
    # Update the table with data
    for n in memo.data:
        t.add_item(n)
    return t


@app.route('/make', methods=['POST'])
def make_discipline():
    """Convert request form to blob, create xls file, return links"""
    if request.method == 'POST':
        # ADD MEMO DATA TO MEMO_DATA TABLE
        try:
            memo = memo_from_request(request)
            db.session.add(memo)
        except Exception as e:
            return alert(f'Failed to create MemoData from form fields: {e}')

        # ADD ENTRY TO KEY_STATUS TABLE
        try:
            key_status = models.KeyStatus(key=memo.key, public=True)
            db.session.add(key_status)
        except Exception as e:
            return alert(f'Failed to create KeyStatus: {e}')

        db.session.commit()

        return render_template(
            'make_links_memo_and_recall.html',
            key=memo.key,
        )

@app.route('/download/xls/<string:key>', methods=['GET'])
def download_xls(key):
    key = key.lower()
    pattern = request.args.get('pattern')
    if pattern:
        pattern = recall.xls.verify_and_clean_pattern(pattern)
    # pattern will now be either None or a nice string
    try:
        xls_doc = models.XlsDoc.query.filter_by(key=key, pattern=pattern).one()
    except sqlalchemy.orm.exc.NoResultFound:

        try:
            memo = models.MemoData.query.filter_by(key=key).one()
        except sqlalchemy.orm.exc.NoResultFound:
            return f'Could not find memo for key={key}'

        # CREATE XLS DOCUMENT
        try:
            table = memo_to_table(memo, pattern=pattern)
        except Exception as e:
            return alert(f'Failed to create table object of blob: {e}')

        # ADD XLS DOCUMENT TO XLS_DOC TABLE
        try:
            filedata = io.BytesIO()
            table.save(filedata)
            filedata.seek(0)
            xls_doc = models.XlsDoc(memo.key, pattern, filedata)
            db.session.add(xls_doc)
            db.session.commit()
        except Exception as e:
            return alert(f'Failed to save xls file data to XlsDoc: {e}')

    # Todo: download only if public
    return send_file(xls_doc.data,
                     attachment_filename=f'{key}.xls',
                     as_attachment=True,
                     mimetype='application/vnd.ms-excel'
                     )


@app.route('/recall/<string:key>')
@login_required
def recall_(key):
    memo = models.MemoData.query.filter_by(key=key).one()
    if memo is None:
        return f'Key "{key}" does not exists or is private'
    nr_items = len(memo.data)

    if memo.discipline == models.Discipline.base2:
        nr_rows = math.ceil(nr_items/30)
        return render_template('recall_numbers.html', memo=memo,
                               nr_cols=30, nr_rows=nr_rows)
    elif memo.discipline == models.Discipline.base10:
        nr_rows = math.ceil(nr_items/40)
        return render_template('recall_numbers.html', memo=memo,
                               nr_cols=40, nr_rows=nr_rows)
    elif memo.discipline == models.Discipline.words:
        nr_cols = math.ceil(nr_items/20)
        if nr_cols%5 == 0:
            nr_cols_iter = [5]*(nr_cols//5)
        else:
            nr_cols_iter = [5]*(nr_cols//5) + [nr_cols%5]
        return render_template('recall_words.html', memo=memo,
                               nr_cols_iter=nr_cols_iter)
    elif memo.discipline == models.Discipline.dates:
        return render_template('recall_dates.html', memo=memo)
    else:
        return 'Recall not implemented yet: ' + memo.discipline


def _arbeiter(key, dictionary):
    pass


def recall_from_request(request):

    form = request.form
    ip = request.remote_addr
    user_id = current_user.id
    username = form['username'].strip().lower()
    key = form['key'].strip().lower()
    memo = models.MemoData.query.filter_by(key=key).one()
    time_remaining = float(form['seconds_remaining'])

    data = list()
    for i in range(len(form)):
        try:
            data.append(form[f'recall_cell_{i}'])
        except KeyError:
            break

    return models.RecallData(
        ip=ip,
        user_id=user_id,
        key=memo.key,
        data=data,
        time_remaining=time_remaining
    )


def start_of_emptiness_before(data, index):
    index_of_empty_cell = index
    for i in reversed(range(index)):
        if data[i].strip():
            break
        else:
            index_of_empty_cell = i
    return index_of_empty_cell


class Arbeiter:
    """Correct user's recall data

    The Arbeiter is used to correct the user's recall.
    The user's recall is compared to the blob answer.
    """
    def __init__(self):
        pass

    def correct(self, recall):
        """Correct client_data (user's recall data)"""
        self.recall = recall
        self.memo = models.MemoData.query.filter_by(key=recall.key).one()

        cell_by_cell_result = self._correct_cells()
        count = dict(collections.Counter(cell_by_cell_result))
        raw_score = self._raw_score(cell_by_cell_result)
        points = self._points(raw_score)

        return {
            'cell_by_cell_result': tuple(cell_by_cell_result),
            'count': count,
            'raw_score': raw_score,
            'points': points
        }

    def _correct_cells(self):
        d = self.memo.discipline
        if d == models.Discipline.base2:
            correcter = self._correct_binary
        elif d == models.Discipline.base10:
            correcter = self._correct_decimals
        elif d == models.Discipline.words:
            correcter = self._correct_words
        elif d == models.Discipline.dates:
            correcter = self._correct_dates
        else:
            raise Exception(f'Blob contain invalid discipline: {d}')

        start_of_emptiness = start_of_emptiness_before(
            self.recall.data,
            len(self.memo.data))
        result = [None]*len(self.recall.data)
        # Todo: won't work for historical dates
        for i, user_value in enumerate(self.recall.data, start=0):
            try:
                correct_value = self.memo.data[i]
            except IndexError:
                result[i] = 'off_limits'
            else:
                if not user_value.strip():
                    # Empty cell
                    if i < start_of_emptiness:
                        result[i] = 'gap'
                    else:
                        result[i] = 'not_reached'
                else:
                    result[i] = correcter(user_value, correct_value)
        return result

    @staticmethod
    def _correct_binary(user_value: str, correct_value: int):
        if user_value == str(correct_value):
            return 'correct'
        else:
            return 'wrong'

    @staticmethod
    def _correct_decimals(user_value: str, correct_value: int):
        if user_value == str(correct_value):
            return 'correct'
        else:
            return 'wrong'

    def _correct_words(self, user_value: str, correct_value: str):
        if user_value.strip().lower() == correct_value.strip().lower():
            return 'correct'
        elif self._word_almost_correct(user_value, correct_value):
            return 'almost_correct'
        else:
            return 'wrong'

    @staticmethod
    def _correct_dates(user_value: str, correct_value: int):
        if user_value == str(correct_value):
            return 'correct'
        else:
            return 'wrong'

    @staticmethod
    def _word_almost_correct(user_value, correct_value):
        return False

    def _raw_score(self, cell_by_cell_result):
        # Will depend on correction method
        return 123

    def _points(self, raw_score):
        return 3.14


@app.route('/arbeiter', methods=['POST'])
def arbeiter():
    app.logger.info(f'Arbeiter got data from {request.remote_addr}')
    if request.method == 'POST':
        try:
            app.logger.info(str(request.form))
            recall = recall_from_request(request)
            db.session.add(recall)
            db.session.commit()

            recall_correction = Arbeiter().correct(recall)
            app.logger.info(f'Arbeiter has corrected {request.remote_addr}')
        except Exception as e:
            app.logger.error(str(e))
            return jsonify({'error': str(e)})

        return jsonify(recall_correction)
    else:
        print('Wrong method!')


@app.route('/results/view', methods=['GET'])
def view_recall():
    file = request.args.get('data')
    filename = os.path.join(
        app.root_path, f'recalldata/{file}')
    with open(filename, 'rb') as file:
        client, result = pickle.load(file)
        blob = load_blob(client.recall_key)
    d = blob['discipline']
    if d == 'binary':
        nr_rows = math.ceil(len(blob['data'])/30)
        return render_template('view_recall_numbers.html', blob=blob,
                               client_data=client, result=result,
                                   nr_cols=30, nr_rows=nr_rows)
    elif d == 'decimal':
        nr_rows = math.ceil(len(blob['data'])/40)
        return render_template('view_recall_numbers.html', blob=blob,
                               client_data=client, result=result,
                                   nr_cols=40, nr_rows=nr_rows)
    elif d == 'words':
        nr_cols = math.ceil(len(blob['data'])/20)
        if nr_cols%5 == 0:
            nr_cols_iter = [5]*(nr_cols//5)
        else:
            nr_cols_iter = [5]*(nr_cols//5) + [nr_cols%5]
        return render_template('view_recall_words.html', blob=blob,
                               client_data=client, result=result,
                               nr_cols_iter=nr_cols_iter)
    elif d == 'dates':
        return render_template('view_recall_dates.html', blob=blob,
                               client_data=client, result=result)
    else:
        raise Exception(f'Blob contain invalid discipline: {d}')

@app.route('/results')
def list_results():
    root = os.path.join(app.root_path, f'recalldata')
    files = os.listdir(root)
    pickle_files = list()
    for file in files:
        if file.lower().endswith('.pickle'):
            timestamp, username = file.split('_', 1)
            local_time = time.localtime(float(timestamp))
            time_str = time.strftime('%Y-%m-%d %H:%M:%S', local_time)
            username = os.path.splitext(username)[0]
            pickle_files.append((file, time_str, username))
    pickle_files.sort(reverse=True)
    return render_template('results.html', results=pickle_files)