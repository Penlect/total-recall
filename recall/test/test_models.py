import os

if os.path.isfile('../test.db'):
    os.remove('../test.db')

from recall import db
from recall.models import *
import random

db.create_all()

u1 = User('penlect', 'asdf', 'DanielA', 'Swe')
u2 = User('daniel', 'afdgf', 'James', 'Den')
l1 = Language('swedish')
l2 = Language('english')
db.session.add(u1)
db.session.add(u2)
db.session.add(l1)
db.session.add(l2)
db.session.commit()

def rand_ip():
    return '.'.join(str(random.randint(0,99)) for _ in range(4))

def rand_disip():
    return random.choice(list(Discipline))

def rand_lang():
    return random.choice(['swedish', 'english'])

def rand_time(discipline):
    if discipline == Discipline.base2:
        return random.choice([(5, 15), (30, 60)])
    elif discipline == Discipline.base10:
        return random.choice([(5, 15), (15, 30), (30, 60), (60, 120)])
    elif discipline == Discipline.words:
        return random.choice([(5, 15), (15, 30)])
    elif discipline == Discipline.dates:
        return (5, 15)
    else:
        raise ValueError('Unknown discipline: ' + discipline)


def rand_data(discipline):
    if discipline == Discipline.base2:
        return tuple(random.randint(0, 1) for _ in range(370))
    elif discipline == Discipline.base10:
        return tuple(random.randint(0, 9) for _ in range(200))
    elif discipline == Discipline.words:
        return ['bacon', 'häst', 'pizza', 'python']
    elif discipline == Discipline.dates:
        stories = ['Kung ramlar ner', 'OS förbjuds']
        dates = [random.randint(1000, 2099) for _ in stories]
        return tuple(zip(dates, stories))
    else:
        raise ValueError('Unknown discipline: ' + discipline)


def rand_memo(user):
    d = rand_disip()
    mt, rt = rand_time(d)
    data = rand_data(d)
    m = MemoData(
        ip=rand_ip(),
        discipline=rand_disip(),
        memo_time=mt,
        recall_time=rt,
        language=rand_lang(),
        data=data,
        generated=True
    )
    m.user = user
    return m

def rand_recall(user, memo):
    r = RecallData(
        ip=rand_ip(),
        data=rand_data(memo.discipline),
        time_remaining=12.543*random.random()
    )
    r.user = user
    r.memo = memo
    return r


for i in range(4):

    m1 = rand_memo(u1)
    m2 = rand_memo(u2)
    db.session.add(m1)
    db.session.add(m2)

    d = XlsDoc(pattern='2,1', data=b'asdfkjadfasdf')
    d.memo = m1
    db.session.add(d)

    r1 = rand_recall(u1, m1)
    r2 = rand_recall(u2, m2)
    db.session.add(r1)
    db.session.add(r2)

    if i%2 == 0:
        r1 = rand_recall(u1, m2)
    else:
        r2 = rand_recall(u2, m1)
    db.session.add(r1)
    db.session.add(r2)
db.session.commit()

# w = Word('123.231.43.5', u1.id, 'caffe')
# db.session.add(w)
# db.session.commit()

def disp():
    print('All Users:     ', User.query.all())
    print('All MemoData:  ', MemoData.query.all())
    print('All XlsDoc:    ', XlsDoc.query.all())
    print('All RecallData:', RecallData.query.all())

    #print('All Langs:     ', Language.query.all())
    #print('All Words:     ', Word.query.all())
    #print()
    print('Users data:')
    for user in User.query.all():
        print('User: ', user.username)
        for m in user.memos.all():
            print('memos:   ', m)
        for r in user.recalls.all():
            print('recalls: ', r)
        print()

    print('-----------------')

disp()

#print(RecallData.query.join(RecallData.memo).filter(MemoData.user_id==1).all())