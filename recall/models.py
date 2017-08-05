
import enum
from datetime import datetime

import os
#os.remove('recall/test.db')

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

    memo_data = db.Column(db.PickleType, nullable=False)
    language = db.Column(db.String(40))
    pattern = db.Column(db.String(255))

    def __init__(self, ip, user_id, key,
                 discipline, memo_time, recall_time,
                 memo_data, language, pattern):

        self.datetime = datetime.utcnow()
        self.ip = ip
        self.user_id = user_id
        self.key = key

        self.discipline = discipline
        self.memo_time = memo_time
        self.recall_time = recall_time
        self.memo_time = memo_time

        self.memo_data = memo_data
        self.language = language
        self.pattern = pattern

    def __repr__(self):
        return f'<MemoData {self.key}>'


class KeyStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(6), db.ForeignKey('memo_data.key'), unique=True)
    public = db.Column(db.Boolean, nullable=False)

    memo = db.relationship('MemoData', back_populates='key_status')

    def __init__(self, key, status):
        self.key = key
        self.public = status

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

    recall_data = db.Column(db.PickleType, nullable=False)
    time_remaining = db.Column(db.Float, nullable=False)
    #__table_args__ = (db.UniqueConstraint('account_id', 'name', name='_account_branch_uc'), )

    def __init__(self, ip, user_id, key,
                 recall_data, time_remaining):

        self.datetime = datetime.utcnow()
        self.ip = ip
        self.user_id = user_id
        self.key = key

        self.recall_data = recall_data
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


db.create_all()

if __name__ == '__main__':

    u1 = User('penlect')
    u2 = User('daniel')
    l1 = Language('swedish')
    l2 = Language('english')
    db.session.add(u1)
    db.session.add(u2)
    db.session.add(l1)
    db.session.add(l2)
    db.session.commit()
    print(User.query.all())
    print(Language.query.all())

    m = MemoData('123.231.43.5', u1.id, 'abc123',
                 Discipline.base2, 5, 15,
                 [1,2,3], 'swedish', '1,4,5')
    k = KeyStatus(m.key, True)
    d = XlsDoc(m.key, b'asdfkjadfasdf')

    r = RecallData('123.231.43.5', u1.id, m.key,
                 [4, 6, 2], 34.543)


    w = Word('123.231.43.5', u1.id, 'caffe',
              WordClass.abstract_noun, l1.id)

    db.session.add(m)
    db.session.add(k)
    db.session.add(d)
    db.session.add(r)
    db.session.add(w)
    db.session.commit()

    print(MemoData.query.all())
    print(RecallData.query.all())
    print(Word.query.all())

    print(u1.username, u1.memos, u1.recalls)
    print(u2.username, u2.memos, u2.recalls)

    print(m.discipline, m.user, m.recalls, m.key_status, m.key_status.public, m.xls_doc.data)
    print(r.user, r.key, r.memo, r.memo.key_status.public)