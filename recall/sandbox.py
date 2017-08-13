import os

if os.path.isfile('test.db'):
    os.remove('test.db')

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

for i in range(33):

    m = MemoData(
        ip='.'.join(str(random.randint(0,99)) for _ in range(4)),
        user_id=u1.id,
        key=str(10000 + i),
        discipline=random.choice(list(Discipline)),
        memo_time=5,
        recall_time=15,
        language=random.choice(['swedish', 'english']),
        data=[1,2,3],
        generated=True
    )
    k = KeyState(m.key)

    d = XlsDoc(m.key, '2,1', b'asdfkjadfasdf')

    r = RecallData('123.231.43.5', u1.id, m.key,
                 [4, 6, 2], 12.543)

    db.session.add(m)
    db.session.add(k)
    db.session.add(d)
    db.session.add(r)

w = Word('123.231.43.5', u1.id, 'caffe',
          WordClass.abstract_noun, l1.id)

db.session.add(w)
db.session.commit()

def disp():
    print('All Users:     ', User.query.all())
    print('All MemoData:  ', MemoData.query.all())
    print('All XlsDoc:    ', XlsDoc.query.all())
    print('All RecallData:', RecallData.query.all())

    print('All Langs:     ', Language.query.all())
    print('All Words:     ', Word.query.all())
    print()
    print('Users data:')
    for user in User.query.all():
        print(user.username, user.memos, user.recalls)

    print('-----------------')
    print

disp()