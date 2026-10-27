"""Обновляет данные сайта из API-Football: расписание, счёт, таблицу, встречи и составы.

Запуск: API_FOOTBALL_KEY=ключ python scripts/update_matches.py [full|hourly]
  full    раз в сутки: расписание на 14 дней, вчерашний день и таблицы лиг
  hourly  раз в час: счёт идущих матчей, потом встречи и составы ближайших игр
Суточный лимит бесплатного тарифа 100 запросов. Скрипт считает запросы и останавливается заранее.
Если API ответил ошибкой, файлы не меняются.
"""
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda n: os.path.join(ROOT, "data", n)
OUT, MANUAL, STATE = D("matches.js"), D("manual.json"), D("state.json")
DETAILS_JS, DETAILS, TEAMS, USAGE = D("details.js"), D("details.json"), D("teams.json"), D("usage.json")
BASE = "https://v3.football.api-sports.io"
DAYS_AHEAD, DAYS_BACK = 14, 1
CAP = 92            # максимум запросов в сутки (лимит тарифа 100)
DETAIL_RUN_CAP = 8  # максимум запросов за один часовой запуск на встречи и составы
STANDINGS = {235: "rpl", 39: "apl", 140: "ll", 135: "sa", 78: "bl", 61: "l1"}
FIN = ("FT", "AET", "PEN", "CANC", "PST", "ABD", "AWD", "WO")

# id лиги в API-Football -> ключ лиги на сайте
LEAGUE_IDS = {
    235: "rpl", 2: "ucl", 3: "uel", 39: "apl", 140: "ll", 135: "sa",
    78: "bl", 61: "l1", 48: "efl", 81: "dfb", 143: "cdr",
}
LEAGUES = {
    "rpl": {"n": "РПЛ", "c": "RU", "o": 1},
    "ucl": {"n": "Лига чемпионов", "c": "EUR", "o": 2},
    "uel": {"n": "Лига Европы", "c": "EUR", "o": 3},
    "apl": {"n": "Премьер-лига", "c": "ENG", "o": 4},
    "ll": {"n": "Ла Лига", "c": "ESP", "o": 5},
    "sa": {"n": "Серия A", "c": "ITA", "o": 6},
    "bl": {"n": "Бундеслига", "c": "GER", "o": 7},
    "l1": {"n": "Лига 1", "c": "FRA", "o": 8},
    "efl": {"n": "Кубок английской лиги", "c": "ENG", "o": 9},
    "dfb": {"n": "Кубок Германии", "c": "GER", "o": 10},
    "cdr": {"n": "Кубок Испании", "c": "ESP", "o": 11},
}

# Русские названия. Если команды нет в списке, остаётся английское название из API.
RU = {
    "zenit st petersburg": "Зенит", "spartak moscow": "Спартак", "cska moscow": "ЦСКА",
    "lokomotiv moscow": "Локомотив", "dynamo moscow": "Динамо Москва", "krasnodar": "Краснодар",
    "rubin kazan": "Рубин", "akhmat grozny": "Ахмат", "rostov": "Ростов",
    "krylya sovetov samara": "Крылья Советов", "orenburg": "Оренбург",
    "baltika kaliningrad": "Балтика", "dynamo makhachkala": "Динамо Махачкала",
    "fakel voronezh": "Факел", "rodina moscow": "Родина", "akron togliatti": "Акрон",
    "akron tolyatti": "Акрон",
    "manchester city": "Манчестер Сити", "manchester united": "Манчестер Юнайтед",
    "liverpool": "Ливерпуль", "chelsea": "Челси", "arsenal": "Арсенал",
    "tottenham": "Тоттенхэм", "newcastle": "Ньюкасл", "aston villa": "Астон Вилла",
    "brighton": "Брайтон", "bournemouth": "Борнмут", "brentford": "Брентфорд",
    "fulham": "Фулхэм", "crystal palace": "Кристал Пэлас", "everton": "Эвертон",
    "west ham": "Вест Хэм", "wolves": "Вулверхэмптон", "nottingham forest": "Ноттингем Форест",
    "leeds": "Лидс Юнайтед", "sunderland": "Сандерленд", "burnley": "Бернли",
    "coventry": "Ковентри Сити", "ipswich": "Ипсвич Таун", "hull city": "Халл Сити",
    "real madrid": "Реал Мадрид", "barcelona": "Барселона", "atletico madrid": "Атлетико",
    "sevilla": "Севилья", "real betis": "Бетис", "valencia": "Валенсия", "villarreal": "Вильярреал",
    "athletic club": "Атлетик", "real sociedad": "Реал Сосьедад", "celta vigo": "Сельта",
    "girona": "Жирона", "cadiz": "Кадис", "mallorca": "Мальорка",
    "bayern munich": "Бавария", "borussia dortmund": "Боруссия Дортмунд",
    "bayer leverkusen": "Байер", "rb leipzig": "РБ Лейпциг", "eintracht frankfurt": "Айнтрахт",
    "vfb stuttgart": "Штутгарт", "wolfsburg": "Вольфсбург", "hoffenheim": "Хоффенхайм",
    "schalke 04": "Шальке", "hertha berlin": "Герта", "sc freiburg": "Фрайбург",
    "juventus": "Ювентус", "inter": "Интер", "ac milan": "Милан", "napoli": "Наполи",
    "roma": "Рома", "lazio": "Лацио", "atalanta": "Аталанта", "fiorentina": "Фиорентина",
    "bologna": "Болонья", "parma": "Парма", "udinese": "Удинезе", "genoa": "Дженоа",
    "paris saint germain": "ПСЖ", "marseille": "Марсель", "lyon": "Лион", "monaco": "Монако",
    "lille": "Лилль",
}


def ru(name):
    return RU.get(name.strip().lower(), name)


def msk_now():
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)


def load_json(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


class Budget(Exception):
    pass


class Api:
    def __init__(self, key, fetch=None, now=None):
        self.key, self._fetch, self.remaining = key, fetch, None
        today = (now or msk_now()).date().isoformat()
        u = load_json(USAGE, {})
        self.usage = u if u.get("d") == today else {"d": today, "n": 0}

    def get(self, path, **params):
        if self.usage["n"] >= CAP or (self.remaining is not None and self.remaining <= 5):
            raise Budget("Дневной лимит запросов почти исчерпан.")
        self.usage["n"] += 1
        if self._fetch:
            data = self._fetch(path, params)
        else:
            url = "%s/%s?%s" % (BASE, path, urllib.parse.urlencode(params))
            req = urllib.request.Request(url, headers={"x-apisports-key": self.key})
            with urllib.request.urlopen(req, timeout=30) as r:
                rem = r.headers.get("x-ratelimit-requests-remaining")
                if rem and rem.isdigit():
                    self.remaining = int(rem)
                data = json.load(r)
        if data.get("errors"):
            raise RuntimeError("API вернул ошибку: %s" % data["errors"])
        return data.get("response", [])

    def save(self):
        save_json(USAGE, self.usage)


def fx_row(fx):
    lg = LEAGUE_IDS.get(fx["league"]["id"])
    if not lg:
        return None
    goals = fx.get("goals") or {}
    t = fx["teams"]
    return [lg, fx["fixture"]["date"][:16], ru(t["home"]["name"]), ru(t["away"]["name"]),
            (fx["fixture"].get("status") or {}).get("short", ""), goals.get("home"), goals.get("away"),
            fx["fixture"]["id"], t["home"].get("id"), t["away"].get("id")]


def api_rows(api, days):
    rows, seen = [], set()
    for day in days:
        for fx in api.get("fixtures", date=day, timezone="Europe/Moscow"):
            r = fx_row(fx)
            if r and tuple(r[:4]) not in seen:
                seen.add(tuple(r[:4]))
                rows.append(r)
    return rows


def build_full(api, today, manual):
    days = [(today + datetime.timedelta(days=i)).isoformat() for i in range(-DAYS_BACK, DAYS_AHEAD)]
    rows = api_rows(api, days)
    if not rows:
        raise RuntimeError("API не вернул ни одного матча нужных лиг. Файлы не изменены.")
    got = {r[0] for r in rows}
    for r in manual:  # ручные матчи нужны только для лиг, которых нет в ответе API
        if r[0] not in got and r[1][:10] >= today.isoformat():
            rows.append(r)
    return sorted(rows, key=lambda r: r[1])


def ts(r):
    return datetime.datetime.fromisoformat(r[1] + ":00+03:00").timestamp()


def has_active(rows, now):
    t = now.timestamp()
    return any(len(r) > 4 and t - 5 * 3600 <= ts(r) <= t + 600 and r[4] not in FIN for r in rows)


def update_results(api, now, rows):
    today = now.date()
    days = [today.isoformat()]
    if now.hour < 5:
        days.insert(0, (today - datetime.timedelta(days=1)).isoformat())
    new = api_rows(api, days)
    if not new:
        return rows
    got = {r[0] for r in new}
    kept = [r for r in rows if not (r[1][:10] in days and r[0] in got)]
    return sorted(kept + new, key=lambda r: r[1])


def season(today):
    return today.year if today.month >= 7 else today.year - 1


def fetch_standings(api, today):
    teams = {}
    for lid, lg in STANDINGS.items():
        for item in api.get("standings", league=lid, season=season(today)):
            for group in item["league"]["standings"]:
                for e in group:
                    a = e["all"]
                    teams[str(e["team"]["id"])] = {
                        "lg": lg, "rank": e["rank"], "pts": e["points"], "p": a["played"], "w": a["win"],
                        "d": a["draw"], "l": a["lose"], "gf": a["goals"]["for"], "ga": a["goals"]["against"],
                        "form": e.get("form") or ""}
    return teams


def fetch_h2h(api, hid, aid):
    items = api.get("fixtures/headtohead", h2h="%s-%s" % (hid, aid), last=6)
    items.sort(key=lambda x: x["fixture"]["date"], reverse=True)
    out = []
    for x in items[:5]:
        g = x.get("goals") or {}
        out.append({"d": x["fixture"]["date"][:10], "h": ru(x["teams"]["home"]["name"]),
                    "a": ru(x["teams"]["away"]["name"]), "hg": g.get("home"), "ag": g.get("away"),
                    "lg": x["league"]["name"]})
    return out


def fetch_lineups(api, fixture_id, hid):
    out = {}
    for item in api.get("fixtures/lineups", fixture=fixture_id):
        side = "home" if item["team"]["id"] == hid else "away"
        pl = lambda arr: [[(p["player"].get("number") or ""), p["player"]["name"], p["player"].get("pos") or ""] for p in arr or []]
        out[side] = {"f": item.get("formation") or "", "c": (item.get("coach") or {}).get("name") or "",
                     "xi": pl(item.get("startXI")), "s": pl(item.get("substitutes"))}
    return out


def update_details(api, now, rows, details):
    t = now.timestamp()
    near = sorted([r for r in rows if len(r) > 9 and r[7] and t - 3600 <= ts(r) <= t + 36 * 3600], key=ts)
    spent, start = 0, api.usage["n"]
    def room():
        return api.usage["n"] - start < DETAIL_RUN_CAP
    # 1) составы: публикуются примерно за час до начала
    for r in near:
        d = details.setdefault(str(r[7]), {})
        if not d.get("lu") and ts(r) - 100 * 60 <= t <= ts(r) + 30 * 60 and room():
            lu = fetch_lineups(api, r[7], r[8])
            if lu:
                d["lu"] = lu
    # 2) встречи: один раз на матч
    for r in near:
        d = details.setdefault(str(r[7]), {})
        if "h2h" not in d and room():
            d["h2h"] = fetch_h2h(api, r[8], r[9])
    keep = {str(r[7]) for r in rows if len(r) > 9}
    return {k: v for k, v in details.items() if k in keep and v}


def write_all(rows, teams, details):
    leagues = json.dumps(LEAGUES, ensure_ascii=False, indent=2).replace("\n", "\n  ")
    text = ("/* Файл создаётся автоматически скриптом scripts/update_matches.py. */\n"
            "window.SHARK_DATA={\n  leagues:" + leagues + ",\n  matches:[\n" +
            ",\n".join("    " + json.dumps(r, ensure_ascii=False) for r in rows) + "\n  ]\n};\n")
    open(OUT, "w", encoding="utf-8").write(text)
    save_json(STATE, rows)
    save_json(DETAILS, details)
    save_json(TEAMS, teams)
    open(DETAILS_JS, "w", encoding="utf-8").write(
        "window.SHARK_DETAILS=" + json.dumps(details, ensure_ascii=False) + ";\nwindow.SHARK_TEAMS=" +
        json.dumps(teams, ensure_ascii=False) + ";\n")


def run(api, mode, now):
    rows = load_json(STATE, [])
    teams = load_json(TEAMS, {})
    details = load_json(DETAILS, {})
    manual = load_json(MANUAL, [])
    if mode == "full" or not rows:
        rows = build_full(api, now.date(), manual)
        try:
            teams = fetch_standings(api, now.date()) or teams
        except Budget:
            raise
        except Exception as e:
            print("Таблицы не обновлены: %s" % e)
    else:
        if has_active(rows, now):
            rows = update_results(api, now, rows)
        else:
            print("Идущих матчей нет, счёт не запрашиваем.")
    try:
        details = update_details(api, now, rows, details)
    except Budget as e:
        print(str(e))
    except Exception as e:
        print("Встречи и составы не обновлены: %s" % e)
    write_all(rows, teams, details)
    return rows


if __name__ == "__main__":
    key = os.environ.get("API_FOOTBALL_KEY", "").strip()
    if not key:
        sys.exit("Не задан ключ API_FOOTBALL_KEY.")
    api = Api(key)
    try:
        rows = run(api, sys.argv[1] if len(sys.argv) > 1 else "full", msk_now())
    except Budget as e:
        api.save()
        print(str(e))
        sys.exit(0)
    except Exception as e:
        api.save()
        sys.exit("Ошибка обновления: %s" % e)
    api.save()
    print("Матчей: %d, запросов сегодня: %d" % (len(rows), api.usage["n"]))
