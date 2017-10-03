"""Defines Database table classes

Dependency
----------
    User
    MemoData -> User, Language
    RecallData -> User, MemoData
    Correction -> RecallData
    Language
    AlmostCorrectWord -> User, Language
    Word -> Language
    Story -> Language

"""
import enum
from datetime import datetime
import re
import io
import math
import random
import collections
import itertools

import sqlalchemy.orm
from passlib.hash import sha256_crypt

from recall import db, SCORE
import recall.xls


class Discipline(enum.Enum):
    """Define valid disciplines and their official names"""
    base2 = 'Binary Numbers'
    base10 = 'Decimal Numbers'
    words = 'Words'
    dates = 'Historical Dates'
    spoken = 'Spoken Numbers'
    cards = 'Cards'
    names = 'Names & Faces'
    images = 'Images'


class Item(enum.Enum):
    """Status of a corrected item of information of a recall"""
    off_limits = 0
    gap = 1
    not_reached = 2
    correct = 3
    wrong = 4
    almost_correct = 5


class State(enum.Enum):
    """State of Discipline"""
    private = 'Private'
    competition = 'Competition'
    public = 'Public'


class WordClass(enum.Enum):
    """Word class type of word"""
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


class RegisterUserError(Exception):
    """User provides bad/invalid data during registration"""
    pass


class User(db.Model):
    # Fields
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    # Todo: email not used in any way
    email = db.Column(db.String(120))
    real_name = db.Column(db.String(120))
    country = db.Column(db.String(120))
    settings = db.Column(db.PickleType)
    blocked = db.Column(db.Boolean)

    # Relationships
    memos = db.relationship('MemoData', backref="user",
                            cascade="save-update, merge, delete",
                            lazy='dynamic')
    recalls = db.relationship('RecallData', backref="user",
                              cascade="save-update, merge, delete",
                              lazy='dynamic')
    almost_correct_words = db.relationship('AlmostCorrectWord', backref="user",
                              cascade="save-update, merge, delete",
                              lazy='dynamic')

    def __init__(self, username, password, email, real_name, country):
        self.datetime = datetime.utcnow()
        self.username = self._valid_username(username)
        self.password = sha256_crypt.hash(self._valid_password(password))
        self.email = self._verify_length(email, length=40)
        self.real_name = self._verify_length(real_name, length=30)
        self.country = self._verify_length(country, length=30)
        self.settings = {
            'pattern_binary': '',
            'pattern_decimals': '',
            'pattern_words': '',
            'pattern_dates': '',
            'pattern_cards': '',
            'card_colors': False
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

    @staticmethod
    def _valid_username(username):
        """Make sure the username is OK to use as a username"""
        candidate = username.strip().lower()
        User._verify_length(candidate, length=12)
        if not re.match(r'[\w_]+$', candidate):
            raise RegisterUserError(
                f'Username "{candidate}" contains forbidden characters.')
        elif User.query.filter_by(username=candidate).first() is not None:
            raise RegisterUserError(
                f'Username "{candidate}" is already taken.')
        else:
            return candidate

    @staticmethod
    def _valid_password(pwd):
        """Make sure the password is OK to use as a password"""
        MIN_LENGTH = 8
        if len(pwd) < MIN_LENGTH:
            raise RegisterUserError(
                f'Password to short! '
                f'Minimum {MIN_LENGTH} characters required.')
        return pwd

    @staticmethod
    def _verify_length(parameter, length):
        if len(parameter) > length:
            raise RegisterUserError(
                f'Parameter "{parameter}" is too long! '
                f'Maximum {length} characters allowed.')
        return parameter


class MemoData(db.Model):

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    ip = db.Column(db.String(40), nullable=False)
    discipline = db.Column(db.Enum(Discipline), nullable=False)
    memo_time = db.Column(db.Integer, nullable=False)  # Seconds
    recall_time = db.Column(db.Integer, nullable=False)  # Seconds
    data = db.Column(db.PickleType, nullable=False)
    generated = db.Column(db.Boolean, nullable=False)
    state = db.Column(db.Enum(State), nullable=False)

    # ForeignKeys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    language_id = db.Column(db.Integer, db.ForeignKey('language.id'))

    # Relationships
    recalls = db.relationship('RecallData', backref='memo',
                              cascade="save-update, merge, delete",
                              lazy='dynamic')

    __mapper_args__ = {
        'polymorphic_on': discipline
    }

    def __init__(self, ip, discipline,
                 memo_time, recall_time,
                 data,
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
        self.data = tuple(data)
        self.generated = generated
        self.state = state

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.id}>'

    @staticmethod
    def from_request(request, user):
        form = request.form
        ip = request.remote_addr

        d = form['discipline'].strip().lower()
        if d == 'base2':
            cls = Base2Data
            discipline = Discipline.base2
        elif d == 'base10':
            cls = Base10Data
            discipline = Discipline.base10
        elif d == 'words':
            cls = WordsData
            discipline = Discipline.words
        elif d == 'dates':
            cls = DatesData
            discipline = Discipline.dates
        elif d == 'spoken':
            cls = SpokenData
            discipline = Discipline.spoken
        elif d == 'cards':
            cls = CardData
            discipline = Discipline.cards
        else:
            raise ValueError(f'Invalid discipline form form: "{d}"')

        memo_time, recall_time = form['time'].strip().split(',')
        memo_time, recall_time = int(memo_time), int(recall_time)
        language = form.get('language')
        if language:
            language = language.strip().lower()
            try:
                language = Language.query.filter_by(language=language).one()
            except sqlalchemy.orm.exc.NoResultFound:
                language = Language(language=language)
                db.session.add(language)
                db.session.commit()
        data = form.get('data')
        nr_items = form.get('nr_items')
        if not (data or nr_items):
            raise ValueError("data or nr_items must be provided!")

        generated = data is None
        if generated:
            # If data was not provided, we must generate it ourselves.
            # In order to do so we need to know how many items to
            # generate, + language if words or dates.
            discipline_data = cls.random(int(nr_items), language)
        else:
            # Parse text data user provided
            discipline_data = cls.from_text(data)

        m = cls(
            ip=ip,
            discipline=discipline,
            memo_time=memo_time,
            recall_time=recall_time,
            data=discipline_data,
            generated=generated,
            state=State.private
        )
        m.user = user
        m.language = language
        return m

    def compare(self, guess: int, index: int):
        """Check if guess match data at index"""
        if int(guess) == self.data[index]:
            return Item.correct
        else:
            return Item.wrong

    @staticmethod
    def _raw_score_digits(cbc_r, row_len):
        """Algorithm for correcting numerical disciplines

        Trailing off_limits values in cbc_r are not allowed
        """
        raw_score = 0
        rows = [cbc_r[0 + i:row_len + i]
                  for i in range(0, len(cbc_r), row_len)]
        for i, row in enumerate(rows, start=1):
            if i == len(rows):  # Last chunk
                row_len = len(row)
            c = collections.Counter(row)
            if c[Item.correct] == row_len:
                raw_score += c[Item.correct]
            elif c[Item.correct] == row_len - 1:
                raw_score += math.ceil(c[Item.correct]/2)
        return raw_score

    def get_xls_filedata(self, pattern, **kwargs):
        """Take relevant data of memo and create table

        The table can later be saved to disk as .xls file.
        """
        # The description include language if available
        nr_items = len(self.data)
        if self.language:
            description = f'{self.discipline.value}, ' \
                          f'{self.language.language.title()}, {nr_items} st.'
        else:
            description = f'{self.discipline.value}, {nr_items} st.'
        # Create header
        header = recall.xls.Header(
            title='Svenska Minnesförbundet',
            description=description,
            recall_key=self.id,
            memo_time=self.memo_time,
            recall_time=self.recall_time
        )
        # Create table
        t = self.xls_table(header=header, pattern=pattern, **kwargs)
        # Update the table with data
        for n in self.data:
            t.add_item(n)
        # Write xls file to file object
        filedata = io.BytesIO()
        t.save(filedata)
        filedata.seek(0)
        return filedata

    def get_xls_filename(self, pattern, card_colors):
        """Compute filename of xls file

        The filename must map uniquely to the xls content,
        since the filename will be used to check if the xls
        document already exists on the server filesystem,
        so it should not be recreated.
        """
        filename_fmt = ('{id}_{discipline}_{memo_time}-{recall_time}min'
                        '_{language}_{nr}st_p{pattern_str}.xls')
        if card_colors:
            # Used for Cards
            filename_fmt = filename_fmt.replace('.xls', '_c.xls')
        filename = filename_fmt.format(
            id=self.id,
            discipline=self.discipline.value.replace(' ', '_'),
            memo_time=self.memo_time,
            recall_time=self.recall_time,
            language=self.language.language.replace(' ', '_').title()\
                if self.language else '',
            nr=len(self.data),
            pattern_str=pattern if pattern is not None else ''
        )
        return filename

    def _points_coefficient(self):
        min = ','.join((str(self.memo_time), str(self.recall_time)))
        if self.discipline.name == 'spoken':
            min = '0,0'
        return SCORE[self.discipline.name][min]

    def points(self, raw_score):
        try:
            k = self._points_coefficient()
        except KeyError:
            return -1
        else:
            return round(raw_score*1000/k)


class Base2Data(MemoData):
    __mapper_args__ = {
        'polymorphic_identity': Discipline.base2,
    }
    xls_table = staticmethod(recall.xls.get_binary_table)

    @staticmethod
    def random(nr_items, *args):
        return tuple(random.randint(0, 1) for _ in range(nr_items))

    @staticmethod
    def from_text(text):
        return tuple(int(digit) for digit in re.findall('[01]', text))

    def raw_score(self, cbc_r):
        return self._raw_score_digits(cbc_r, 30)


class Base10Data(MemoData):
    __mapper_args__ = {
        'polymorphic_identity': Discipline.base10,
    }
    xls_table = staticmethod(recall.xls.get_decimal_table)

    @staticmethod
    def random(nr_items, *args):
        return tuple(random.randint(0, 9) for _ in range(nr_items))

    @staticmethod
    def from_text(text):
        return tuple(int(digit) for digit in re.findall('\d', text))

    def raw_score(self, cbc_r):
        return self._raw_score_digits(cbc_r, 40)


class SpokenData(MemoData):
    __mapper_args__ = {
        'polymorphic_identity': Discipline.spoken,
    }
    xls_table = staticmethod(recall.xls.get_decimal_table)

    @staticmethod
    def random(nr_items, *args):
        return tuple(random.randint(0, 9) for _ in range(nr_items))

    @staticmethod
    def from_text(text):
        return tuple(int(digit) for digit in re.findall('\d', text))

    @staticmethod
    def raw_score(cbc_r):
        """Calculate raw score
        1.  One point is awarded for every correct consecutive digit that the
            competitor writes down from the first digit of the spoken
            sequence.
        2.  As soon as the competitor makes their first mistake, that is
            where the marking stops. For example, if a competitor recalls
            127 digits but makes a mistake at the 43 rd  digit, then the score
            will be 42. If a competitor recalled 200 digits but made a
            mistake on the first digit the score would be 0.
        """
        consecutive = 0
        for cell in cbc_r:
            if cell == Item.correct:
                consecutive += 1
            else:
                break
        return consecutive

    def points(self, raw_score):
        """Overrides default implementation"""
        try:
            k = self._points_coefficient()
        except KeyError:
            return -1
        else:
            return round(math.sqrt(raw_score)*k)


class WordsData(MemoData):
    """Represents Words data - tuple of strings"""
    __mapper_args__ = {
        'polymorphic_identity': Discipline.words,
    }
    xls_table = staticmethod(recall.xls.get_words_table)

    @staticmethod
    def random(nr_items, language):
        words = [w.word for w in language.words]
        random.shuffle(words)
        data = tuple(words[0:nr_items])
        return data

    @staticmethod
    def from_text(text):
        return tuple(unique_lines_in_textarea(text, lower=True))

    def compare(self, guess: str, index: int):
        guess = str(guess)
        if guess == self.data[index]:
            return Item.correct
        elif self._word_almost_correct(guess, index):
            return Item.almost_correct
        else:
            return Item.wrong

    def _word_almost_correct(self, guess: str, index: int):
        if not hasattr(self, '_almost_correct_word_lookup'):
            mappings = self.user.almost_correct_words.all()
            self._almost_correct_word_lookup = mappings
        for m in self._almost_correct_word_lookup:
            if m.word == self.data[index] and m.language == self.language:
                if m.almost_correct == guess:
                    return True
        return False

    @staticmethod
    def raw_score(cbc_r):
        column_len = 20
        raw_score = 0
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
        raw_score = math.ceil(raw_score)
        return raw_score


class InvalidHistoricalDate(Exception):
    pass


class DatesData(MemoData):
    """Represents Historical Dates data

    A Historical Date is represented as a tuple with three elements:
        (1000 <= date <=2099, Story of maximum six words, shuffle_index)
        types: (int, str, int)
    The shuffle_index is used to define how the list of stories will
    be shuffled when printed during recall.

    For example:
        (2006, 'House burns down', 2)
        (1998, 'Eternal love', 0)
        (2009, 'Certain death prevented', 1)
        (2003, 'Life never the same again', 3)
    Will during recall be printed in this order:
        (1998, 'Eternal love', 0)
        (2009, 'Certain death prevented', 1)
        (2006, 'House burns down', 2)
        (2003, 'Life never the same again', 3)
    """
    __mapper_args__ = {
        'polymorphic_identity': Discipline.dates,
    }
    xls_table = staticmethod(recall.xls.get_dates_table)

    @property
    def lookup(self):
        if not hasattr(self, '_lookup'):
            self._lookup = {recall_order: date for date, story, recall_order
                            in self.data}
        return self._lookup

    @staticmethod
    def random(nr_items, language):
        stories = [s.story for s in language.stories]
        nr_items = min(nr_items, len(stories))
        random.shuffle(stories)
        stories = stories[0:nr_items]
        dates = random.sample(range(1000, 2100), len(stories))
        recall_order = list(range(nr_items))
        random.shuffle(recall_order)
        data = list(zip(dates, stories, recall_order))
        return data

    @staticmethod
    def from_text(text):
        lines = unique_lines_in_textarea(text, lower=False)
        stories = list()
        dates = list()
        for line in lines:
            try:
                date, story = line.split(maxsplit=1)
            except ValueError:
                raise InvalidHistoricalDate(
                    f'Invalid Historical Date: "{line}"')
            try:
                date = int(date)
            except ValueError:
                raise InvalidHistoricalDate(
                    f'Failed to interpret "{date}" '
                    'as a date between 1000 and 2099'
                )
            if not (1000 <= int(date) <= 2099):
                raise InvalidHistoricalDate(
                    f'Date out of range: 1000 <= {date} <= 2099')
            if date in dates:
                raise InvalidHistoricalDate(
                    f'Date "{date}" occurs twice.'
                )
            else:
                dates.append(date)
            story = story.strip()
            if story in stories:
                raise InvalidHistoricalDate(
                    f'Story "{story}" occurs twice.'
                )
            else:
                stories.append(story)

        recall_order = list(range(len(stories)))
        random.shuffle(recall_order)
        data = list(zip(dates, stories, recall_order))
        return data

    def compare(self, guess: int, index: int):
        if int(guess) == self.lookup[index]:
            return Item.correct
        else:
            return Item.wrong

    @staticmethod
    def raw_score(cbc_r):
        """Calculate raw score
        1.  A point is awarded for every correctly assigned year.
        2.  Half a mark is deducted for an incorrectly assigned year.
        4.  There is no penalty for missing dates.
        5.  The results are totalled. The Total Score is rounded up to the
        nearest whole number, i.e. 45.5 is rounded up to 46.
        6.  If the final score is a negative, it is rounded up to zero.

        :param cbc_r: Cell by cell result
        :return: Raw score
        """
        raw_score = 0
        c = collections.Counter(cbc_r)
        raw_score += c[Item.correct]
        raw_score -= c[Item.wrong]/2
        raw_score = max(0, raw_score)
        return math.ceil(raw_score)


class CardData(MemoData):
    """Represents Card data

    Cards are represented as integers between 0 and 51.

    The suite is computes as: suite = card_int // 13, where
        suite = 0 => Spades
        suite = 1 => Hearts
        suite = 2 => Diamonds
        suite = 3 => Clubs
    The card value is computed as: value = card_int % 13, where
        value = 0 => A
        value = 1 => 2
        ...
        value = 9 => 10
        value = 10 => J, Jack
        value = 11 => Q, Queen
        value = 12 => K, King
    """
    __mapper_args__ = {
        'polymorphic_identity': Discipline.cards,
    }
    xls_table = staticmethod(recall.xls.get_card_table)

    @staticmethod
    def random(nr_items, *args):

        def get_card():
            cards = list(range(52))
            while True:
                random.shuffle(cards)
                yield from cards

        return tuple(c for c in itertools.islice(get_card(), nr_items))

    @staticmethod
    def from_text(text):
        return tuple(int(digit) for digit in text.split(',') if digit.strip())

    def raw_score(self, cbc_r):
        return self._raw_score_digits(cbc_r, 52)


class RecallData(db.Model):

    # Fields
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, nullable=False)
    ip = db.Column(db.String(40), nullable=False)
    data = db.Column(db.PickleType, nullable=False)
    time_remaining = db.Column(db.Float, nullable=False)
    locked = db.Column(db.Boolean, nullable=False)

    # ForeignKeys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    memo_id = db.Column(db.Integer, db.ForeignKey('memo_data.id'), nullable=False)

    # Relationships
    correction = db.relationship('Correction', backref='recall',
                                 cascade="save-update, merge, delete",
                                 uselist=False)

    def __init__(self, request):
        form = request.form

        self.datetime = datetime.utcnow()
        self.ip = request.remote_addr
        data = list()
        for i in range(len(form)):
            try:
                recall_cell = form[f'r_{i}'].strip()
            except KeyError:
                break
            else:
                data.append(recall_cell)
        self.data = data
        self.time_remaining = float(form['seconds_remaining'])
        self.locked = False

    @property
    def start_of_emptiness(self):
        if not hasattr(self, '_start_of_emptiness'):
            nr_items = len(self.memo.data)
            self._start_of_emptiness = 0
            for i, recall_cell in enumerate(self.data):
                if recall_cell and i < nr_items:
                    self._start_of_emptiness = i + 1
        return self._start_of_emptiness

    def _correct_cells(self):
        result = [None]*len(self.data)
        nr_items = len(self.memo.data)
        for i, user_value in enumerate(self.data, start=0):
            if i >= nr_items:
                result[i] = Item.off_limits
            else:
                if not user_value.strip():
                    # Empty cell
                    if i < self.start_of_emptiness:
                        result[i] = Item.gap
                    else:
                        result[i] = Item.not_reached
                else:
                    result[i] = self.memo.compare(user_value, i)
        return result

    def correct(self):
        cbc_r = self._correct_cells()
        raw_score = self.memo.raw_score(cbc_r[0:self.start_of_emptiness])
        points = self.memo.points(raw_score)
        return raw_score, points, cbc_r

    def __repr__(self):
        return f'<RecallData of {self.memo_id}>'


class Correction(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    off_limits = db.Column(db.Integer, nullable=False)
    gap = db.Column(db.Integer, nullable=False)
    not_reached = db.Column(db.Integer, nullable=False)
    correct = db.Column(db.Integer, nullable=False)
    wrong = db.Column(db.Integer, nullable=False)
    almost_correct = db.Column(db.Integer, nullable=False)
    consecutive = db.Column(db.Integer, nullable=False)

    raw_score = db.Column(db.Float, nullable=False)
    points = db.Column(db.Float, nullable=False)
    cell_by_cell = db.Column(db.PickleType)

    # ForeignKeys
    recall_id = db.Column(db.Integer, db.ForeignKey('recall_data.id'))

    def __init__(self, raw_score, points, cell_by_cell):
        c = collections.Counter(cell_by_cell)

        self.off_limits = c[Item.off_limits]
        self.gap = c[Item.gap]
        self.not_reached = c[Item.not_reached]
        self.correct = c[Item.correct]
        self.wrong = c[Item.wrong]
        self.almost_correct = c[Item.almost_correct]

        self.consecutive = 0
        for cell in cell_by_cell:
            if cell == Item.correct:
                self.consecutive += 1
            else:
                break

        self.raw_score = raw_score
        self.points = points
        self.cell_by_cell = cell_by_cell

    def __iter__(self):
        """Used for template access"""
        yield from (
            ('off_limits', self.off_limits),
            ('gap', self.gap),
            ('not_reached', self.not_reached),
            ('correct', self.correct),
            ('wrong', self.wrong),
            ('almost_correct', self.almost_correct),
            ('consecutive', self.consecutive),
            ('raw_score', self.raw_score),
            ('points', self.points),
            ('cell_by_cell', [i.name for i in self.cell_by_cell])
        )

    def __repr__(self):
        return (f'<Correction of recall {self.recall_id}: '
                f'points={self.points}, '
                f'raw_score{self.raw_score}, '
                f'correct={self.correct}, '
                f'consecutive={self.consecutive}>')


class Language(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(80), unique=True, nullable=False)

    # Relationships
    words = db.relationship('Word', backref="language", lazy='dynamic')
    stories = db.relationship('Story', backref="language", lazy='dynamic')
    almost_correct_words = db.relationship('AlmostCorrectWord',
                                           backref="language", lazy='dynamic')
    memos = db.relationship('MemoData', backref="language", lazy='dynamic')

    def __init__(self, language):
        self.language = language

    def __repr__(self):
        return f'<Language {self.language}>'

    @staticmethod
    def find_or_add(language):
        """Find and matching language - add first if does not exist"""
        try:
            language = Language.query.filter_by(language=language).one()
        except sqlalchemy.orm.exc.NoResultFound:
            # Add the language to the database
            language = Language(language=language)
            db.session.add(language)
            db.session.commit()
        return language


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

    def __repr__(self):
        return f'<{self.word} ~= {self.almost_correct}>'


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

    def __str__(self):
        """Used when exporting as csv"""
        return '{lang},{cls},{word}'.format(
            lang=self.language.language,
            cls=self.word_class.name,
            word=self.word
        )

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

    def __str__(self):
        """Used when exporting as csv"""
        return f'{self.language.language},{self.story}'

    def __repr__(self):
        return f'<Story "{self.story}">'
