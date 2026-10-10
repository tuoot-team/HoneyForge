# CLI

**Ответственный:** @potjoke  
**Стек:** Python, httpx, argparse REPL

## Запуск

```powershell
cd source/cli
copy .env.example .env
python -m pip install -r requirements.txt
# рядом должен быть поднят core-api
python main.py
```

## Команды

См. `help` внутри REPL: profiles, pair-confirm, traps, events-list / events-tail.

Пример профиля (`profile.json`):

```json
{
  "name": "mid-ssh",
  "description": "demo",
  "interaction_level": "medium",
  "blocks": {
    "services": [{"name": "ssh", "port": 22}],
    "mask": {"jitter_pct": 30}
  }
}
```

```
forge> profile-create --file profile.json
forge> pair-confirm ABC123 --profile-id <uuid>
forge> events-tail
```
