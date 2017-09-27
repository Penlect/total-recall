
import os
import re
from flask import (render_template, request, jsonify, url_for,
                   flash, redirect, send_from_directory)
from flask_login import login_user, logout_user, current_user, login_required
import math
import collections
import json
import functools

import sqlalchemy.orm
from passlib.hash import sha256_crypt
import requests

from recall import app, db, login_manager
from recall import models
import recall.xls

import logging
handler = logging.FileHandler('flask.log')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
app.logger.addHandler(handler)


NR_DIGITS_IN_ROW_BINARY = 30
NR_DIGITS_IN_ROW_DECIMALS = 40
NR_DIGITS_IN_COLUMN = 25
NR_WORDS_IN_ROW = 5
NR_WORDS_IN_COLUMN = 20
NR_DATES_IN_COLUMN = 40


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

    try:
        user = models.User(
            username=request.form['username'],
            password=request.form['password'],
            email=request.form['email'],
            real_name=request.form['real_name'],
            country=request.form['country']
        )
    except models.RegisterUserError as error:
        flash(str(error) + ' Try again.', 'danger')
        return redirect(url_for('register'))

    # Verify that user is not a robot
    # https://www.google.com/recaptcha/intro/
    resp = requests.post(
        url='https://www.google.com/recaptcha/api/siteverify',
        data={
            'secret': '6LfWbjAUAAAAAB57PUEvWxN3QqTJkYqjugrOUgNn',
            'response': request.form['g-recaptcha-response']
        }
    ).json()
    if resp['success'] is not True:
        app.logger.error(resp)
        err_code = resp['error-codes'][0]
        if err_code == 'missing-input-secret':
            app.logger.error('The secret parameter is missing.')
            flash('reCAPTCHA: Server failed with secret parameter.', 'danger')
        elif err_code == 'invalid-input-secret':
            app.logger.error('The secret parameter is invalid or malformed.')
            flash('reCAPTCHA: Server failed with secret parameter.', 'danger')
        elif err_code == 'missing-input-response':
            app.logger.error('The response parameter is missing.')
            flash('reCAPTCHA: Missing parameter.', 'danger')
        elif err_code == 'invalid-input-response':
            app.logger.error('The response parameter is invalid or malformed.')
            flash('reCAPTCHA: Invalid parameter.', 'danger')
        elif err_code == 'bad-request':
            app.logger.error('The request is invalid or malformed.')
            flash('reCAPTCHA: Bad request.', 'danger')
        return redirect(url_for('register'))

    db.session.add(user)
    db.session.commit()
    flash('User successfully registered', 'success')
    app.logger.info(f'New user registered: {user}')
    return redirect(url_for('login'))


class WrongPasswordError(Exception):
    pass


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    username = request.form['username'].strip().lower()
    try:
        user = models.User.query.filter_by(username=username).one()
        if not sha256_crypt.verify(request.form['password'], user.password):
            raise WrongPasswordError
    except (sqlalchemy.orm.exc.NoResultFound, WrongPasswordError):
        flash('Username or Password is invalid', 'danger')
        return redirect(url_for('login'))
    if user.blocked is True:
        flash('This user is blocked', 'danger')
        return redirect(url_for('login'))
    login_user(user)
    flash(f'Logged in user "{username}" successfully', 'success')
    app.logger.info(f'User logged in: {username}')
    # Todo: investigate below
    # is_safe_url should check if the url is safe for redirects.
    # See http://flask.pocoo.org/snippets/62/ for an example.
    return redirect(url_for('user', username=user.username))


@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    flash(f'Logged out user "{username}" successfully', 'success')
    app.logger.info(f'User logged out: {username}')
    return redirect(url_for('login'))


@app.route('/delete/account')
@login_required
def delete_account():
    # Todo: figure out the correct order of doing things
    username = current_user.username
    db.session.delete(current_user)
    db.session.commit()
    logout_user()
    flash(f'Account "{username}" deleted.', 'danger')
    app.logger.info(f'User deleted account: {username}')
    return redirect(url_for('index'))


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
    return redirect(url_for('user_delete_column', username=current_user.username))


@app.route('/delete/all_memos')
@login_required
def delete_all_memos():
    for memo in current_user.memos:
        db.session.delete(memo)
    flash(f'Deleted all memos', 'success')
    db.session.commit()
    return redirect(url_for('user', username=current_user.username))


@app.route('/delete/recall/<int:recall_id>')
@login_required
def delete_recall(recall_id):
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
    return redirect(url_for('user_delete_column', username=current_user.username))


@app.route('/delete/all_recalls')
@login_required
def delete_all_recalls():
    for memo in current_user.memos:
        for recall in memo.recalls:
            if recall.user_id == current_user.id:
                db.session.delete(recall)
    flash(f'Deleted recalls', 'success')
    db.session.commit()
    return redirect(url_for('user', username=current_user.username))


@app.route('/delete/story', methods=['GET'])
@login_required
def delete_story():
    story_id = int(request.args.get('story_id'))
    story = models.Story.query.get(story_id)
    # Todo: only admin users should be able to delete?
    if story is None:
        flash('Can\'t delete story, not found in database', 'danger')
    else:
        flash(f'Deleted story "{story.story}".', 'danger')
        db.session.delete(story)
        db.session.commit()
    return 'Done'


@app.route('/delete/word', methods=['GET'])
@login_required
def delete_word():
    story_id = int(request.args.get('word_id'))
    word = models.Word.query.get(story_id)
    # Todo: only admin users should be able to delete?
    if word is None:
        flash('Can\'t delete word, not found in database', 'danger')
    else:
        flash(f'Deleted word "{word.word}".', 'danger')
        db.session.delete(word)
        db.session.commit()
    return 'Done'


@app.route('/delete/almostcorrectword', methods=['GET'])
@login_required
def delete_almost_correct_word():
    story_id = int(request.args.get('mapping_id'))
    mapping = models.AlmostCorrectWord.query.get(story_id)
    if mapping is None:
        flash('Can\'t delete almost-correct-word, not found in database', 'danger')
    else:
        flash(f'Deleted almost-correct-word "{mapping.almost_correct}".', 'danger')
        db.session.delete(mapping)
        db.session.commit()
    return 'Done'


@app.route('/changestate/<string:memo_id>/<string:state>')
@login_required
def change_state(memo_id, state):
    memo = models.MemoData.query.filter_by(id=memo_id).one()
    if memo.user.id != current_user.id:
        return 'Not authorized.'
    state = state.strip().lower()
    for s in models.State:
        if s.name == state:
            memo.state = s
            db.session.commit()
            return redirect(url_for('user', username=current_user.username))
    else:
        return f'Unknown state {state}'


@app.route('/users')
@login_required
def users():
    users = models.User.query.all()
    return render_template('users.html', users=users)


def _user(username, delete_column=False):
    username = username.strip().lower()
    try:
        user = models.User.query.filter_by(username=username).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return f'No such user "{username}"'

    if request.method == 'POST':
        settings = dict(current_user.settings)  # Must have new id
        # Verify patterns
        settings['card_colors'] = request.form.get('card_colors') == 'on'
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
        return redirect(url_for('user', username=current_user.username))

    r = models.RecallData.query.join(models.RecallData.memo).filter(
        models.MemoData.user_id==user.id)
    return render_template('user.html', user=user,
                           users_home_page=(user.id == current_user.id),
                           recalls=r, delete_column=delete_column)


@app.route('/user/<string:username>', methods=['GET', 'POST'])
@login_required
def user(username):
    return _user(username, delete_column=False)


@app.route('/user/<string:username>/delete', methods=['GET', 'POST'])
@login_required
def user_delete_column(username):
    return _user(username, delete_column=True)


@app.route('/make', methods=['GET', 'POST'])
@login_required
def make_discipline():
    """Convert request form to memo"""
    if request.method == 'GET':
        return render_template('make.html')
    elif request.method == 'POST':
        try:
            memo = models.MemoData.from_request(request, current_user)
        except (models.InvalidHistoricalDate, ValueError) as error:
            return 'Failed to create discipline: ' + str(error)

        if len(memo.data) == 0:
            if memo.language is None:
                return 'Failed to create discipline!'
            else:
                return ('Failed to create discipline. '
                        'Maybe the database has no data for language = '
                        f'"{memo.language.language}" ?')
        db.session.add(memo)
        db.session.commit()
        app.logger.info(
            f'User {current_user.username} created memorization {memo}')
        return 'Successfully created discipline'


@app.route('/xls/<int:memo_id>', methods=['GET'])
@login_required
def download_xls(memo_id: int):
    pattern = request.args.get('pattern')
    if pattern:
        pattern = recall.xls.verify_and_clean_pattern(pattern)
    # pattern will now be either None or a nice string
    try:
        memo = models.MemoData.query.filter_by(id=memo_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return f'Could not find memo {memo_id}'

    if memo.discipline == models.Discipline.spoken:
        return 'Not possible for discipline Spoken Numbers'
    elif memo.discipline == models.Discipline.cards:
        card_colors = request.args.get('card_colors')
        card_colors = (card_colors == 'True')
        memo.get_xls_filedata = functools.partial(memo.get_xls_filedata,
                                                  card_colors=card_colors)
    else:
        card_colors = False

    # If the current user doesn't own the memorization,
    # he/she is only allowed to download xls if it is
    # public.
    if memo.user.id != current_user.id:
        if memo.state != models.State.public:
            return 'Download not allowed.'

    filename = memo.get_xls_filename(pattern, card_colors)
    fullfile = os.path.join(app.root_path, f'xls/{filename}')
    if not os.path.isfile(fullfile):
        filedata = memo.get_xls_filedata(pattern)
        with open(fullfile, 'wb') as h:
            h.write(filedata.getvalue())
    app.logger.info(f'{current_user.username} downloads {filename}')
    return send_from_directory(os.path.join(app.root_path, 'xls'),
                               filename,
                               as_attachment=True)


@app.route('/play/<int:memo_id>', methods=['GET'])
@login_required
def play_spoken(memo_id: int):
    try:
        memo = models.MemoData.query.filter_by(id=memo_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return f'Could not find memo for key={memo_id}'
    if memo.user.id != current_user.id:
        if memo.state != models.State.public:
            return 'Play not allowed.'
    app.logger.info(f'{current_user.username} plays {memo}')
    return render_template('play_spoken.html', data=json.dumps(memo.data))


@app.route('/recall/<int:memo_id>')
@login_required
def recall_(memo_id):
    """Send the user to the recall page of memorization provided id

    The following rules apply:
    * Any user can always do recall on the memorizations he/she
      created. Any number of times.
    * A user can do recall of another users memorization only
      if that memorization is in Competition state. And he/she
      can only do it once
    """
    try:
        memo = models.MemoData.query.filter_by(id=memo_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return f'Does not exists'
    if memo.user.id != current_user.id:
        if memo.state != models.State.competition:
            return 'This memorization is not in Competition-state'
        elif memo.recalls.filter_by(user_id=current_user.id).first():
            return 'This user has already done recall for this memorization'

    # If we reach here, the user is allowed to do recall
    app.logger.info(
        f'User {current_user.username} request recall page of memo {memo.id}')

    nr_items = len(memo.data)
    seconds_remaining = memo.recall_time*60
    if memo.discipline == models.Discipline.base2:
        nr_rows = math.ceil(nr_items/NR_DIGITS_IN_ROW_BINARY)
        return render_template('recall_numbers.html', memo=memo,
                               nr_cols=NR_DIGITS_IN_ROW_BINARY,
                               nr_rows=nr_rows,
                               nr_digits_in_column=NR_DIGITS_IN_COLUMN,
                               seconds_remaining=seconds_remaining)
    elif memo.discipline == models.Discipline.base10\
            or memo.discipline == models.Discipline.spoken:
        nr_rows = math.ceil(nr_items/NR_DIGITS_IN_ROW_DECIMALS)
        return render_template('recall_numbers.html', memo=memo,
                               nr_cols=NR_DIGITS_IN_ROW_DECIMALS,
                               nr_rows=nr_rows,
                               nr_digits_in_column=NR_DIGITS_IN_COLUMN,
                               seconds_remaining=seconds_remaining)
    elif memo.discipline == models.Discipline.words:
        # Compute the total nr of columns (acc over all pages)
        nr_cols = int(math.ceil(nr_items/NR_WORDS_IN_COLUMN))
        nr_full_tables = nr_cols//NR_WORDS_IN_ROW
        remainder_cols = nr_cols%NR_WORDS_IN_ROW
        if remainder_cols == 0:
            nr_cols_iter = [NR_WORDS_IN_ROW]*nr_full_tables
        else:
            nr_cols_iter = [NR_WORDS_IN_ROW]*nr_full_tables + [remainder_cols]
        return render_template('recall_words.html', memo=memo,
                               nr_cols_iter=nr_cols_iter,
                               nr_words_in_column=NR_WORDS_IN_COLUMN,
                               seconds_remaining=seconds_remaining)
    elif memo.discipline == models.Discipline.dates:
        return render_template('recall_dates.html', memo=memo,
                               data=sorted(memo.data, key=lambda x: x[2]),
                               nr_dates_in_column=NR_DATES_IN_COLUMN,
                               seconds_remaining=seconds_remaining)
    elif memo.discipline == models.Discipline.cards:
        return render_template('recall_cards.html', memo=memo,
                               nr_decks=math.ceil(nr_items/52),
                               seconds_remaining=seconds_remaining)
    else:
        return 'Recall not implemented yet: ' + memo.discipline.name


@app.route('/arbeiter', methods=['POST'])
def arbeiter():
    # Todo: Backup solution if commit fails
    """Accept posted recall data, correct, and store in database"""

    # Make sure a user is logged in
    if not current_user.is_authenticated:
        app.logger.warning('Arbeiter: User is not authenticated.')
        return jsonify({'error': 'User is not authenticated'})

    arbeiter = f'{current_user.username}\'s Arbeiter:'
    app.logger.info(f'{arbeiter}: Got recall data from competitor')

    # There must exist a corresponding memorization for this
    # Recall in the database
    memo_id = int(request.form['memo_id'])
    memo = models.MemoData.query.filter_by(id=memo_id).one()

    # Check if there already exists a recall entry for this
    # memorization and user in the database.
    user_id = int(request.form['user_id'])
    recall = memo.recalls.filter_by(user_id=user_id).first()

    if recall:
        app.logger.debug(f'{arbeiter}: Found existing recall for competitor: '
                         f'recall {recall.id}')
        if recall.locked is True and user_id != memo.user_id:
            # If the recall is locked, no further submits will
            # be accepted - unless the user is the owner of the
            # memorization, then he can recall as many times he
            # wants.
            app.logger.warning(f'{arbeiter}: Recall {recall.id} is locked')
            return jsonify({'error': 'Recall is locked'})

        if recall.user_id == current_user.id:
            # Update the recall instance with new field values
            recall.__init__(request)
        else:
            # In this case the Arbeiter got recall data of a
            # user who is no longer logged in - that is not
            # allowed.
            app.logger.warning(f'{arbeiter}: Wrong user logged in')
            return jsonify({'error': 'User not logged in'})
    else:
        app.logger.debug(f'{arbeiter}: First time recall of memo {memo.id}')
        # Create a new recall object and add to database
        recall = models.RecallData(request)
        recall.user = current_user
        recall.memo = memo
        db.session.add(recall)

    # In the final submit the client should send a signal to
    # lock the recall, so no further recalls will be accepted.
    # (unless the client is the owner of the memorization)
    if request.form['locked'] == 'true':
        app.logger.info(f'{arbeiter}: Recall {recall.id} is now locked')
        recall.locked = True

    db.session.commit()

    raw_score, points, cbc_r = recall.correct()

    if recall.correction:
        app.logger.debug(f'{arbeiter}: Re-correcting recall {recall.id}')
        recall.correction.__init__(raw_score, points, cbc_r)
    else:
        app.logger.debug(
            f'{arbeiter}: Correcting recall {recall.id} for the first time')
        correction = models.Correction(raw_score, points, cbc_r)
        correction.recall = recall
        db.session.add(correction)

    app.logger.info(recall.correction)

    db.session.commit()

    app.logger.info(f'Arbeiter has corrected {recall.user.username}\'s '
                    f'recall of memo {recall.memo.id}')
    if recall.locked is True:
        return jsonify(dict(recall.correction))
    else:
        return jsonify({'success': 'Recall received'})


@app.route('/arbeiter/correct/<int:recall_id>')
@login_required
def recorrect(recall_id):
    app.logger.info(f'Arbeiter will re-correct recall {recall_id}')
    try:
        recall = models.RecallData.query.filter_by(id=recall_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return f'Does not exists'
    if recall.memo.user.id != current_user.id:
        return 'Not allowed. This user do not own the memorization'
    raw_score, points, cbc_r = recall.correct()
    old = recall.correction
    recall.correction = models.Correction(raw_score, points, cbc_r)
    db.session.delete(old)
    db.session.commit()
    return redirect(url_for('view_recall', recall_id=recall_id))


@app.route('/recall/view/<int:recall_id>')
@login_required
def view_recall(recall_id):
    """View recall"""
    try:
        recall = models.RecallData.query.filter_by(id=recall_id).one()
    except sqlalchemy.orm.exc.NoResultFound:
        return f'Does not exists'

    if recall.memo.user_id != current_user.id:
        if recall.user_id != current_user.id:
            if recall.memo.state.value != 'Public':
                return 'Not allowed to view recall!'

    # If we reach here, the user is allowed to view recall
    app.logger.info(
        f'User {current_user.username} view recall {recall_id}')

    nr_items = len(recall.memo.data)
    seconds_remaining = recall.time_remaining
    if recall.memo.discipline == models.Discipline.base2:
        nr_rows = math.ceil(nr_items/NR_DIGITS_IN_ROW_BINARY)
        return render_template('recall_numbers.html', memo=recall.memo,
                               nr_cols=NR_DIGITS_IN_ROW_BINARY,
                               nr_rows=nr_rows,
                               nr_digits_in_column=NR_DIGITS_IN_COLUMN,
                               seconds_remaining=seconds_remaining,
                               view=True,
                               recall=recall,
                               result=json.dumps(dict(recall.correction)))
    elif recall.memo.discipline == models.Discipline.base10\
            or recall.memo.discipline == models.Discipline.spoken:
        nr_rows = math.ceil(nr_items/NR_DIGITS_IN_ROW_DECIMALS)
        return render_template('recall_numbers.html', memo=recall.memo,
                               nr_cols=NR_DIGITS_IN_ROW_DECIMALS,
                               nr_rows=nr_rows,
                               nr_digits_in_column=NR_DIGITS_IN_COLUMN,
                               seconds_remaining=seconds_remaining,
                               view=True,
                               recall=recall,
                               result=json.dumps(dict(recall.correction)))
    elif recall.memo.discipline == models.Discipline.words:
        # Compute the total nr of columns (acc over all pages)
        nr_cols = int(math.ceil(nr_items/NR_WORDS_IN_COLUMN))
        nr_full_tables = nr_cols//NR_WORDS_IN_ROW
        remainder_cols = nr_cols%NR_WORDS_IN_ROW
        if remainder_cols == 0:
            nr_cols_iter = [NR_WORDS_IN_ROW]*nr_full_tables
        else:
            nr_cols_iter = [NR_WORDS_IN_ROW]*nr_full_tables + [remainder_cols]
        return render_template('recall_words.html', memo=recall.memo,
                               nr_cols_iter=nr_cols_iter,
                               nr_words_in_column=NR_WORDS_IN_COLUMN,
                               seconds_remaining=seconds_remaining,
                               view=True,
                               recall=recall,
                               result=json.dumps(dict(recall.correction)))
    elif recall.memo.discipline == models.Discipline.dates:
        return render_template('recall_dates.html', memo=recall.memo,
                               data=sorted(recall.memo.data, key=lambda x: x[2]),
                               nr_dates_in_column=NR_DATES_IN_COLUMN,
                               seconds_remaining=seconds_remaining,
                               view=True,
                               recall=recall,
                               result=json.dumps(dict(recall.correction)))
    else:
        return 'Recall not implemented yet: ' + recall.memo.discipline


@app.route('/database/stories', methods=['GET', 'POST'])
@login_required
def db_stories():
    """Words database dashboard"""
    if request.method == 'GET':
        return render_template('db_stories.html')


@app.route('/database/stories/csv', methods=['GET'])
@login_required
def db_stories_csv():
    """Words database dashboard"""
    if request.method == 'GET':
        rows = (str(w) for w in models.Story.query.order_by(
            models.Story.language_id).all())
        return '<br>'.join(rows)


@app.route('/database/stories/table', methods=['GET', 'POST'])
@login_required
def table_stories():
    """Words database dashboard"""
    if request.method == 'GET':
        language = request.args.get('language')
        if language and language.strip().lower() != 'all':
            try:
                language = models.Language.query.filter_by(
                    language=language.strip().lower()).one()
            except sqlalchemy.orm.exc.NoResultFound:
                stories = list()
            else:
                stories = language.stories.order_by(models.Story.story).all()
        else:
            stories = models.Story.query.order_by(models.Story.story).all()
        return render_template('table_stories.html', stories=stories)

    elif request.method == 'POST':
        language = request.form['language'].strip().lower()
        try:
            language = models.Language.query.filter_by(language=language).one()
        except sqlalchemy.orm.exc.NoResultFound:
            language = models.Language(language=language)
            db.session.add(language)
            db.session.commit()
        text_area = request.form['data']
        nr_success = 0
        for line in text_area.split('\n'):
            line = line.strip()
            if line:
                if language.stories.filter(models.Story.story == line).first():
                    flash(f'Story "{line}" already exists in database.',
                          'warning')
                    continue
                try:
                    s = models.Story(
                        ip=request.remote_addr,
                        username=current_user.username,
                        story=line
                    )
                    s.language = language
                except ValueError as error:
                    flash(str(error), 'danger')
                else:
                    db.session.add(s)
                    nr_success += 1
        db.session.commit()
        if nr_success == 1:
            flash(f'Story successfully added to the database.',
                  'success')
        elif nr_success > 1:
            flash(f'{nr_success} stories successfully added to the database.',
                  'success')
        return 'Done'


@app.route('/database/words', methods=['GET', 'POST'])
@login_required
def db_words():
    """Words database dashboard"""
    if request.method == 'GET':
        return render_template('db_words.html')


@app.route('/database/words/csv', methods=['GET'])
@login_required
def db_words_csv():
    """Words database dashboard"""
    if request.method == 'GET':
        rows = (str(w) for w in models.Word.query.order_by(
            models.Word.language_id).all())
        return '<br>'.join(rows)


@app.route('/database/words/table', methods=['GET', 'POST'])
@login_required
def table_words():
    """Words database dashboard"""
    if request.method == 'GET':
        language = request.args.get('language')
        if language and language.strip().lower() != 'all':
            try:
                language = models.Language.query.filter_by(
                    language=language.strip().lower()).one()
            except sqlalchemy.orm.exc.NoResultFound:
                words = list()
            else:
                words = language.words.order_by(models.Word.word).all()
        else:
            words = models.Word.query.order_by(models.Word.word).all()
        distribution = collections.Counter(w.word_class.value for w in words)
        return render_template('table_words.html', words=words,
                               distribution=distribution, nr_words=len(words))

    elif request.method == 'POST':
        language = request.form['language'].strip().lower()
        word_class = request.form['word_class'].strip().lower()
        try:
            language = models.Language.query.filter_by(language=language).one()
        except sqlalchemy.orm.exc.NoResultFound:
            language = models.Language(language=language)
            db.session.add(language)
            db.session.commit()
        text_area = request.form['data']
        nr_exist = 0
        nr_added = 0
        nr_updated = 0
        for line in text_area.split('\n'):
            line = line.strip().lower()
            if line:
                db_word = language.words.filter(models.Word.word == line).first()
                if db_word:
                    if db_word.word_class.name == word_class:
                        nr_exist += 1
                    else:
                        for wc in models.WordClass:
                            if wc.name == word_class:
                                db_word.word_class = wc
                                nr_updated += 1
                                break
                    continue
                try:
                    w = models.Word(
                        ip=request.remote_addr,
                        username=current_user.username,
                        word=line,
                        word_class=word_class
                    )
                    w.language = language
                except ValueError as error:
                    flash(str(error), 'danger')
                else:
                    db.session.add(w)
                    nr_added += 1
        db.session.commit()
        if nr_exist > 0:
            plural = 's' if nr_exist > 1 else ''
            flash(f'{nr_exist} word{plural} already exist in database. Not added',
                  'warning')
        if nr_updated > 0:
            plural = 's' if nr_exist > 1 else ''
            flash(f'{nr_updated} word{plural} updated in database.', 'success')
        if nr_added > 0:
            plural = 's' if nr_exist > 1 else ''
            flash(f'{nr_added} word{plural} added to the database.', 'success')
        return 'Done'


@app.route('/database/almostcorrectwords', methods=['GET', 'POST'])
@login_required
def db_almost_correct_words():
    """Words database dashboard"""
    if request.method == 'GET':
        return render_template('db_almost_correct_words.html')

@app.route('/database/almostcorrectwords/table', methods=['GET', 'POST'])
@login_required
def table_almost_correct_words():
    """Words database dashboard"""
    if request.method == 'GET':
        language = request.args.get('language')
        if language and language.strip().lower() != 'all':
            try:
                language = models.Language.query.filter_by(
                    language=language.strip().lower()).one()
            except sqlalchemy.orm.exc.NoResultFound:
                mappings = list()
            else:
                mappings = language.almost_correct_words.filter_by(
                    user_id=current_user.id).order_by(models.AlmostCorrectWord.word).all()
        else:
            mappings = models.AlmostCorrectWord.query.filter_by(
                user_id=current_user.id).order_by(models.AlmostCorrectWord.word).all()
        return render_template('table_almost_correct_words.html', mappings=mappings)

    elif request.method == 'POST':
        language = request.form['language'].strip().lower()
        word = request.form['word'].strip().lower()
        almost_correct = request.form['almost_correct'].strip().lower()
        try:
            language = models.Language.query.filter_by(language=language).one()
        except sqlalchemy.orm.exc.NoResultFound:
            language = models.Language(language=language)
            db.session.add(language)
            db.session.commit()
        m = models.AlmostCorrectWord(
            ip=request.remote_addr,
            word=word,
            almost_correct=almost_correct
        )
        m.language = language
        m.user = current_user
        db.session.commit()
        return 'Done'
