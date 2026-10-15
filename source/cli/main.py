from colorama import Fore, Style, init as init_Colorama
from dotenv import load_dotenv

from cat_mode import maybe_Meow
from commands.auth import auth_Login
from line_input import read_Line
from parser import create_parser, execute_args
from texts import (
	CoreApiErrorText,
	LoginPasswordPrompt,
	LoginSuccessText,
	LoginUsernamePrompt,
	PasswordErrorText,
	WelcomeText,
	clear_Screen,
	print_Logo,
)
from client import *

init_Colorama()
load_dotenv()


def run_Login() -> None:
	global is_logged
	is_logged = False
	username_history = []
	clear_Screen()
	while not is_logged:
		enter_Username = read_Line(
			Fore.GREEN + LoginUsernamePrompt + Style.RESET_ALL,
			history=username_history,
		).strip()
		if enter_Username and (not username_history or username_history[-1] != enter_Username):
			username_history.append(enter_Username)
		enter_Password = read_Line(
			Fore.GREEN + LoginPasswordPrompt + Style.RESET_ALL,
			echo=False,
		)
		if enter_Username and auth_Login(enter_Username, enter_Password) not in [None, ""]:
			is_logged = True
		else:
			print(Fore.RED + PasswordErrorText + Style.RESET_ALL)
			maybe_Meow()

def main() -> None:
	print("HoneyForge CLI v0.1.0")
	print("Проверка подключения к CoreAPI...")

	try:
		if get_Health().get("status") == "ok": pass
	except Exception:
		print(Fore.RED + CoreApiErrorText + Style.RESET_ALL)
		maybe_Meow()
		return
	
	run_Login()
	clear_Screen()
	print_Logo()
	print(Fore.GREEN + LoginSuccessText + Style.RESET_ALL)
	print(Fore.YELLOW + WelcomeText + Style.RESET_ALL)
	maybe_Meow()

	parser = create_parser()
	command_history = []
	while is_logged:
		try:
			print()
			input_args = read_Line(
				Fore.CYAN + "forge" + Style.RESET_ALL + "> ",
				history=command_history,
			)
			stripped = input_args.strip()
			first = stripped.split(" ")[0] if stripped else ""
			if stripped and first not in ("exit", "quit"):
				if not command_history or command_history[-1] != stripped:
					command_history.append(stripped)
			if first in ["exit", "quit"]:
				print(Fore.RED + "Выход..." + Style.RESET_ALL)
				maybe_Meow()
				break
			execute_args(parser, input_args)
		except SystemExit:
			continue
		except KeyboardInterrupt:
			print()
			continue


if __name__ == "__main__":
	main()
