from distutils.log import debug
import optparse
import os
import errno
import json
import re
import base64
from turtle import clear
from urllib.parse import parse_qs
from pickle import TRUE
from bs4 import BeautifulSoup
from http_request import HTTPRequest
from requests_toolbelt.multipart import decoder
from jinja2 import Template
from colorama import init
from termcolor import colored


def consolidate(requests_raw, extensions, debug):
    requests_consolidated = []
    if debug:
        print("\n")
        print(colored("[+]Consolidating requests begins:", "cyan"))

    for req_raw in requests_raw:
        req_raw_parsed = HTTPRequest(req_raw)
        shouldDrop = False

        if debug:
            print("\n")
            print("================================================================================================================")
            print(colored("[+]Processing request:", "cyan"))
            print(req_raw)

        extension = os.path.splitext(req_raw_parsed.parsed_url.path)[1]
        if extension != "" and extension in extensions:
            if debug:
                print(colored("[*]Request has unwanted extension '{}', should drop".format(extension), "yellow"))
            continue

        params_cur = []
        params_cur.extend(list(parse_qs(req_raw_parsed.parsed_url.query, True).keys()))

        # no request data
        if req_raw_parsed.data is None or req_raw_parsed.data.strip() == "":
            if debug:
                print(colored("[+]Request has no request data", "cyan"))

        # request data is application/x-www-form-urlencoded
        elif "form-urlencoded" in req_raw_parsed.headers["Content-Type"]:
            if debug:
                print(colored("[+]Content-Type is: {}".format(req_raw_parsed.headers["Content-Type"]), "cyan"))

            params_cur.extend(list(parse_qs(req_raw_parsed.data, True).keys()))

        # request data is application/json
        elif "json" in req_raw_parsed.headers["Content-Type"]:
            if debug:
                print(colored("[+]Content-Type is: {}".format(req_raw_parsed.headers["Content-Type"]), "cyan"))

            try:
                params_cur.extend(list(json.loads(req_raw_parsed.data).keys()))
            except ValueError as e:
                raise

        # request data is multipart/form-data
        elif "multipart" in req_raw_parsed.headers["Content-Type"]:
            if debug:
                print(colored("[+]Content-Type is: {}".format(req_raw_parsed.headers["Content-Type"]), "cyan"))

            for part in decoder.MultipartDecoder(req_raw_parsed.data, req_raw_parsed.headers["Content-Type"]).parts:
                params_cur.append(re.search('name="([^\s"]+)"', part.headers[b'Content-Disposition'].decode()).group(1))
        else:
            if debug:
                print(colored("[*]Content-Type is: {}".format(req_raw_parsed.headers["Content-Type"])), "yellow")

        if len(params_cur) == 0:
            if debug:
                print(colored("[*]Request has no parameter, should drop", "yellow"))
            continue

        if debug:
            print(colored("[+]Found {} parameters: {}".format(len(params_cur), params_cur), "cyan"))

        for req_con in requests_consolidated:
            req_con_parsed = HTTPRequest(req_con)

            if req_raw_parsed.command == req_con_parsed.command and req_raw_parsed.parsed_url.path == req_con_parsed.parsed_url.path:
                if debug:
                    print("\n")
                    print(colored("[*]Found 1 similer request already exists:", "yellow"))
                    print(req_con)

                params_con = []
                params_con.extend(list(parse_qs(req_con_parsed.parsed_url.query, True).keys()))

                if (req_raw_parsed.data is None and req_con_parsed.data is None) or (req_raw_parsed.data.strip() == "" and req_con_parsed.data.strip() == ""):
                    if debug:
                        print(colored("[+]Request has no request data", "cyan"))

                # request data is application/x-www-form-urlencoded
                elif "form-urlencoded" in req_raw_parsed.headers["Content-Type"] and "form-urlencoded" in req_con_parsed.headers["Content-Type"]:
                    if debug:
                        print(colored("[+]Content-Type is: {}".format(req_raw_parsed.headers["Content-Type"]), "cyan"))

                    params_con.extend(list(parse_qs(req_con_parsed.data, True).keys()))

                # request data is application/json
                elif "json" in req_raw_parsed.headers["Content-Type"] and "json" in req_con_parsed.headers["Content-Type"]:
                    if debug:
                        print(colored("[+]Content-Type is: {}".format(req_raw_parsed.headers["Content-Type"]), "cyan"))

                    try:
                        params_con.extend(list(json.loads(req_con_parsed.data).keys()))
                    except ValueError as e:
                        raise

                # request data is multipart/form-data
                elif "multipart" in req_raw_parsed.headers["Content-Type"] and "multipart" in req_con_parsed.headers["Content-Type"]:
                    if debug:
                        print(colored("[+]Content-Type is: {}".format(req_raw_parsed.headers["Content-Type"]), "cyan"))

                    for part in decoder.MultipartDecoder(req_con_parsed.data, req_con_parsed.headers["Content-Type"]).parts:
                        params_con.append(re.search('name="([^\s"]+)"', part.headers[b'Content-Disposition'].decode()).group(1))
                else:
                    if debug:
                        print(colored("[*]Content-Type is: {}".format(req_con_parsed.headers["Content-Type"])), "yellow")

                if debug:
                    print(colored("[+]Found {} parameters: {}".format(len(params_con), params_con), "cyan"))

                if sorted(params_cur) == sorted(params_con):
                    if debug:
                        print("\n")
                        print(colored("[*]The two requests have same parameters, current processing request should drop", "yellow"))

                    shouldDrop = True
                    break
                elif all(item in params_con for item in params_cur):
                    if debug:
                        print("\n")
                        print(colored("[*]Similerly existed request contains all parameters of current request has, should drop", "yellow"))

                    shouldDrop = True
                    break
                elif all(item in params_cur for item in params_con):
                    if debug:
                        print("\n")
                        print(colored("[*]Current processing request contains all parameters of similerly existed request has, shoud replace", "yellow"))
                    requests_consolidated.remove(req_con)
                    requests_consolidated.append(req_raw)
                    shouldDrop = True
                    break

        if not shouldDrop:
            if debug:
                print(colored("[+]Request is satisfied, should keep", "cyan"))

            requests_consolidated.append(req_raw)

    if debug:
        print("================================================================================================================")
        print(colored("[+]Consolidating requests ends.", "cyan"))
        print("\n")

    return requests_consolidated


def main():
    # init colorama
    init()

    # Configure menu
    parser = optparse.OptionParser(
        "usage: %prog -i <burp_file> -o <output_dir> [-t <template>] [-c] [-ex <extensions>] [--debug]")

    parser.add_option("-i", "--input", dest="input_file", type="string", help="Specify input file containing raw HTTP requests exported from Burp Suite")

    parser.add_option("-o", "--output-dir", dest="output_dir", type="string", help="Specify output directory")

    parser.add_option("-t", "--template", dest="template", type="string", help="Specify template for output. If omited, will split raw requests to files")

    parser.add_option("-c", "--consolidate", dest="shouldConsolidate", default=False, action="store_true",
                      help="Determin if remove duplicate requests that have same paths and paramters, no parameters and specified extensions")

    parser.add_option("-e", "--extension", dest="extensions", default=".txt,.js,.css,.scss,.gif,.bmp,.jpg,.svg,.jpeg,.png,.tiff,.html,.pdf,.swf,.mp3,.mp4,.mkv,.avi,.mov,.exe,.flv",
                      help="Specify extensions of requests to remove. Default: .txt,.js,.css,.scss,.gif,.bmp,.jpg,.svg,.jpeg,.png,.tiff,.html,.pdf,.swf,.mp3,.mp4,.mkv,.avi,.mov,.exe,.flv")

    parser.add_option("-d", "--debug", dest="debug", default=False, action="store_true", help="Run script in debug mode and print out more details")

    (options, _) = parser.parse_args()

    # Input
    if not options.input_file:
        parser.print_help()
        exit(0)
    elif not os.path.isfile(options.input_file):
        print(
            colored("[-] Input option: '{}' is not a file".format(options.input_file), "red"))
        exit(0)
    elif not os.path.exists(options.input_file):
        print(
            colored("[-] Input file: '{}' doesn't exist".format(options.input_file), "red"))
        exit(0)

    print(colored("[+] Input file: {}".format(options.input_file), "cyan"))

    # Output
    if not options.output_dir:
        parser.print_help()
        exit(0)
    elif not os.path.isdir(options.output_dir):
        print(
            colored("[-] Output option: '{}' is not a directory".format(options.output_dir), "red"))
        exit(0)
    elif not os.path.exists(options.output_dir):
        print(
            colored("[*] Output directory: '{}' doesn't exist and will try to create it".format(options.output_dir), "yellow"))
        try:
            os.makedirs(options.output_dir)
        except OSError as e:  # Guard against race condition
            if e.errno != errno.EEXIST:
                raise

    # Template & output_file
    if not options.template:
        print(colored("[*] Template is not specified, will do requests splitting by default, output to: {}".format(options.output_dir), "yellow"))
    else:
        if not os.path.exists(os.path.join(os.getcwd(), "templates", options.template)):
            print(colored("[-] Template: '{}' doesn't exist!".format(options.template), "red"))
            exit(0)            
        template_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates", options.template)
        print(colored("[+] Template: {}".format(template_path), "cyan"))

        gen_extension = ""
        if "python" in options.template:
            gen_extension = ".py"
        elif "php" in options.template:
            gen_extension = ".php"
        elif "bash" in options.template:
            gen_extension = ".sh"
        elif "nodejs" in options.template:
            gen_extension = ".js"
        output_fie = os.path.join(options.output_dir, "code_gen{}".format(gen_extension))
        if os.path.exists(output_fie):
            os.remove(output_fie)
        print(colored("[+] Output file: {}".format(output_fie), "cyan"))

    with open(options.input_file, "r") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
        raw_requests = soup.find_all("request")
    for i, req in enumerate(raw_requests):
        raw_requests[i] = base64.b64decode(req.text.strip()).decode('utf-8')

    print(
        colored("[+] Found {} requests in total".format(len(raw_requests)), "cyan"))

    if options.shouldConsolidate:
        print(colored("[*] --consolidate option is on".format(len(raw_requests)), "yellow"))
        raw_requests = consolidate(raw_requests, options.extensions, options.debug)
        print(colored("[*] Number of requests are consolidated to {}".format(len(raw_requests)), "yellow"))
        if len(raw_requests)==0:
            exit(0)

    if not options.template:
        for i, raw_request in enumerate(raw_requests):
            with open(os.path.join(options.output_dir, "raw_request{}.txt".format(i)), "w") as f:
                f.write(raw_request)
        print(colored("[+] Requests are exported to {}".format(os.path.join(options.output_dir, "raw_request*.txt")), "cyan"))
    else:
        parsed_requests=[]
        for raw_request in raw_requests:
            parsed_requests.append(HTTPRequest(raw_request))

        with open(template_path) as f:
            Template(f.read()).stream(http_requests=parsed_requests).dump(output_fie)
            #print(Template(f.read()).render(http_requests=parsed_requests))

        print(colored("[+] Code is generated to {}".format(output_fie), "cyan"))


if __name__ == "__main__":
    main()
