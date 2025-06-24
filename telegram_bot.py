import os
import json
import logging
import re
import sys
import requests
import base64
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

BEST_BIDDERS_FILE = "best_bidders.json"
SECRETS_PATH = "/home/pi/.first-one-secrets"

def read_secrets(secrets_path=SECRETS_PATH):
    """Зчитує всі змінні з .secrets у словник"""
    if not os.path.exists(secrets_path):
        print(f"Файл {secrets_path} не знайдено!", file=sys.stderr)
        sys.exit(1)
    secrets = {}
    with open(secrets_path, encoding="utf-8") as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split("=", 1)
                secrets[k.strip()] = v.strip()
    # мінімально необхідні для роботи
    required = ["TELEGRAM_TOKEN", "GITHUB_TOKEN", "REPO", "BRANCH", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"]
    for req in required:
        if req not in secrets:
            print(f"{req} не знайдено у {secrets_path}!", file=sys.stderr)
            sys.exit(1)
    return secrets

def get_file_sha(token, repo, path, branch):
    """Повертає SHA існуючого файлу (щоб оновити його через API)"""
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    headers = {"Authorization": f"token {token}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()["sha"]
    return None

def update_github_file(token, repo, path, content, message, branch, committer_name, committer_email, sha=None):
    """Оновлює або створює файл у репозиторії через GitHub API"""
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"}
    data = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": branch,
        "committer": {
            "name": committer_name,
            "email": committer_email
        }
    }
    if sha:
        data["sha"] = sha
    r = requests.put(url, headers=headers, json=data)
    if r.status_code not in (200, 201):
        raise Exception(f"GitHub API error [{r.status_code}]: {r.text}")
    return r.json()["content"]["html_url"]

def load_best_bidders():
    if os.path.exists(BEST_BIDDERS_FILE):
        with open(BEST_BIDDERS_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    return {"boy": {"number": None, "sum": 0}, "girl": {"number": None, "sum": 0}}

def save_best_bidders(best_bidders):
    with open(BEST_BIDDERS_FILE, "w", encoding='utf-8') as f:
        json.dump(best_bidders, f, ensure_ascii=False, indent=2)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    chat_id = update.effective_chat.id

    try:
        match = re.match(r"^(х|д)\s+(\d+)\s+(\d+)$", msg.lower())
        if not match:
            raise ValueError

        gender_raw, number_raw, sum_raw = match.groups()
        number = int(number_raw)
        total_sum = int(sum_raw)
        if number < 1 or total_sum < 1:
            raise ValueError

        best_bidders = load_best_bidders()
        key = "boy" if gender_raw == 'х' else "girl"

        best_bidders[key] = {"number": number, "sum": total_sum}
        save_best_bidders(best_bidders)

        # --- GitHub commit via API ---
        secrets = read_secrets()
        github_token = secrets["GITHUB_TOKEN"]
        repo = secrets["REPO"]
        branch = secrets["BRANCH"]
        committer_name = secrets["GIT_COMMITTER_NAME"]
        committer_email = secrets["GIT_COMMITTER_EMAIL"]
        commit_message = f"update best {key}: #{number} {total_sum} грн"

        try:
            sha = get_file_sha(github_token, repo, BEST_BIDDERS_FILE, branch)
            html_url = update_github_file(
                github_token,
                repo,
                BEST_BIDDERS_FILE,
                json.dumps(best_bidders, ensure_ascii=False, indent=2),
                commit_message,
                branch,
                committer_name,
                committer_email,
                sha
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ Оновлено та закомічено! {'Хлопчик' if key=='boy' else 'Дівчинка'} №{number} — {total_sum} грн.\n[Переглянути у GitHub]({html_url})",
                parse_mode='Markdown'
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ Оновлено локально, але не вдалося закомітити у репозиторій: {e}"
            )

    except ValueError:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Неправильний формат! Надішліть повідомлення у вигляді:\n"
                 "`х 2 100` — ставка на хлопчика №2, 100 грн\n"
                 "`д 3 200` — ставка на дівчинку №3, 200 грн",
            parse_mode='Markdown'
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Сталася помилка: {e}"
        )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    secrets = read_secrets()
    token = secrets["TELEGRAM_TOKEN"]
    app = ApplicationBuilder().token(token).build()
    handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    app.add_handler(handler)
    print("Bot started...")
    app.run_polling()
