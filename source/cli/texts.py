import os

from colorama import *

def print_Logo():
    print(Fore.MAGENTA + r"""
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠰⣾⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⣴⡏⠀⠀⢀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿⣿⣷⣄⠀⠀⠀⠀⢀⣼⣿⣁⣤⡶⠁⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⢀⣀⣤⣶⣿⣿⣿⣿⣿⡄⠀⢠⣷⣾⣿⣿⣿⣿⣁⣀⡀⠀⠀
⠀⠀⠀⢀⣠⣴⣾⡿⠟⠋⠉⠀⠈⢿⣿⣿⠷⠀⣾⠿⠛⣿⣿⠿⠛⠋⠁⠀⠀⠀
⠀⢲⣿⡿⠟⠋⠁⠀⠀⠀⠀⢀⣀⣈⣁⣀⣀⣀⣀⣀⣀⣁⣀⣀⣀⡀⠀⠀⠀⠀
⠀⠈⠁⠀⠀⠀⢠⣤⣤⣤⣤⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣇⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠙⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⠄⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠋⠁⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⠛⠛⢛⣿⣿⣿⣿⣿⣿⡟⠛⠛⠛⠃⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⣿⣿⣿⣿⣿⣿⣿⣆⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣄⣀⡀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠉⠁⠀⠀⠀
    """ + Style.RESET_ALL)

def clear_Screen():
    os.system('cls' if os.name == 'nt' else 'clear')

PasswordErrorText = "Incorrect password. Please try again."

LoginSuccessText = "Login successful! Welcome to HoneyForge."

WelcomeText = "Type 'help' for available commands."

HelpText = """Available commands:
help - Show this help message
clear - Clear the screen
exit, quit - Exit the program"""

HelpHelpText = """
Usage: help [topic]
"""

HelpClearText = """
Usage: clear - Clear the screen
"""

HelpExitText = """
Usage: exit, quit - Exit the program
"""