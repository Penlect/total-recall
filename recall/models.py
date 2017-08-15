
import enum
from datetime import datetime
import re
import io
import os
import random
from collections import namedtuple

# os.remove('test.db')

from recall import db, app
import recall.xls


# Todo: Move random data creation to classes here
DATABASE_WORDS = os.path.join(app.root_path, 'db_words.txt')
DATABASE_STORIES = os.path.join(app.root_path, 'db_stories.txt')
WordEntry = namedtuple('WordEntry', 'language value name date word_class')
StoryEntry = namedtuple('StoryEntry', 'language value name date')


class Discipline(enum.Enum):
    base2 = 'Binary Numbers'
    base10 = 'Decimal Numbers'
    words = 'Words'
    dates = 'Historical Dates'


class State(enum.Enum):
    private = 'Private'
    competition = 'Competition'
    public = 'Public'


class WordClass(enum.Enum):
    concrete_noun = "Concrete Noun"
    abstract_noun = "Abstract Noun"
    infinitive_verb = "Infinitive Verb"


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


class DisciplineData:

    def __init__(self, data):
        self._data = tuple(data)

    def __len__(self):
        return len(self._data)

    @property
    def data(self):
        return self._data


class Base2Data(DisciplineData):
    enum = Discipline.base2

    def __init__(self, data):
        super().__init__(data)

    @classmethod
    def random(cls, nr_items, *args):
        return cls(random.randint(0, 1) for _ in range(nr_items))

    @classmethod
    def from_text(cls, text):
        return cls(int(digit) for digit in re.findall('[01]', text))


class Base10Data(DisciplineData):
    enum = Discipline.base10

    def __init__(self, data):
        super().__init__(data)

    @classmethod
    def random(cls, nr_items, *args):
        return cls(random.randint(0, 9) for _ in range(nr_items))

    @classmethod
    def from_text(cls, text):
        return cls(int(digit) for digit in re.findall('\d', text))


class WordsData(DisciplineData):
    enum = Discipline.words

    def __init__(self, data):
        super().__init__(data)

    @classmethod
    def random(cls, nr_items, language):
        language = language.strip().lower()
        words = [word.value for word in
                 load_database(DATABASE_WORDS, WordEntry)
                 if word.language == language]
        random.shuffle(words)
        data = tuple(words[0:nr_items])
        return cls(data)

    @classmethod
    def from_text(cls, text):
        return cls(unique_lines_in_textarea(text, lower=True))


class DatesData(DisciplineData):
    enum = Discipline.dates

    def __init__(self, data):
        super().__init__(data)

    @classmethod
    def random(cls, nr_items, language):
        language = language.strip().lower()
        stories = [story.value for story in
                   load_database(DATABASE_STORIES, StoryEntry)
                   if story.language == language]
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
        random.shuffle(data)
        return cls(data)


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

    def __init__(self, username, email, real_name, country):
        self.datetime = datetime.utcnow()
        self.username = username
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
    #__table_args__ = (db.UniqueConstraint('account_id', 'name', name='_account_branch_uc'), )

    def __init__(self, ip, data, time_remaining: float):

        self.datetime = datetime.utcnow()
        self.ip = ip
        self.data = data
        self.time_remaining = time_remaining

    @classmethod
    def from_request(cls, request, user):
        form = request.form
        ip = request.remote_addr
        key = form['key'].strip().lower()
        memo = MemoData.query.filter_by(id=key).one()
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


class Language(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(80), unique=True, nullable=False)
    words = db.relationship('Word', backref="language", lazy='dynamic')

    def __init__(self, language):
        self.language = language

    def __repr__(self):
        return f'<Language {self.language}>'


class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    ip = db.Column(db.String(40), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    language_id = db.Column(db.Integer, db.ForeignKey('language.id'))
    user = db.relationship('User')

    word = db.Column(db.String(80), nullable=False)
    word_class = db.Column(db.Enum(WordClass), nullable=False)

    def __init__(self, ip, word, word_class):

        self.datetime = datetime.utcnow()
        self.ip = ip
        self.word = word
        self.word_class = word_class

    def __repr__(self):
        return f'<Word {self.word}>'