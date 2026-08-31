import json
with open('jis32.json','r', encoding='utf-8') as f:
    data = json.load(f)
print('total objects in file=', len(data))
for i,e in enumerate(data,1):
    print(i, e.get('id'), e.get('char'))
