import argparse
import shlex

from texts import *

def tester(args):
    print("IP: " + args.ip)
    print("Port: " + str(args.port))

def create_parser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_test = subparsers.add_parser("test")
    parser_test.add_argument("--ip", type=str, required=True, help="IP address to test")
    parser_test.add_argument("--port", type=int, default=8888, help="Port to test")
    parser_test.set_defaults(func=tester)

    parser_help = subparsers.add_parser("help")
    parser_help.set_defaults(func=lambda args: print(HelpText))

    parser_clear = subparsers.add_parser("clear")
    parser_clear.set_defaults(func=lambda args: clear_Screen())

    return parser

def execute_args(parser,input_args):
    args_list = shlex.split(input_args)
            
    parsed_args = parser.parse_args(args_list)
    parsed_args.func(parsed_args)