import os
import errno
import json
import re
import base64
import argparse
from signal import SIG_DFL
from urllib.parse import parse_qs
from bs4 import BeautifulSoup
from sqlalchemy import false
from http_request import HTTPRequest
from requests_toolbelt.multipart import decoder
from jinja2 import Template
from colorama import init
from termcolor import colored
from termcolor import cprint


def consolidate(raw_requests, args):
    if args.debug:
        print("\n")
        print(colored("[+]Consolidating requests begins:", "cyan"))

    requests_consolidated = []

    should_exclude = False
    should_remove_duplicates = False
    should_remove_nop = False

    if args.consolidate_mode == "all":
        should_exclude = True
        should_remove_duplicates = True
        should_remove_nop = True

    if "1" in args.consolidate_mode:
        should_exclude = True

    if "2" in args.consolidate_mode:
        should_remove_duplicates = True

    if "3" in args.consolidate_mode:
        should_remove_nop = True

    for req1 in raw_requests:
        req1_parsed = HTTPRequest(req1)
        shouldDrop = False

        if args.debug:
            print("\n")
            print("================================================================================================================")
            print(colored("[+]Processing request:", "cyan"))
            print(req1)

        # Exclusions
        if should_exclude:
            exclusions = args.exclusions.split(",")
            extension = os.path.splitext(req1_parsed.parsed_url.path)[1].strip()
            if extension != "" and extension in exclusions:
                if args.debug:
                    print(colored("[*]Request path {} has unwanted extension '{}', should drop".format(req1_parsed.parsed_url.path, extension), "yellow"))
                continue

        params1 = []
        params1.extend(list(parse_qs(req1_parsed.parsed_url.query, True).keys()))

        # no request data
        if req1_parsed.data is None or req1_parsed.data.strip() == "":
            if args.debug:
                print(colored("[+]Request has no request data", "cyan"))

        # request data is application/x-www-form-urlencoded
        elif "form-urlencoded" in req1_parsed.headers["Content-Type"]:
            if args.debug:
                print(colored("[+]Content-Type is: {}".format(req1_parsed.headers["Content-Type"]), "cyan"))

            params1.extend(list(parse_qs(req1_parsed.data, True).keys()))

        # request data is application/json
        elif "json" in req1_parsed.headers["Content-Type"]:
            if args.debug:
                print(colored("[+]Content-Type is: {}".format(req1_parsed.headers["Content-Type"]), "cyan"))

            try:
                params1.extend(list(json.loads(req1_parsed.data).keys()))
            except ValueError as e:
                raise

        # request data is multipart/form-data
        elif "multipart" in req1_parsed.headers["Content-Type"]:
            if args.debug:
                print(colored("[+]Content-Type is: {}".format(req1_parsed.headers["Content-Type"]), "cyan"))

            for part in decoder.MultipartDecoder(req1_parsed.data, req1_parsed.headers["Content-Type"]).parts:
                params1.append(re.search('name="([^\s"]+)"', part.headers[b'Content-Disposition'].decode()).group(1))
        else:
            if args.debug:
                print(colored("[*]Content-Type is: {}".format(req1_parsed.headers["Content-Type"])), "yellow")

        if len(params1) == 0 and should_remove_nop:
            if args.debug:
                print(colored("[*]Request has no parameter, should drop", "yellow"))
            continue

        if args.debug:
            print(colored("[+]Found {} parameters: {}".format(len(params1), params1), "cyan"))

        if should_remove_duplicates:
            for req2 in requests_consolidated:
                req2_parsed = HTTPRequest(req2)

                if req1_parsed.command == req2_parsed.command and req1_parsed.parsed_url.path == req2_parsed.parsed_url.path:
                    if args.debug:
                        print("\n")
                        print(colored("[*]Found 1 similer request already exists:", "yellow"))
                        print(req2)

                    params2 = []
                    params2.extend(list(parse_qs(req2_parsed.parsed_url.query, True).keys()))

                    if (req1_parsed.data is None and req2_parsed.data is None) or (req1_parsed.data.strip() == "" and req2_parsed.data.strip() == ""):
                        if args.debug:
                            print(colored("[+]Request has no request data", "cyan"))

                    # request data is application/x-www-form-urlencoded
                    elif "form-urlencoded" in req1_parsed.headers["Content-Type"] and "form-urlencoded" in req2_parsed.headers["Content-Type"]:
                        if args.debug:
                            print(colored("[+]Content-Type is: {}".format(req1_parsed.headers["Content-Type"]), "cyan"))

                        params2.extend(list(parse_qs(req2_parsed.data, True).keys()))

                    # request data is application/json
                    elif "json" in req1_parsed.headers["Content-Type"] and "json" in req2_parsed.headers["Content-Type"]:
                        if args.debug:
                            print(colored("[+]Content-Type is: {}".format(req1_parsed.headers["Content-Type"]), "cyan"))

                        try:
                            params2.extend(list(json.loads(req2_parsed.data).keys()))
                        except ValueError as e:
                            raise

                    # request data is multipart/form-data
                    elif "multipart" in req1_parsed.headers["Content-Type"] and "multipart" in req2_parsed.headers["Content-Type"]:
                        if args.debug:
                            print(colored("[+]Content-Type is: {}".format(req1_parsed.headers["Content-Type"]), "cyan"))

                        for part in decoder.MultipartDecoder(req2_parsed.data, req2_parsed.headers["Content-Type"]).parts:
                            params2.append(re.search('name="([^\s"]+)"', part.headers[b'Content-Disposition'].decode()).group(1))
                    else:
                        if args.debug:
                            print(colored("[*]Content-Type is: {}".format(req2_parsed.headers["Content-Type"])), "yellow")

                    if args.debug:
                        print(colored("[+]Found {} parameters: {}".format(len(params2), params2), "cyan"))

                    if sorted(params1) == sorted(params2):
                        if args.debug:
                            print("\n")
                            cprint("[*]The two requests have same parameters, current processing request should drop", "yellow")

                        shouldDrop = True
                        break
                    elif all(item in params2 for item in params1):
                        if args.debug:
                            print("\n")
                            cprint("[*]Similerly existed request contains all parameters of current request has, should drop", "yellow")

                        shouldDrop = True
                        break
                    elif all(item in params1 for item in params2):
                        if args.debug:
                            print("\n")
                            cprint("[*]Current processing request contains all parameters of similerly existed request has, shoud replace", "yellow")
                        requests_consolidated.remove(req2)
                        requests_consolidated.append(req1)
                        shouldDrop = True
                        break

        if not shouldDrop:
            if args.debug:
                cprint("[+]Request is satisfied, should keep", "cyan")

            requests_consolidated.append(req1)

    if args.debug:
        print("================================================================================================================")
        cprint("[+]Consolidating requests ends.", "cyan")
        print("\n")

    return requests_consolidated


def main():
    # init colorama
    init()

    # Configure menu
    parser = argparse.ArgumentParser()

    parser.add_argument("-i", metavar="<input file>", dest="input_file", type=str, required=True, help="Input file containing raw HTTP requests exported from Burp Suite")

    parser.add_argument("-o", metavar="<output directory>", dest="output_dir", type=str, required=True, help="Specify output directory")

    parser.add_argument("-t", metavar="<template>", dest="template", type=str, help="Template for output. If omited, will split raw requests to files")

    parser.add_argument("--consolidate", metavar="<modes: all|1,2,3>", dest="consolidate_mode",
                        help='''Consolidate requests in following modes:
                        1: Exclude requests of specific extensions;
                        2: Remove duplicates which have same HTTP methods, paths and parameters;
                        3: Remove requests that have no parameters;
                        Feed with 'all' will do all above otherwise feed with comma seperated sequence for desired modes
                        ''')

    parser.add_argument("--exclusions", metavar="<exclusions>", dest="exclusions", default=".ico,.txt,.js,.css,.scss,.gif,.bmp,.jpg,.svg,.jpeg,.png,.tiff,.html,.pdf,.swf,.mp3,.mp4,.mkv,.avi,.mov,.exe,.flv",
                        help="This is a make-up for --consolidate which specifies what extensions of requests to exclude. If omitted, default buit-in exclusions will be applied. Default: .ico,.txt,.js,.css,.scss,.gif,.bmp,.jpg,.svg,.jpeg,.png,.tiff,.html,.pdf,.swf,.mp3,.mp4,.mkv,.avi,.mov,.exe,.flv")

    parser.add_argument("--debug", dest="debug", default=False, action="store_true", help="Run script in debug mode and print out more details")

    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')

    args = parser.parse_args()

    # Input
    if not os.path.exists(args.input_file) or not os.path.isfile(args.input_file):
        print(colored("[-] Input file: '{}' either doesn't exist or isn't a file.".format(args.input_file), "red"))
        exit(0)

    print(colored("[+] Input file: {}".format(args.input_file), "cyan"))

    # Output
    if not os.path.exists(args.output_dir) or not os.path.isdir(args.output_dir):
        print(colored("[-] Output directory: '{}' either doesn't exist or isn't a directory".format(args.output_dir), "red"))
        exit(0)

    # Template
    if not args.template:
        print(colored("[*] Template is not specified, will do requests splitting by default, output to: {}".format(args.output_dir), "yellow"))
    else:
        template_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates", args.template)

        if not os.path.exists(template_path):
            print(colored("[-] Template: '{}' doesn't exist!".format(args.template), "red"))
            exit(0)
        
        print(colored("[+] Template: {}".format(template_path), "cyan"))

        output_fie = os.path.join(args.output_dir, "code_gen{}".format(os.path.splitext(template_path)[1]))
        if os.path.exists(output_fie):
            os.remove(output_fie)

        print(colored("[+] Output file: {}".format(output_fie), "cyan"))

    with open(args.input_file) as f:
        soup = BeautifulSoup(f.read(), features="xml")
        raw_requests = soup.find_all("request")
    for i, req in enumerate(raw_requests):
        raw_requests[i] = base64.b64decode(req.text.strip()).decode('utf-8')

    print(
        colored("[+] Found {} requests in total".format(len(raw_requests)), "cyan"))

    if args.consolidate_mode:
        cprint("[*] --consolidate option is on", "yellow")
        raw_requests = consolidate(raw_requests, args)
        if len(raw_requests) == 0:
            exit(0)

    if not args.template:
        for i, raw_request in enumerate(raw_requests):
            with open(os.path.join(args.output_dir, "raw_request{}.txt".format(i)), "w") as f:
                f.write(raw_request)
        print(colored("[+] {} requests are exported to {}".format(len(raw_requests), os.path.join(args.output_dir, "raw_request*.txt")), "cyan"))
    else:
        parsed_requests = []
        for raw_request in raw_requests:
            parsed_requests.append(HTTPRequest(raw_request))

        with open(template_path) as f:
            Template(f.read()).stream(http_requests=parsed_requests).dump(output_fie)
            # print(Template(f.read()).render(http_requests=parsed_requests))

        print(colored("[+] {} requests are exported based on template to {}".format(len(raw_requests), output_fie), "cyan"))


if __name__ == "__main__":
    main()
