#!/usr/bin/env python3
"""
update_balances.py

Оновлює файл balances.json у корені репозиторію актуальними балансами Monobank-банок.
Можна запускати на Raspberry Pi по cron.

Додатково: автоматично пушить balances.json у GitHub.
Усі налаштування (GITHUB_TOKEN, REPO, BRANCH, LONG_JAR_ID_1, LONG_JAR_ID_2) — у файлі .secrets у такому вигляді:
GITHUB_TOKEN=...
REPO=owner/repo
BRANCH=main
LONG_JAR_ID_1=...
LONG_JAR_ID_2=...
"""

import requests
import json
import os
import sys
from datetime import datetime, timezone
import base64

BALANCES_FILEPATH = "balances.json"
SECRETS_PATH = ".secrets"

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
    # Перевіряємо обов'язкові поля
    required = ["GITHUB_TOKEN", "REPO", "BRANCH", "LONG_JAR_ID_1", "LONG_JAR_ID_2"]
    for req in required:
        if req not in secrets:
            print(f"{req} не знайдено у {secrets_path}!", file=sys.stderr)
            sys.exit(1)
    return secrets

# --- Monobank API ---

def get_jar_info(long_jar_id):
    """Отримати дані банки по longJarId через офіційний API"""
    url = f"https://api.monobank.ua/bank/jar/{long_jar_id}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()

# --- GitHub API ---

def get_file_sha(token, repo, path, branch):
    """Повертає SHA існуючого файлу (щоб оновити його через API)"""
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    headers = {"Authorization": f"token {token}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()["sha"]
    return None

def update_github_file(token, repo, path, content, message, branch, sha=None):
    """Оновлює або створює файл у репозиторії через GitHub API"""
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"}
    data = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": branch
    }
    if sha:
        data["sha"] = sha
    r = requests.put(url, headers=headers, json=data)
    if r.status_code not in (200, 201):
        print(f"GitHub API error [{r.status_code}]: {r.text}", file=sys.stderr)
        raise Exception("Не вдалося оновити файл у репозиторії")
    print(f"balances.json оновлено у GitHub ({r.json()['content']['html_url']})")

# --- Основна логіка ---

def main():
    secrets = read_secrets(SECRETS_PATH)
    github_token = secrets["GITHUB_TOKEN"]
    repo = secrets["REPO"]
    branch = secrets["BRANCH"]
    long_jar_ids = [secrets["LONG_JAR_ID_1"], secrets["LONG_JAR_ID_2"]]

    jars = []
    for long_jar_id in long_jar_ids:
        try:
            jar = get_jar_info(long_jar_id)
            jars.append({
                "ownerName": jar.get("ownerName"),
                "title": jar.get("title"),
                "amount": jar.get("amount"),
                "ownerIcon": jar.get("ownerIcon"),
                "currency": jar.get("currency"),
                "jarId": jar.get("jarId")
            })
        except Exception as e:
            jars.append({
                "ownerName": "Помилка",
                "title": f"Не вдалося отримати баланс ({long_jar_id})",
                "amount": None,
                "ownerIcon": "",
                "currency": None,
                "jarId": long_jar_id,
                "error": str(e)
            })
    balances = {
        "jars": jars,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    # Запис локально
    with open(BALANCES_FILEPATH, "w", encoding="utf-8") as f:
        json.dump(balances, f, ensure_ascii=False, indent=2)
    print("Оновлено balances.json локально")

    # Пуш у GitHub
    sha = get_file_sha(github_token, repo, BALANCES_FILEPATH, branch)
    update_github_file(
        github_token,
        repo,
        BALANCES_FILEPATH,
        json.dumps(balances, ensure_ascii=False, indent=2),
        f"Update balances.json ({datetime.now().isoformat(timespec='seconds')})",
        branch,
        sha
    )

if __name__ == "__main__":
    main()
