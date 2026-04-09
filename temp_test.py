from app import app
from data.locations import US_LOCATIONS

with app.test_client() as client:
    with client.session_transaction() as sess:
        sess.clear()
    state = 'Arizona'
    city_data = US_LOCATIONS[state]['cities'][0]
    res1 = client.post('/api/generate', json={'state': state, 'city_data': city_data})
    print('gen1', res1.status_code, res1.get_json())
    with client.session_transaction() as sess:
        print('session1', sess.get('generated_pages'))
    fn1 = res1.get_json().get('filename')
    resprev1 = client.get(f'/preview/{fn1}')
    print('preview1', resprev1.status_code)

    city_data2 = US_LOCATIONS[state]['cities'][1]
    res2 = client.post('/api/generate', json={'state': state, 'city_data': city_data2})
    print('gen2', res2.status_code, res2.get_json())
    with client.session_transaction() as sess:
        print('session2', sess.get('generated_pages'))
    fn2 = res2.get_json().get('filename')
    resprev2 = client.get(f'/preview/{fn2}')
    print('preview2', resprev2.status_code)
