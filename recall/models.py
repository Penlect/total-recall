
import enum
from datetime import datetime
import re
import io
import os
import math
import random
import collections
from collections import namedtuple
import sqlalchemy.orm
# os.remove('test.db')

from recall import db, app
import recall.xls


class Discipline(enum.Enum):
    base2 = 'Binary Numbers'
    base10 = 'Decimal Numbers'
    words = 'Words'
    dates = 'Historical Dates'


class Item(enum.Enum):
    off_limits = 0
    gap = 1
    not_reached = 2
    correct = 3
    wrong = 4
    almost_correct = 5


class State(enum.Enum):
    private = 'Private'
    competition = 'Competition'
    public = 'Public'


class WordClass(enum.Enum):
    concrete_noun = "Concrete Noun"
    abstract_noun = "Abstract Noun"
    infinitive_verb = "Infinitive Verb"


def unique_lines_in_textarea(data: str, lower=False):
    """Get unique nonempty lines in textarea"""
    if lower:
        data = data.lower()
    lines = list()
    for line in data.split('\n'):
        line = line.strip()
        if line and line not in lines:
            lines.append(line)
    return lines


class DisciplineData:

    def __init__(self, data):
        self._data = tuple(data)
        self.cell_by_cell_result = None
        self._raw_score = None

    def __len__(self):
        return len(self._data)

    @property
    def data(self):
        return self._data

    def correct(self, recall_data):
        nr_items = len(self._data)
        start_of_emptiness = self.start_of_emptiness_before_index(recall_data,
                                                                  nr_items)
        result = [None]*len(recall_data)
        for i, user_value in enumerate(recall_data, start=0):
            if i >= nr_items:
                result[i] = Item.off_limits
            else:
                if not user_value.strip():
                    # Empty cell
                    if i < start_of_emptiness:
                        result[i] = Item.gap
                    else:
                        result[i] = Item.not_reached
                else:
                    result[i] = self.compare(user_value, i)
        self.cell_by_cell_result = result
        self.start_of_emptiness = start_of_emptiness

    def compare(self, guess, index):
        raise NotImplementedError

    @staticmethod
    def start_of_emptiness_before_index(data, index):
        index_of_empty_cell = index
        for i in reversed(range(index)):
            if data[i].strip():
                break
            else:
                index_of_empty_cell = i
        return index_of_empty_cell

    def _raw_score_digits(self, row_len):
        raw_score = 0
        cbc_r = self.cell_by_cell_result[0:self.start_of_emptiness]
        chunks = [cbc_r[0 + i:row_len + i]
                  for i in range(0, len(cbc_r), row_len)]
        for i, chunk in enumerate(chunks, start=1):
            if i == len(chunks):  # Last chunk
                row_len = len(chunk)
            c = collections.Counter(chunk)
            if c[Item.correct] == row_len:
                raw_score += c[Item.correct]
            elif c[Item.correct] == row_len - 1:
                raw_score += math.ceil(c[Item.correct]/2)
        return raw_score

class Base2Data(DisciplineData):
    enum = Discipline.base2

    def __init__(self, data, memo_time=-1, recall_time=-1):
        super().__init__(data)
        self.memo_time = memo_time
        self.recall_time = recall_time

    @classmethod
    def random(cls, nr_items, *args):
        return cls(random.randint(0, 1) for _ in range(nr_items))

    @classmethod
    def from_text(cls, text):
        return cls(int(digit) for digit in re.findall('[01]', text))

    def compare(self, guess: int, index: int):
        if int(guess) == self._data[index]:
            return Item.correct
        else:
            return Item.wrong

    @property
    def raw_score(self):
        return self._raw_score_digits(30)

    @property
    def points(self):
        if (self.memo_time, self.recall_time) == (5, 15):
            return math.ceil(self.raw_score*1000/1178)
        elif (self.memo_time, self.recall_time) == (30, 60):
            return math.ceil(self.raw_score*1000/4673)
        else:
            return -1

class Base10Data(DisciplineData):
    enum = Discipline.base10

    def __init__(self, data, memo_time=-1, recall_time=-1):
        super().__init__(data)
        self.memo_time = memo_time
        self.recall_time = recall_time

    @classmethod
    def random(cls, nr_items, *args):
        return cls(random.randint(0, 9) for _ in range(nr_items))

    @classmethod
    def from_text(cls, text):
        return cls(int(digit) for digit in re.findall('\d', text))

    def compare(self, guess: int, index: int):
        if int(guess) == self._data[index]:
            return Item.correct
        else:
            return Item.wrong

    @property
    def raw_score(self):
        return self._raw_score_digits(40)

    @property
    def points(self):
        if (self.memo_time, self.recall_time) == (5, 15):
            return math.ceil(self.raw_score*1000/547)
        elif (self.memo_time, self.recall_time) == (15, 30):
            return math.ceil(self.raw_score*1000/1112)
        elif (self.memo_time, self.recall_time) == (30, 60):
            return math.ceil(self.raw_score*1000/1752)
        elif (self.memo_time, self.recall_time) == (60, 120):
            return math.ceil(self.raw_score*1000/3234)
        else:
            return -1


class WordsData(DisciplineData):
    enum = Discipline.words

    def __init__(self, data, memo_time=-1, recall_time=-1):
        super().__init__(data)
        self.memo_time = memo_time
        self.recall_time = recall_time

    @classmethod
    def random(cls, nr_items, language):
        language = language.strip().lower()
        try:
            language = Language.query.filter_by(language=language).one()
        except sqlalchemy.orm.exc.NoResultFound:
            words = list()
        else:
            words = language.words
        words = [w.word for w in words]
        random.shuffle(words)
        data = tuple(words[0:nr_items])
        return cls(data)

    @classmethod
    def from_text(cls, text):
        return cls(unique_lines_in_textarea(text, lower=True))

    def compare(self, guess: str, index: int):
        guess = str(guess)
        if guess == self._data[index]:
            return Item.correct
        elif self._word_almost_correct(guess, index):
            return Item.almost_correct
        else:
            return Item.wrong

    def _word_almost_correct(self, guess: str, index: int):
        return False

    @property
    def raw_score(self):
        if self._raw_score is None:
            column_len = 20
            raw_score = 0
            cbc_r = self.cell_by_cell_result[0:self.start_of_emptiness]
            chunks = [cbc_r[0 + i:column_len + i]
                      for i in range(0, len(cbc_r), column_len)]
            for i, chunk in enumerate(chunks, start=1):
                if i == len(chunks):  # last chunk
                    column_len = len(chunk)
                c = collections.Counter(chunk)
                if c[Item.correct] + c[Item.almost_correct] == column_len:
                    raw_score += c[Item.correct]
                elif c[Item.correct] + c[Item.almost_correct] == column_len - 1:
                    raw_score += max(0, column_len / 2 - c[Item.almost_correct])
            self._raw_score = math.ceil(raw_score)
        return self._raw_score

    @property
    def points(self):
        if (self.memo_time, self.recall_time) == (5, 15):
            return math.ceil(self.raw_score*1000/125)
        elif (self.memo_time, self.recall_time) == (15, 30):
            return math.ceil(self.raw_score*1000/312)
        else:
            return -1


class DatesData(DisciplineData):
    enum = Discipline.dates

    def __init__(self, data, memo_time=-1, recall_time=-1):
        super().__init__(data)
        self.memo_time = memo_time
        self.recall_time = recall_time
        self._lookup = {recall_order: date for date, story, recall_order
                        in data}

    @classmethod
    def random(cls, nr_items, language):
        language = language.strip().lower()
        try:
            language = Language.query.filter_by(language=language).one()
        except sqlalchemy.orm.exc.NoResultFound:
            stories = list()
        else:
            stories = language.stories
        stories = [s.story for s in stories]
        if len(stories) < nr_items:
            nr_items = len(stories)
        random.shuffle(stories)
        stories = stories[0:nr_items]
        dates = [random.randint(1000, 2099) for _ in stories]
        recall_order = list(range(nr_items))
        random.shuffle(recall_order)
        data = list(zip(dates, stories, recall_order))
        random.shuffle(data)
        return cls(data)

    @classmethod
    def from_text(cls, text):
        lines = unique_lines_in_textarea(text, lower=False)
        stories = list()
        dates = list()
        for line in lines:
            date, story = line.split(maxsplit=1)
            if not (1000 <= int(date) <= 2099):
                raise ValueError(f'Date out of range: 1000 <= {date} <= 2099')
            stories.append(story.strip())
            dates.append(int(date))
        recall_order = list(range(len(stories)))
        random.shuffle(recall_order)
        data = list(zip(dates, stories, recall_order))
        return cls(data)

    def compare(self, guess: int, index: int):
        if int(guess) == self._lookup[index]:
            return Item.correct
        else:
            return Item.wrong

    @property
    def raw_score(self):
        if self._raw_score is None:
            raw_score = 0
            cbc_r = self.cell_by_cell_result[0:self.start_of_emptiness]
            c = collections.Counter(cbc_r)
            raw_score += c[Item.correct]
            raw_score -= c[Item.wrong]/2
            raw_score = max(0, raw_score)
            self._raw_score = math.ceil(raw_score)
        return self._raw_score

    @property
    def points(self):
        return math.ceil(self.raw_score*1000/125)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120))
    real_name = db.Column(db.String(120))
    country = db.Column(db.String(120))
    settings = db.Column(db.PickleType)
    blocked = db.Column(db.Boolean)

    memos = db.relationship('MemoData', backref="user",
                            cascade="save-update, merge, delete",
                            lazy='dynamic')
    recalls = db.relationship('RecallData', backref="user",
                              cascade="save-update, merge, delete",
                              lazy='dynamic')

    def __init__(self, username, password, email, real_name, country):
        self.datetime = datetime.utcnow()
        self.username = username
        self.password = password
        self.email = email
        self.real_name = real_name
        self.country = country
        self.settings = {
            'pattern_binary': '',
            'pattern_decimals': '',
            'pattern_words': '',
            'pattern_dates': ''
        }
        self.blocked = False

    @classmethod
    def from_request(cls, request):
        return cls(
            # Todo: restrict username characters and length
            username=request.form['username'].strip().lower(),
            password=request.form['password'],
            email=request.form['email'],
            real_name=request.form['real_name'],
            country=request.form['country']
        )

    # https://flask-login.readthedocs.io/en/latest/#your-user-class
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return not self.blocked

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.username

    def __repr__(self):
        return f'<User {self.username}>'


class MemoData(db.Model):

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    ip = db.Column(db.String(40), nullable=False)
    discipline = db.Column(db.Enum(Discipline), nullable=False)
    memo_time = db.Column(db.Integer, nullable=False)  # Seconds
    recall_time = db.Column(db.Integer, nullable=False)  # Seconds
    # Todo: change language to foreign key
    language = db.Column(db.String(40))
    data = db.Column(db.PickleType, nullable=False)
    generated = db.Column(db.Boolean, nullable=False)
    state = db.Column(db.Enum(State), nullable=False)

    # ForeignKeys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Relationships
    # Todo: make plural
    xls_doc = db.relationship('XlsDoc', backref='memo',
                              cascade="save-update, merge, delete",
                              lazy='dynamic')
    recalls = db.relationship('RecallData', backref='memo',
                              cascade="save-update, merge, delete",
                              lazy='dynamic')

    def __init__(self, ip,
                 discipline, memo_time, recall_time,
                 language, data,
                 generated, state=State.private):

        self.datetime = datetime.utcnow()
        self.ip = ip

        self.discipline = discipline
        if memo_time < 0:
            raise ValueError(f'memo_time cannot be negative: {memo_time}')
        self.memo_time = memo_time
        if recall_time < 0:
            raise ValueError(f'recall_time cannot be negative: {recall_time}')
        self.recall_time = recall_time
        # Language must be provided if words and dates,
        # set it to None for other disciplines.
        if discipline == Discipline.words or \
                        discipline == Discipline.dates:
            if not language:
                raise ValueError(
                    f'Language must be provided for "{discipline.value}"')
            self.language = language.strip().lower()
        else:
            self.language = None
        self.data = data
        self.generated = generated
        self.state = state

    @classmethod
    def from_request(cls, request, user):
        form = request.form
        ip = request.remote_addr

        d = form['discipline'].strip().lower()
        if d == 'binary':
            maker = Base2Data
        elif d == 'decimals':
            maker = Base10Data
        elif d == 'words':
            maker = WordsData
        elif d == 'dates':
            maker = DatesData
        else:
            raise ValueError(f'Invalid discipline form form: "{d}"')

        memo_time, recall_time = form['time'].strip().lower().split(',')
        memo_time, recall_time = int(memo_time), int(recall_time)

        language = form.get('language')
        data = form.get('data')
        nr_items = form.get('nr_items')
        assert data or nr_items, "data or nr_items must be provided!"

        generated = data is None
        if generated:
            # If data was not provided, we must generate it ourselves.
            # In order to do so we need to know how many items to
            # generate, + language if words or dates.
            discipline_data = maker.random(int(nr_items), language)
        else:
            # Parse text data user provided
            discipline_data = maker.from_text(data)

        m = cls(
            ip=ip,
            discipline=discipline_data.enum,
            memo_time=memo_time,
            recall_time=recall_time,
            language=language,
            data=discipline_data.data,
            generated=generated,
            state=State.private
        )
        m.user = user
        return m

    def get_data_handler(self):
        for cls in (Base2Data, Base10Data, WordsData, DatesData):
            if self.discipline == cls.enum:
                return cls(self.data, self.memo_time, self.recall_time)
        raise AssertionError(f'Now Data class for {self.memo.discipline}.')

    def __repr__(self):
        return f'<MemoData {self.id}>'


class XlsDoc(db.Model):

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    pattern = db.Column(db.String(120))
    data = db.Column(db.PickleType, nullable=False)

    # ForeignKeys
    memo_id = db.Column(db.Integer, db.ForeignKey('memo_data.id'))

    def __init__(self, pattern, data):
        self.pattern = pattern
        self.data = data

    @classmethod
    def from_memo(cls, memo, pattern):
        """Take relevant data of memo and create table

        The table can later be saved to disk as .xls file
        with the .save() function.
        """

        # Depending on which discipline we have, we'll need discipline
        # specific table and description
        if memo.discipline == Discipline.base2:
            table = recall.xls.get_binary_table
        elif memo.discipline == Discipline.base10:
            table = recall.xls.get_decimal_table
        elif memo.discipline == Discipline.words:
            table = recall.xls.get_words_table
        elif memo.discipline == Discipline.dates:
            table = recall.xls.get_dates_table
        else:
            raise ValueError(
                f'Invalid discipline: "{memo.discipline}"'
            )
        # The description include language if available
        nr_items = len(memo.data)
        if memo.language:
            description = f'{memo.discipline.value}, {memo.language.title()}, {nr_items} st.'
        else:
            description = f'{memo.discipline.value}, {nr_items} st.'
        # Create header
        header = recall.xls.Header(
            title='Svenska Minnesförbundet',
            description=description,
            recall_key=memo.id,
            memo_time=memo.memo_time,
            recall_time=memo.recall_time
        )
        # Create table
        t = table(header=header, pattern=pattern)
        # Update the table with data
        for n in memo.data:
            t.add_item(n)
        # Write xls file to file object
        filedata = io.BytesIO()
        t.save(filedata)
        filedata.seek(0)
        # Create instance and attach memo reference
        xls_doc = cls(pattern, filedata)
        xls_doc.memo = memo
        return xls_doc

    @property
    def filename(self):
        """Create xls filename containing blob data"""
        # Todo: Think about this
        XLS_FILENAME_FMT = '{discipline}_{nr}st_{language}_{memo_time}-{recall_time}min_p{pattern_str}_{correction}_{recall_key}'
        return None


    def __repr__(self):
        return f'<XlsDoc {self.memo_id}; p={self.pattern}; {len(self.data)} bytes>'


class RecallData(db.Model):

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    ip = db.Column(db.String(40), nullable=False)
    data = db.Column(db.PickleType, nullable=False)
    time_remaining = db.Column(db.Float, nullable=False)

    # ForeignKeys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    memo_id = db.Column(db.Integer, db.ForeignKey('memo_data.id'), nullable=False)

    # Relationships
    correction = db.relationship('Correction', backref='recall',
                                 cascade="save-update, merge, delete",
                                 uselist=False)

    def __init__(self, ip, data, time_remaining: float):

        self.datetime = datetime.utcnow()
        self.ip = ip
        self.data = data
        self.time_remaining = time_remaining

    @classmethod
    def from_request(cls, request, user):
        form = request.form
        ip = request.remote_addr
        memo_id = form['memo_id'].strip().lower()
        memo = MemoData.query.filter_by(id=memo_id).one()
        time_remaining = float(form['seconds_remaining'])

        data = list()
        for i in range(len(form)):
            try:
                data.append(form[f'recall_cell_{i}'])
            except KeyError:
                break

        r = RecallData(
            ip=ip,
            data=data,
            time_remaining=time_remaining
        )
        r.user = user
        r.memo = memo
        return r

    def __repr__(self):
        return f'<RecallData {self.memo_id}>'


class Correction(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    off_limits = db.Column(db.Integer, nullable=False)
    gap = db.Column(db.Integer, nullable=False)
    not_reached = db.Column(db.Integer, nullable=False)
    correct = db.Column(db.Integer, nullable=False)
    wrong = db.Column(db.Integer, nullable=False)
    almost_correct = db.Column(db.Integer, nullable=False)

    raw_score = db.Column(db.Float, nullable=False)
    points = db.Column(db.Float, nullable=False)
    cell_by_cell = db.Column(db.PickleType)

    # ForeignKeys
    recall_id = db.Column(db.Integer, db.ForeignKey('recall_data.id'))

    def __init__(self, raw_score, points, cell_by_cell):  # update with __init__
        c = collections.Counter(cell_by_cell)

        self.off_limits = c[Item.off_limits]
        self.gap = c[Item.gap]
        self.not_reached = c[Item.not_reached]
        self.correct = c[Item.correct]
        self.wrong = c[Item.wrong]
        self.almost_correct = c[Item.almost_correct]

        self.raw_score = raw_score
        self.points = points
        self.cell_by_cell = cell_by_cell

    def __iter__(self):
        yield from (
            ('off_limits', self.off_limits),
            ('gap', self.gap),
            ('not_reached', self.not_reached),
            ('correct', self.correct),
            ('wrong', self.wrong),
            ('almost_correct', self.almost_correct),
            ('raw_score', self.raw_score),
            ('points', self.points),
            ('cell_by_cell', [i.name for i in self.cell_by_cell])
        )


class AlmostCorrectWord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    ip = db.Column(db.String(40), nullable=False)

    word = db.Column(db.String(80), nullable=False)
    almost_correct = db.Column(db.String(80), nullable=False)

    # ForeignKeys
    language_id = db.Column(db.Integer, db.ForeignKey('language.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __init__(self, ip, word, almost_correct):
        self.datetime = datetime.utcnow()
        self.ip = ip
        self.word = word
        self.almost_correct = almost_correct


class Language(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(80), unique=True, nullable=False)

    # Relationships
    words = db.relationship('Word', backref="language", lazy='dynamic')
    stories = db.relationship('Story', backref="language", lazy='dynamic')
    almost_correct_words = db.relationship('AlmostCorrectWord',
                                           backref="language", lazy='dynamic')

    def __init__(self, language):
        self.language = language

    def __repr__(self):
        return f'<Language {self.language}>'


# Todo: Database of almost correct words during competition
class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    ip = db.Column(db.String(40), nullable=False)
    # The username is not a ForeignKey since we don't want the
    # word to be deleted if the user deletes his/her account
    username = db.Column(db.String(40), nullable=False)

    word = db.Column(db.String(80), nullable=False)
    word_class = db.Column(db.Enum(WordClass), nullable=False)

    # ForeignKeys
    language_id = db.Column(db.Integer, db.ForeignKey('language.id'))

    def __init__(self, ip, username, word, word_class):
        self.datetime = datetime.utcnow()
        self.ip = ip
        self.username = username
        self.word = word
        self.word_class = word_class

    def __repr__(self):
        return f'<Word {self.word}>'


class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    ip = db.Column(db.String(40), nullable=False)
    # The username is not a ForeignKey since we don't want the
    # story to be deleted if the user deletes his/her account
    username = db.Column(db.String(40), nullable=False)

    story = db.Column(db.String(100), nullable=False)

    # ForeignKeys
    language_id = db.Column(db.Integer, db.ForeignKey('language.id'))

    def __init__(self, ip, username, story):
        self.datetime = datetime.utcnow()
        self.ip = ip
        self.username = username
        story = story.strip()
        nr_words = len(story.split())
        if nr_words > 6:
            raise ValueError('Maximum 6 words allowed in a story. '
                             f'{nr_words} words found in "{story}".')
        self.story = story

    def __repr__(self):
        return f'<Story "{self.story}">'
