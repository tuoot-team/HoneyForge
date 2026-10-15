from __future__ import annotations

import random

from colorama import Fore, Style

import client
from texts import CatArts, CatMeowLines, CatUwuLines


def maybe_Meow() -> None:
	if not client.is_CatMode():
		return
	if random.randrange(4) != 0:
		return
	# Котики и nya выпадают чаще, чем короткий uwu.
	roll = random.randrange(10)
	if roll < 5:
		line = random.choice(CatArts)
	elif roll < 9:
		line = random.choice(CatMeowLines)
	else:
		line = random.choice(CatUwuLines)
	print(Fore.MAGENTA + line + Style.RESET_ALL)
