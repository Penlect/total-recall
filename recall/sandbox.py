import os
os.remove('test.db')

from recall import db
from recall.models import User, Language, MemoData, XlsDoc, KeyStatus, RecallData, Word, WordClass, Discipline


print(os.getcwd())
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

m = MemoData('123.231.43.5', u1.id, 'abc123',
             Discipline.base2, 5, 15,
             'swedish', '1,4,5', [1,2,3],
             False)
m2 = MemoData('44.66.4773.5', u1.id, '454fds',
             Discipline.base2, 5, 15,
             'swedish', '1,4,5', [1,2,3],
             False)
k = KeyStatus(m.key, True)
k2 = KeyStatus(m2.key, True)

d = XlsDoc(m.key, b'asdfkjadfasdf')
d2 = XlsDoc(m2.key, b'asdfkjadfasdf')

r = RecallData('123.231.43.5', u1.id, m.key,
             [4, 6, 2], 34.543)

r2 = RecallData('123.231.43.5', u1.id, m2.key,
             [4, 6, 2], 34.543)

r3 = RecallData('123.6.43.5', u1.id, m2.key,
             [4, 6, 2], 314.543)

w = Word('123.231.43.5', u1.id, 'caffe',
          WordClass.abstract_noun, l1.id)

db.session.add(m)
db.session.add(k)
db.session.add(d)
db.session.add(m2)
db.session.add(k2)
db.session.add(d2)
db.session.add(r)
db.session.add(r2)
db.session.add(r3)
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
db.session.delete(m2)
db.session.commit()
disp()