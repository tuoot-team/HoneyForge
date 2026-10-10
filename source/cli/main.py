from texts import *
from commands.auth import *
from client import *
from parser import *

from colorama import *
from dotenv import load_dotenv

import shlex

load_dotenv()

def login():
    global is_logged
    is_logged = False

    clear_Screen()

    while not is_logged:
        enter_Password = input(Fore.GREEN + "Enter password: " + Style.RESET_ALL)
        if auth_Login(enter_Password) not in [None, ""]:
            is_logged = True
        else:
            print(Fore.RED + PasswordErrorText + Style.RESET_ALL)

def __main__():
    login()

    clear_Screen()
    print_Logo()
    print(Fore.GREEN + LoginSuccessText + Style.RESET_ALL)
    print(Fore.YELLOW + WelcomeText + Style.RESET_ALL)

    while is_logged:
        try:
            parser = create_parser()

            input_args = input(Fore.CYAN + "\nforge" + Style.RESET_ALL + "> ")

            if input_args.split(" ")[0] in ["exit", "quit"]:
                print(Fore.RED + "Exiting..." + Style.RESET_ALL)
                break        
            
            execute_args(parser, input_args)

        except SystemExit:
            continue


__main__()