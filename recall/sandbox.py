import os
#os.remove('test.db')

from recall import db
from recall.models import User, Language, MemoData, XlsDoc, KeyStatus, RecallData, Word, WordClass, Discipline


print(os.getcwd())
db.create_all()

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
             'swedish', '1,4,5', [1,2,3],
             False)
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

print('-----------------')

db.session.delete(u1)
db.session.commit()