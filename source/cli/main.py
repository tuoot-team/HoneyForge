from colorama import Fore, Style
from dotenv import load_dotenv

from commands.auth import auth_Login
from parser import create_parser, execute_args
from texts import (
	LoginSuccessText,
	PasswordErrorText,
	WelcomeText,
	clear_Screen,
	print_Logo,
)

load_dotenv()


def run_Login() -> None:
	global is_logged
	is_logged = False
	clear_Screen()
	while not is_logged:
		enter_Password = input(Fore.GREEN + "Пароль: " + Style.RESET_ALL)
		if auth_Login(enter_Password) not in [None, ""]:
			is_logged = True
		else:
			print(Fore.RED + PasswordErrorText + Style.RESET_ALL)


def main() -> None:
	run_Login()
	clear_Screen()
	print_Logo()
	print(Fore.GREEN + LoginSuccessText + Style.RESET_ALL)
	print(Fore.YELLOW + WelcomeText + Style.RESET_ALL)

	parser = create_parser()
	while is_logged:
		try:
			input_args = input(Fore.CYAN + "\nforge" + Style.RESET_ALL + "> ")
			first = input_args.strip().split(" ")[0] if input_args.strip() else ""
			if first in ["exit", "quit"]:
				print(Fore.RED + "Выход..." + Style.RESET_ALL)
				break
			execute_args(parser, input_args)
		except SystemExit:
			continue
		except KeyboardInterrupt:
			print()
			continue


if __name__ == "__main__":
	main()
