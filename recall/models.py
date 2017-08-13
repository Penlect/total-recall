
import enum
from datetime import datetime
import re

import os

# os.remove('test.db')

from recall import db


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
    xls_doc = db.relationship('XlsDoc', backref='memo',
                              cascade="save-update, merge, delete")
    recalls = db.relationship('RecallData', backref='memo',
                              cascade="save-update, merge, delete")

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