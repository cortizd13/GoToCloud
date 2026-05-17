import requests, json

sid = None

questions = [
    'Hola',
    'Que servicios tienen?',
    'Cuentame mas de seguridad',
    'Como los contacto?'
]

for q in questions:
    body = {'message': q}
    if sid:
        body['session_id'] = sid
    resp = requests.post('http://localhost:8000/chat/message', headers={'Content-Type': 'application/json'}, json=body, timeout=60)
    data = resp.json()
    sid = data.get('session_id')
    print('>>> ' + q)
    print('<<< ' + (data.get('reply') or 'N/A')[:300])
    print('tools: ' + str(data.get('tool_calls', [])))
    print()