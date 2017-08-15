
import os
from flask import (render_template, request, jsonify, send_file, url_for,
                   flash, redirect)
from flask_login import login_user , logout_user , current_user , login_required
import random
import time
import math
import hashlib
import pickle
import collections

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


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
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
    # POST: create user -> insert in db -> redirect to login
    user = models.User.from_request(request)
    db.session.add(user)
    db.session.commit()
    flash('User successfully registered', 'success')
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    username = request.form['username'].strip().lower()
    user = models.User.query.filter_by(username=username).first()
    if user is None:
        flash('Username or Password is invalid', 'danger')
        return redirect(url_for('login'))
    login_user(user)
    flash('Logged in successfully', 'success')
    # Todo: investigate below
    # is_safe_url should check if the url is safe for redirects.
    # See http://flask.pocoo.org/snippets/62/ for an example.
    return redirect(url_for('user', username=user.username))


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/delete/account')
@login_required
def delete_account():
    # Todo: figure out the correct order of doing things
    db.session.delete(current_user)
    db.session.commit()
    logout_user()
    return 'Account deleted.'


@app.route('/delete/memo/<int:memo_id>')
@login_required
def delete_memo(memo_id):
    memo = models.MemoData.query.get(memo_id)
    if memo is None:
        flash('Can\'t delete memo, not found in database', 'danger')
    elif memo.user.id != current_user.id:
        flash('You can only delete your own memos', 'danger')
    else:
        flash(f'Deleted memo {memo_id}', 'success')
        db.session.delete(memo)
        db.session.commit()
    return redirect(url_for('user', username=current_user.username))


@app.route('/delete/recall/<int:recall_id>')
@login_required
def delete_recall(recall_id):
    # Todo: implement
    recall = models.RecallData.query.get(recall_id)
    if recall is None:
        flash('Can\'t delete recall, not found in database', 'danger')
    elif recall.memo.user.id != current_user.id:
        flash('You can only delete recalls for which you own the memorization',
              'danger')
    else:
        flash(f'Deleted recall {recall_id}', 'success')
        db.session.delete(recall)
        db.session.commit()
    return redirect(url_for('user', username=current_user.username))


@app.route('/togglekey/<string:memo_id>')
@login_required
def toggle_key_state(memo_id):
    # Todo: Improve this
    key_state = models.MemoData.query.filter_by(id=memo_id).one()
    if key_state.state == models.State.private:
        key_state.state = models.State.competition
    elif key_state.state == models.State.competition:
        key_state.state = models.State.public
    elif key_state.state == models.State.public:
        key_state.state = models.State.private
    db.session.commit()
    return redirect(url_for('user', username=current_user.username))


@app.route('/users')
@login_required
def users():
    users = models.User.query.all()
    return render_template('users.html', users=users)


@app.route('/user/<string:username>', methods=['GET', 'POST'])
@login_required
def user(username):
    username = username.strip().lower()
    try:
        user = models.User.query.filter_by(username=username).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return f'No such user "{username}"'

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

    # Todo, remove pagination
    r = models.RecallData.query.join(models.RecallData.memo).filter(
        models.MemoData.user_id==user.id)
    return render_template('user.html', user=user,
                           users_home_page=(user.id == current_user.id),
                           recalls=r)


@app.route('/generate')
@login_required
def generate():
    return render_template('make_generate.html')


@app.route('/create')
@login_required
def create():
    return render_template('make_create.html')


@app.route('/make', methods=['POST'])
@login_required
def make_discipline():
    """Convert request form to memo"""
    if request.method == 'POST':
        memo = models.MemoData.from_request(request, current_user)
        db.session.add(memo)
        db.session.commit()
        return render_template(
            'make_links_memo_and_recall.html',
            memo_id=memo.id
        )

@app.route('/download/xls/<int:memo_id>', methods=['GET'])
@login_required
def download_xls(memo_id: int):
    pattern = request.args.get('pattern')
    if pattern:
        pattern = recall.xls.verify_and_clean_pattern(pattern)
    # pattern will now be either None or a nice string
    try:
        memo = models.MemoData.query.filter_by(id=memo_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return f'Could not find memo for key={memo_id}'

    # If the current user doesn't own the memorization,
    # he/she is only allowed to download xls if it is
    # public.
    if memo.user.id != current_user.id:
        if memo.state != models.State.public:
            return 'Download not allowed.'

    try:
        xls_doc = models.XlsDoc.query.filter_by(memo_id=memo.id, pattern=pattern).one()
    except sqlalchemy.orm.exc.NoResultFound:
        # Failed to find already-created xls, create it:
        try:
            xls_doc = models.XlsDoc.from_memo(memo, pattern)
        except Exception as e:
            return f'Failed to create xls document: {e}'
        else:
            db.session.add(xls_doc)
            db.session.commit()

    # Todo: download only if public
    return send_file(xls_doc.data,
                     attachment_filename=f'{memo_id}.xls',
                     as_attachment=True,
                     mimetype='application/vnd.ms-excel'
                     )


@app.route('/recall/<string:memo_id>')
@login_required
def recall_(memo_id):
    memo = models.MemoData.query.filter_by(id=memo_id).one()
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
        self.memo = recall.memo

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
            recall = models.RecallData.from_request(request, current_user)
            # Todo: Backup solution if commit fails
            db.session.add(recall)
            db.session.commit()

            recall_correction = Arbeiter().correct(recall)
            app.logger.info(f'Arbeiter has corrected {request.remote_addr}')
        except Exception as e:
            app.logger.error(str(e))
            return jsonify({'error': str(e)})

        return jsonify(recall_correction)


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
