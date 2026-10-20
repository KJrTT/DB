"""Снимает план выполнения запроса и кладёт его в файл JSON.

Запрос задаётся здесь, в файле, а не в командной строке. Поэтому кавычки,
фигурные скобки и знак $ нигде не проходят через оболочку — команда запуска
одинаково работает в PowerShell, cmd.exe, Терминале macOS и Linux.

    docker compose run --rm python work/praktikum-explain/plan.py
    docker compose run --rm python work/praktikum-explain/plan.py plan-2.json

Имя файла можно задать одним словом в конце команды — кавычек ему не нужно.
Без него берётся FAYL из блока ниже.

Индексы скрипт не создаёт и не удаляет: он снимает план того состояния
коллекции, которое вы сделали в оболочке или в Compass.
"""

from pymongo import MongoClient

BAZA = "logs"
KOLLEKCIYA = "events"

# Фильтр — тот же документ, что вы пишете в find({...}).
FILTR = {
    "level": "error"
}

# Сортировка: поле и направление. 1 — по возрастанию, -1 — по убыванию.
SORTIROVKA = [("duration_ms", -1)]

# Сколько документов вернуть. 0 — все.
PREDEL = 10

# Куда положить план. Файл ложится рядом с этим скриптом.
FAYL = "plan-1.json"

# ─────────────────────────────────────────────────────────────────────────
#  Дальше менять ничего не нужно.
# ─────────────────────────────────────────────────────────────────────────

import json
import sys
from pathlib import Path

from bson.json_util import RELAXED_JSON_OPTIONS, dumps


def oshibka(tekst):
    print(tekst, file=sys.stderr)
    sys.exit(2)


def shagi_plana(stadiya):
    """Имена шагов снизу вверх: так же, как их рисует визуализатор."""
    imena = []
    while stadiya:
        imena.append(stadiya["stage"])
        stadiya = stadiya.get("inputStage")
    return list(reversed(imena))


def main():
    imya = sys.argv[1] if len(sys.argv) > 1 else FAYL
    if not imya.endswith(".json"):
        oshibka("Имя файла должно оканчиваться на .json, например plan-2.json")

    # Раннер подключён к сети сервера: адрес тот же, что и на компьютере.
    client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except Exception:
        oshibka(
            "Сервер не отвечает. Поднимите стенд:  docker compose up -d\n"
            "и залейте данные:                     docker compose run --rm reset"
        )

    kollekciya = client[BAZA][KOLLEKCIYA]
    vsego = kollekciya.count_documents({})
    if vsego == 0:
        oshibka("Коллекция %s.%s пуста. Данные: docker compose run --rm reset"
                % (BAZA, KOLLEKCIYA))

    kursor = kollekciya.find(FILTR)
    if SORTIROVKA:
        kursor = kursor.sort(SORTIROVKA)
    if PREDEL:
        kursor = kursor.limit(PREDEL)

    plan = kursor.explain()
    stats = plan["executionStats"]

    # Файл кладём рядом со скриптом: студент запускает его из своей папки work.
    fayl = Path(__file__).resolve().parent / imya
    # dumps из bson пишет даты и числа BSON так, как их ждёт визуализатор.
    fayl.write_text(dumps(plan, json_options=RELAXED_JSON_OPTIONS), encoding="utf-8")

    print("Запрос к %s.%s, всего документов в коллекции: %d" % (BAZA, KOLLEKCIYA, vsego))
    print("  фильтр:                %s" % json.dumps(FILTR, ensure_ascii=False))
    print("  сортировка:            %s" % (SORTIROVKA or "нет"))
    print("  предел:                %s" % (PREDEL or "нет"))
    print()
    print("  файл с планом:         %s" % fayl.name)
    print("  возвращено:            %d" % stats["nReturned"])
    print("  документов просмотрено:%d" % stats["totalDocsExamined"])
    print("  ключей просмотрено:    %d" % stats["totalKeysExamined"])
    print("  шаги плана:            %s" % " → ".join(shagi_plana(stats["executionStages"])))
    print("  индексы коллекции:     %s"
          % ", ".join(i["name"] for i in kollekciya.list_indexes()))


if __name__ == "__main__":
    main()