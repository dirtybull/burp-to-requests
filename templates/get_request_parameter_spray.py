import os
import requests
import time
import warnings
from bs4 import BeautifulSoup
from random import randint
from termcolor import colored
from termcolor import cprint
from urllib.parse import urlparse
from urllib.parse import parse_qs

warnings.filterwarnings('ignore')

###########################
## For GET requests only ##
###########################
parameter_file_path="~/BugBounties/WorkSpace/Targets/?/params.txt"

if not os.path.exists(parameter_file_path) or not os.path.isfile(parameter_file_path):
    cprint("{} either doesn't exist or isn't a file".format(parameter_file_path),"red")
    exit(0)

session = requests.Session()
proxies = {
    'http': 'http://127.0.0.1:8080',
    'https': 'http://127.0.0.1:8080',
}
session.proxies = proxies
session.verify = False
timeout = 60
http_requests = []

{%- for request in http_requests %}
{%- if request.command == "GET" %}

http_requests.append({"method": "{{ request.command }}", "host": "{{ request.host }}", "path": "{{ request.path }}", "url": "https://{{ request.host }}{{ request.path }}",
"headers": {
{%- for header_name, header_value in request.headers.items() -%}
"{{header_name}}": r'''{{header_value}}''',
{%- endfor -%}
},
"cookies": {
{%- for cookie_name, cookie_value in request.cookies.items() -%}
"{{cookie_name}}": r'''{{cookie_value}}''',
{%- endfor -%}
}})
{%- endif %}
{%- endfor %}

cprint("[+] Start fetching, it takes time ... ...\n", "cyan")

for req in http_requests:
    url = req.get("url").strip()
    url_parsed = urlparse(url)
    parameters_original = list(parse_qs(url_parsed.query, True).keys())
    basename = os.path.basename(url_parsed.path).lower()

    if "logout" in basename or "log-out" in basename or "log_out" in basename:
        cprint("[*] It seems {} is for logging out, skip\n".format(url), "yellow")
        continue

    print("{}{}".format(colored("[+] Fetching on:      ", "cyan"), url))

    try:
        resp = session.get(url, headers=req.get("headers"), cookies=req.get("cookies"), timeout=timeout)
        res_code = str(resp.status_code)
        res_length = len(resp.content)

        print("{}{} {}{}".format(colored("[+] Status Code: ", "cyan"), res_code, colored("Content Length: ", "cyan"), res_length))

        time.sleep(0.1)

    except requests.exceptions.RequestException as e:
        print("error occured: {}".format(e))
        continue

    if res_code.startswith("20"):
        url_origin = url
        with open(parameter_file_path) as f:
            parameters = f.read().splitlines()

        inputs = BeautifulSoup(resp.text, "html.parser").find_all("input")
        if len(inputs) > 0:
            parameters_input=[]
            cprint("[+] Found {} inputs: ".format(len(inputs)), "cyan")

            for input in inputs:
                print("    {}".format(input))
                if input.get("id") is not None and input.get("id") not in parameters:
                    parameters_input.append(input.get("id"))
                if input.get("name") is not None and input.get("name") not in parameters:
                    parameters_input.append(input.get("name"))

            print("{}{}".format(colored("[+] Parsed to parameters: ", "cyan"), parameters_input))
            parameters.extend(parameters_input)

        #Remove duplicated parameters
        parameters = sorted(parameters)
        for p in parameters_original:
            if p in parameters:
                parameters.remove(p)

        # Append a random parameter
        parameters.append("xrandom")

        # Append parameters to the url
        for p in parameters:
            if "?" not in url:
                url = "{}?{}={}".format(url, p, randint(1000, 9999))
            else:
                url = "{}&{}={}".format(url, p, randint(1000, 9999))

        if url_origin != url:
            print("{}{}".format(colored("[+] Redo fetching on: ", "cyan"), url))

            try:
                resp2 = session.get(url, headers=req.get("headers"), cookies=req.get("cookies"), timeout=timeout)
                res_code2 = str(resp2.status_code)
                res_length2 = len(resp2.content)

                print("{}{} {}{}".format(colored("[+] Status Code: ", "cyan"), res_code2, colored("Content Length: ", "cyan"), res_length2))

                time.sleep(0.1)

            except requests.exceptions.RequestException as e:
                print("error occured: {}".format(e))
                continue

            if res_code != res_code2 or res_length != res_length2:
                cprint("[*] Attention! Found request either has different status code or different content in response when appending parameters:", "yellow")
                print("  Origin request:             {}".format(url_origin))
                print("    status code: {}, content-length: {}\n".format(res_code, res_length))
                print("  Parameter-appended request: {}".format(url))
                print("    status code: {}, content-length: {}\n".format(res_code2, res_length2))

    print("----------------------------------------------------------------------------------------------------------------------\n")

cprint("[+] Fetching finished.", "cyan")
