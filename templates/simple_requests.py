import requests
import time
import warnings

warnings.filterwarnings('ignore')

session = requests.Session()
proxies = {
    'http': 'http://127.0.0.1:8080',
    'https': 'http://127.0.0.1:8080',
}
session.proxies = proxies
session.verify = False
http_requests = []

{%- for request in http_requests %}

http_requests.append({"method": "{{ request.command }}", "host": "{{ request.host }}", "path": "{{ request.path }}", "url": "https://{{ request.host }}{{ request.path }}",
"headers": {
{%- for header_name, header_value in request.headers.items() -%}
"{{header_name}}":r'''{{header_value}}''',
{%- endfor -%}
},
"cookies": {
{%- for cookie_name, cookie_value in request.cookies.items() -%}
"{{cookie_name}}":r'''{{cookie_value}}''',
{%- endfor -%}
},
"data": r'''{{ request.data or '' }}'''})

{%- endfor %}

for req in http_requests:
    prepared_req = requests.Request(method=req.get("method"),
                                    url=req.get("url"),
                                    headers=req.get("headers"),
                                    cookies=req.get("cookies"),
                                    data=req.get("data")).prepare()
    try:
        resp = session.send(prepared_req, timeout=60)
        print("status code: {}".format(resp.status_code))
        #print(resp.text)
        #print(resp.headers)
    except requests.exceptions.RequestException as e:
        print("error occured: {}".format(e))
    time.sleep(0.1)
