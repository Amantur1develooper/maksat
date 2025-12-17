import os, json, logging, requests
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

log = logging.getLogger(__name__)

# ---------- ЛОКАЛЬНАЯ КОНФИГ ----------
# 1) Пробуем из переменных окружения
ENV_BOT = os.getenv("TELEGRAM_BOT_TOKEN")
ENV_CHAT = os.getenv("TELEGRAM_CHAT_ID")

# 2) Если их нет — используем локальные dev-значения (НЕ коммить в git!)
DEV_BOT = "8583338642:AAEn5fyWZM4qyMDaRL6tNxJzPzt_CIf-UHY"   # <— твой тестовый токен
# DEV_CHAT = "1028830632"  
DEV_CHAT = "317815640"
   
# 317815640# <— твой user id (или id группы)

# 3) Итоговые значения
TELEGRAM_BOT_TOKEN = (ENV_BOT or DEV_BOT).strip()
TELEGRAM_CHAT_ID   = (ENV_CHAT or DEV_CHAT).strip()
# --------------------------------------

def index(request):
    return render(request, "index.html")

def contact(request):
    return render(request, "contact.html")

@csrf_exempt
def tg_lead(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        log.exception("bad_json")
        return JsonResponse({"ok": False, "error": "bad_json"}, status=200)

    full_name = (data.get("full_name") or "").strip()
    email     = (data.get("email") or "").strip()
    phone     = (data.get("phone") or "").strip()
    message   = (data.get("message") or "").strip()

    if not full_name or (not email and not phone):
        return JsonResponse({"ok": False, "error": "validation"}, status=200)

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.error("telegram_env_missing BOT=%s CHAT=%s",
                  bool(TELEGRAM_BOT_TOKEN), bool(TELEGRAM_CHAT_ID))
        return JsonResponse({"ok": False, "error": "server_misconfigured"}, status=200)

    # собираем текст
    lines = [
        "🟦 *ETHNIC GAMES — New Lead*",
        f"*Name:* {full_name}",
        f"*Email:* {email or '—'}",
        f"*Phone:* {phone or '—'}",
    ]
    if message:
        lines.append(f"*Message:* {message}")
    text = "\n".join(lines)

    # отправляем в Telegram
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        r = requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            timeout=10
        )
        try:
            r_json = r.json()
        except Exception:
            r_json = {"raw": r.text[:300]}

        if r.status_code != 200 or not r_json.get("ok"):
            log.error("telegram_send_failed code=%s body=%s", r.status_code, r_json)
            return JsonResponse({"ok": False, "error": "telegram_failed", "details": r_json}, status=200)
    except requests.exceptions.RequestException:
        log.exception("telegram_request_exception")
        return JsonResponse({"ok": False, "error": "telegram_request_exception"}, status=200)

    return JsonResponse({"ok": True})
