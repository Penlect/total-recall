
import enum
from datetime import datetime
import re

import os
#os.remove('test.db')

from recall import db


class Discipline(enum.Enum):
    base2 = 'Binary Numbers'
    base10 = 'Decimal Numbers'
    words = 'Words'
    dates = 'Historical Dates'


class WordClass(enum.Enum):
    concrete_noun = "Concrete Noun"
    abstract_noun = "Abstract Noun"
    infinitive_verb = "Infinitive Verb"


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120))
    first_name = db.Column(db.String(120))
    last_name = db.Column(db.String(120))

    memos = db.relationship('MemoData', back_populates="user")
    recalls = db.relationship('RecallData', back_populates="user")

    def __init__(self, username):
        self.username = username

    def __repr__(self):
        return f'<User {self.username}>'


class MemoData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    ip = db.Column(db.String(40), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates="memos")

    key = db.Column(db.String(6), unique=True, nullable=False)
    key_status = db.relationship('KeyStatus', back_populates='memo',
                              uselist=False)
    xls_doc = db.relationship('XlsDoc', back_populates='memo',
                              uselist=False)
    recalls = db.relationship('RecallData', back_populates='memo')

    discipline = db.Column(db.Enum(Discipline), nullable=False)
    # The unit will be seconds
    memo_time = db.Column(db.Integer, nullable=False)
    recall_time = db.Column(db.Integer, nullable=False)

    language = db.Column(db.String(40))
    pattern = db.Column(db.String(255))
    data = db.Column(db.PickleType, nullable=False)
    generated = db.Column(db.Boolean, nullable=False)

    def __init__(self, ip, user_id, key,
                 discipline, memo_time, recall_time,
                 language, pattern, data,
                 generated):

        self.datetime = datetime.utcnow()
        self.ip = ip
        self.user_id = user_id
        self.key = key

        self.discipline = discipline
        if memo_time < 0:
            raise ValueError(f'memo_time cannot be negative: {memo_time}')
        self.memo_time = memo_time
        if recall_time < 0:
            raise ValueError(f'recall_time cannot be negative: {recall_time}')
        self.recall_time = recall_time

        if discipline == Discipline.words or \
                        discipline == Discipline.dates:
            if not language:
                raise ValueError(
                    f'Language must be provided for "{discipline.value}"')
            self.language = language.strip().lower()
        else:
            self.language = None
        if pattern.strip():
            if not re.fullmatch('(\d+)(,\s*\d+\s*)*', pattern):
                raise ValueError('The pattern provided doesn\'t match a '
                                 'comma separated list of numbers.')
        self.pattern = pattern
        self.data = data
        self.generated = generated

    def __repr__(self):
        return f'<MemoData {self.key}>'


class KeyStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(6), db.ForeignKey('memo_data.key'), unique=True)
    public = db.Column(db.Boolean, nullable=False)

    memo = db.relationship('MemoData', back_populates='key_status')

    def __init__(self, key, public: bool):
        self.key = key
        self.public = public

    def __repr__(self):
        return f'<KeyStatus {self.key}:public={self.public}>'


class XlsDoc(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(6), db.ForeignKey('memo_data.key'), unique=True)
    data = db.Column(db.PickleType, nullable=False)

    memo = db.relationship('MemoData', back_populates='xls_doc')

    def __init__(self, key, data):
        self.key = key
        self.data = data

    def __repr__(self):
        return f'<XlsDoc {self.key}>'


class RecallData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    ip = db.Column(db.String(40), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', back_populates="recalls")

    key = db.Column(db.String(6), db.ForeignKey('memo_data.key'))
    memo = db.relationship('MemoData', back_populates='recalls')

    data = db.Column(db.PickleType, nullable=False)
    time_remaining = db.Column(db.Float, nullable=False)
    #__table_args__ = (db.UniqueConstraint('account_id', 'name', name='_account_branch_uc'), )

    def __init__(self, ip, user_id, key,
                 data, time_remaining):

        self.datetime = datetime.utcnow()
        self.ip = ip
        self.user_id = user_id
        self.key = key

        self.data = data
        self.time_remaining = time_remaining

    def __repr__(self):
        return f'<RecallData {self.key}>'


class Language(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(80), unique=True, nullable=False)
    words = db.relationship('Word', back_populates="language", lazy='dynamic')

    def __init__(self, language):
        self.language = language

    def __repr__(self):
        return f'<Language {self.language}>'


class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    ip = db.Column(db.String(40), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User')

    word = db.Column(db.String(80), nullable=False)
    word_class = db.Column(db.Enum(WordClass), nullable=False)
    language_id = db.Column(db.Integer, db.ForeignKey('language.id'))
    language = db.relationship('Language', back_populates="words")

    def __init__(self, ip, user_id,
                 word, word_class, language):

        self.datetime = datetime.utcnow()
        self.ip = ip
        self.user_id = user_id

        self.word = word
        self.word_class = word_class
        self.language_id = language

    def __repr__(self):
        return f'<Word {self.word}>'