#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "colorama==0.4.6"
# ]
# ///
import subprocess
import json
import urllib.parse
from datetime import datetime
import re
from colorama import init, Fore, Style

# Globale Konfiguration
DEFAULT_INSTANCE_URL = "https://chaos.social"
USER_AGENT = "MastodonTrollHunter/1.0 (Python; +https://example.com)"
TROLL_KEYWORDS = [
    "woke",
    "ihr schafe",
    "trump ftw",
    "genderwahnsinn",
    "genderschwachsinn" "klimawahn",
    "💙",
    "!!!!!!!!!!!!!!!!!!!",
    "Deutsches Reich",
    "Schwachsinn",
    "fuer",
    "nur die afd",
    "ae",
]
# Initialisiere colorama
init()


# --- Hilfsfunktionen ---
def clean_html(content: str) -> str:
    """Entfernt HTML-Tags aus dem gegebenen Inhalt."""
    return re.sub(r"<[^>]+>", "", content)


def days_since(date_string: str) -> str | int:
    """Berechnet die Anzahl der Tage seit einem gegebenen Datum (als String)."""
    try:
        date = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        current_date = datetime.now(date.tzinfo)
        days_diff = (current_date - date).days
        return days_diff
    except Exception as e:
        return f"Error: {str(e)}"


def calculate_time_difference(post_time: str, reply_time: str) -> str | float:
    """Berechnet die Zeitdifferenz zwischen zwei Zeitpunkten in Stunden."""
    try:
        post_dt = datetime.fromisoformat(post_time.replace("Z", "+00:00"))
        reply_dt = datetime.fromisoformat(reply_time.replace("Z", "+00:00"))
        diff_seconds = (reply_dt - post_dt).total_seconds()
        diff_hours = diff_seconds / 3600
        return round(diff_hours, 1)
    except Exception as e:
        return f"Error: {str(e)}"


def execute_curl(
    url: str, method: str = "GET", data: dict | None = None, token: str | None = None
) -> dict:
    """Führt einen curl-Befehl aus und gibt die JSON-Antwort zurück."""
    try:
        cmd = [
            "curl",
            "-s",
            "-X",
            method,
            url,
            "-H",
            f"User-Agent: {USER_AGENT}",
            "-H",
            "Accept: application/json",
            "--max-time",
            "30",
        ]
        if token:
            cmd.extend(["-H", f"Authorization: Bearer {token}"])
        if data:
            for key, value in data.items():
                cmd.extend(["--data-urlencode", f"{key}={value}"])
        print(f"{Fore.CYAN}Executing curl command: {' '.join(cmd)}{Style.RESET_ALL}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"{Fore.CYAN}Raw response: {result.stdout[:200]}...{Style.RESET_ALL}")
        if not result.stdout.strip():
            return {"error": "Empty response from API"}
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON response: {str(e)}, Response: {result.stdout}"
            }
    except subprocess.CalledProcessError as e:
        return {
            "error": f"curl failed with code {e.returncode}: {e.stderr}, Command: {' '.join(cmd)}"
        }
    except Exception as e:
        return {"error": f"Failed to execute curl: {str(e)}"}


# --- Mastodon API Funktionen ---
def lookup_account(nickname: str, instance_url: str = DEFAULT_INSTANCE_URL) -> dict:
    """Ruft Kontoinformationen für einen Mastodon-Benutzer ab."""
    encoded_nickname = urllib.parse.quote(nickname)
    lookup_url = f"{instance_url}/api/v1/accounts/lookup?acct={encoded_nickname}"
    print(f"{Fore.CYAN}Requesting lookup URL: {lookup_url}{Style.RESET_ALL}")
    return execute_curl(lookup_url)


def get_account_statuses(
    account_id: str, instance_url: str = DEFAULT_INSTANCE_URL
) -> dict:
    """Ruft die Statusmeldungen eines Mastodon-Kontos ab."""
    statuses_url = (
        f"{instance_url}/api/v1/accounts/{account_id}/statuses?exclude_replies=false"
    )
    print(f"{Fore.CYAN}Requesting statuses URL: {statuses_url}{Style.RESET_ALL}")
    return execute_curl(statuses_url)


def get_status_context(
    status_id: str, instance_url: str = DEFAULT_INSTANCE_URL
) -> dict:
    """Ruft den Kontext (Konversation) eines Status ab."""
    context_url = f"{instance_url}/api/v1/statuses/{status_id}/context"
    print(f"{Fore.CYAN}Requesting context URL: {context_url}{Style.RESET_ALL}")
    return execute_curl(context_url)


def file_report(
    account_id: str,
    status_id: str,
    comment: str,
    category: str,
    token: str,
    forward: bool = False,
    instance_url: str = DEFAULT_INSTANCE_URL,
) -> dict:
    """Erstellt einen Bericht gegen ein Konto."""
    report_url = f"{instance_url}/api/v1/reports"
    data = {
        "account_id": account_id,
        "status_ids[]": status_id,
        "comment": comment,
        "category": category,
        "forward": str(forward).lower(),
    }
    return execute_curl(report_url, method="POST", data=data, token=token)


# --- Datenverarbeitungsfunktionen ---
def analyze_account_for_troll_indicators(account: dict) -> dict:
    """Analysiert ein Konto auf potenzielle Troll-Indikatoren."""
    now = datetime.now().timestamp()
    created_at = datetime.fromisoformat(
        account.get("created_at").replace("Z", "+00:00")
    ).timestamp()
    note = account.get("note", "").lower()
    indicators = {
        "new_account": (now - created_at) < 30 * 24 * 60 * 60,
        "low_followers_high_statuses": account.get("followers_count", 0) < 100
        and account.get("statuses_count", 0) > 1000,
        "suspicious_note": any(
            keyword in note for keyword in ["woke", "redpill", "ironie"]
        ),
        "low_statuses_count": account.get("statuses_count", 0) < 10,
    }
    return indicators


def analyze_reply_for_troll_indicators(reply: dict) -> dict:
    """Analysiert eine Antwort auf potenzielle Troll-Indikatoren."""
    account = reply.get("account", {})
    content = reply.get("content", "").lower()
    now = datetime.now().timestamp()
    created_at = datetime.fromisoformat(
        account.get("created_at").replace("Z", "+00:00")
    ).timestamp()
    indicators = {
        "new_account": (now - created_at) < 30 * 24 * 60 * 60,
        "low_followers": account.get("followers_count", 0) < 5,
        "low_statuses_count": account.get("statuses_count", 0) < 10,
        "suspicious_content": any(
            keyword.lower() in content
            or (keyword == "!!!!!!!!!!!!!!!!!!!" and re.search(r"!{10,}", content))
            for keyword in TROLL_KEYWORDS
        ),
    }
    return indicators


def highlight_troll_keywords(text: str) -> str:
    """Hebt Troll-Keywords im Text farbig und fettgedruckt hervor."""
    for keyword in TROLL_KEYWORDS:
        text = re.sub(
            re.escape(keyword),
            f"{Fore.RED}{Style.BRIGHT}{keyword}{Style.RESET_ALL}",
            text,
            flags=re.IGNORECASE,
        )
    return text


def create_mastodon_data_structure(account_data: dict, statuses: list) -> dict:
    """Erstellt die Datenstruktur für die Mastodon-Daten."""
    account = {
        "id": account_data.get("id"),
        "username": account_data.get("username"),
        "display_name": account_data.get("display_name"),
        "note": clean_html(account_data.get("note")),
        "created_at": account_data.get("created_at"),
        "followers_count": account_data.get("followers_count"),
        "following_count": account_data.get("following_count"),
        "statuses_count": account_data.get("statuses_count"),
        "last_status_at": account_data.get("last_status_at"),
        "fields": account_data.get("fields"),
        "potential_troll_indicators": analyze_account_for_troll_indicators(
            account_data
        ),
    }
    posts = []
    for status in statuses:
        post_id = status.get("id")
        context = get_status_context(post_id)
        if "error" in context:
            context = {"descendants": [], "error": context["error"]}
        replies = []
        for descendant in context.get("descendants", []):
            reply_account = descendant.get("account", {})
            reply = {
                "reply_id": descendant.get("id"),
                "created_at": descendant.get("created_at"),
                "content": clean_html(descendant.get("content")),
                "url": descendant.get("url"),
                "account": {
                    "id": reply_account.get("id"),
                    "username": reply_account.get("username"),
                    "acct": reply_account.get("acct"),
                    "display_name": reply_account.get("display_name"),
                    "created_at": reply_account.get("created_at"),
                    "followers_count": reply_account.get("followers_count"),
                    "following_count": reply_account.get("following_count"),
                    "statuses_count": reply_account.get("statuses_count", 0),
                    "last_status_at": reply_account.get("last_status_at"),
                },
            }
            reply["account"]["potential_troll_indicators"] = (
                analyze_reply_for_troll_indicators(reply)
            )
            replies.append(reply)
        posts.append(
            {
                "id": post_id,
                "created_at": status.get("created_at"),
                "content": clean_html(status.get("content")),
                "replies_count": status.get("replies_count"),
                "reblogs_count": status.get("reblogs_count"),
                "favourites_count": status.get("favourites_count"),
                "replies": replies,
            }
        )
    return {"account": account, "posts": posts}


def scrape_mastodon_data(
    nickname: str, instance_url: str = DEFAULT_INSTANCE_URL
) -> dict:
    """Hauptfunktion zum Scrapen von Mastodon-Daten."""
    account_data = lookup_account(nickname, instance_url)
    if "error" in account_data:
        return account_data
    account_id = account_data.get("id")
    if not account_id:
        return {"error": "Account ID not found in response"}
    statuses = get_account_statuses(account_id, instance_url)
    if "error" in statuses:
        return statuses
    return create_mastodon_data_structure(account_data, statuses)


# --- Ausgabe Funktionen ---
def print_account_information(account: dict):
    """Gibt die Kontoinformationen formatiert aus."""
    print(f"\n{Fore.BLUE}=== Account Information ==={Style.RESET_ALL}")
    print(f"{Fore.BLUE}Username:{Style.RESET_ALL} {account['username']}")
    print(f"{Fore.BLUE}Display Name:{Style.RESET_ALL} {account['display_name']}")
    print(f"{Fore.BLUE}Created At:{Style.RESET_ALL} {account['created_at']}")
    print(f"{Fore.BLUE}Followers:{Style.RESET_ALL} {account['followers_count']}")
    print(f"{Fore.BLUE}Following:{Style.RESET_ALL} {account['following_count']}")
    print(f"{Fore.BLUE}Statuses:{Style.RESET_ALL} {account['statuses_count']}")
    print(
        f"{Fore.BLUE}Last Active:{Style.RESET_ALL} {account['last_status_at']} ({days_since(account['last_status_at'])} days ago)"
    )
    print(f"\n{Fore.RED}Troll Indicators:{Style.RESET_ALL}")
    troll_flags = account["potential_troll_indicators"]
    # troll_count = sum(1 for flag in troll_flags.values() if flag)
    # print(f"{Fore.RED}{troll_flags} {'❌' * troll_count}{Style.RESET_ALL}")
    print_troll_indicators(troll_flags)


def print_troll_replies(posts: list, token: str | None = None):
    """Gibt die Posts mit Troll-Antworten formatiert aus."""
    print(f"\n{Fore.YELLOW}=== Posts with Troll Replies ==={Style.RESET_ALL}")
    for post in posts:
        troll_replies = [
            reply
            for reply in post["replies"]
            if any(reply["account"]["potential_troll_indicators"].values())
        ]
        if troll_replies:
            print(f"\n{Fore.YELLOW}Post ID:{Style.RESET_ALL} {post['id']}")
            print(f"{Fore.YELLOW}Posted At:{Style.RESET_ALL} {post['created_at'][:10]}")
            print(f"{Fore.YELLOW}Time:{Style.RESET_ALL} {post['created_at'][11:19]}")
            print(
                f"{Fore.YELLOW}Replies Count:{Style.RESET_ALL} {post['replies_count']}"
            )
            content_preview = (
                post["content"][:1000] + "..."
                if len(post["content"]) > 1000
                else post["content"]
            )
            print(f"{Fore.YELLOW}Content:{Style.RESET_ALL} {content_preview}")
            print(
                f"{Fore.MAGENTA}--- Replies with Troll Indicators ---{Style.RESET_ALL}"
            )
            for reply in troll_replies:
                print_reply_information(reply, post["created_at"], token)
                print(f"{Fore.MAGENTA}---{Style.RESET_ALL}")


def print_reply_information(
    reply: dict, post_created_at: str, token: str | None = None
):
    """Gibt Informationen zu einer einzelnen Antwort aus und fragt ggf. nach einem Report."""
    troll_flags = reply["account"]["potential_troll_indicators"]

    content = highlight_troll_keywords(reply["content"])
    content_preview = content[:1000] + "..." if len(content) > 1000 else content
    print(f"{Fore.MAGENTA}Reply ID:{Style.RESET_ALL} {reply['reply_id']}")
    print(
        f"{Fore.MAGENTA}Posted At:{Style.RESET_ALL} {reply['created_at'][:10]} {Fore.MAGENTA}Time:{Style.RESET_ALL} {reply['created_at'][11:19]}"
    )

    print(
        f"{Fore.MAGENTA}Reply Time Difference to post:{Style.RESET_ALL} {calculate_time_difference(post_created_at, reply['created_at'])} hours"
    )
    print(f"{Fore.MAGENTA}Content:{Style.RESET_ALL} {content_preview}")
    print(
        f"{Fore.MAGENTA}By:{Style.RESET_ALL} {reply['account']['acct']} ({reply.get('url', 'No URL available')})"
    )
    print(
        f"{Fore.MAGENTA}Followers:{Style.RESET_ALL} {reply['account']['followers_count']}  {Fore.MAGENTA}Following:{Style.RESET_ALL} {reply['account']['following_count']}  {Fore.MAGENTA}Statuses:{Style.RESET_ALL} {reply['account']['statuses_count']}"
    )

    print(
        f"{Fore.MAGENTA}Last Active:{Style.RESET_ALL} {reply['account']['last_status_at']} ({days_since(reply['account']['last_status_at'])} days ago)"
    )
    print(f"{Fore.RED}Troll Indicators:{Style.RESET_ALL}")
    print_troll_indicators(troll_flags)

    if token and token.strip():
        ask_for_report(reply, token)


def print_troll_indicators(indicators: dict):
    """Gibt die Troll-Indikatoren mit Häkchen und Kreuzen aus."""
    for key, value in indicators.items():
        symbol = "✅" if value else "❌"
        color = Fore.GREEN if value else Fore.WHITE
        print(f"  {Fore.RED}{key}:{Style.RESET_ALL} {color}{symbol}{Style.RESET_ALL}")


def ask_for_report(reply: dict, token: str):
    """Ask user if he wants to file a report."""
    report_choice = (
        input(
            f"{Fore.CYAN}Do you want to report this account? (y/n): {Style.RESET_ALL}"
        )
        .strip()
        .lower()
    )
    if report_choice == "y":
        comment = input(
            f"{Fore.CYAN}Enter comment for the report (max 1000 chars): {Style.RESET_ALL}"
        ).strip()
        category = (
            input(
                f"{Fore.CYAN}Enter category (spam/legal/violation/other): {Style.RESET_ALL}"
            )
            .strip()
            .lower()
        )
        if category not in ["spam", "legal", "violation", "other"]:
            print(
                f"{Fore.RED}Invalid category. Defaulting to 'other'.{Style.RESET_ALL}"
            )
            category = "other"
        forward = (
            input(
                f"{Fore.CYAN}Forward to remote admin if account is remote? (y/n): {Style.RESET_ALL}"
            )
            .strip()
            .lower()
            == "y"
        )
        report_response = file_report(
            account_id=reply["account"]["id"],
            status_id=reply["reply_id"],
            comment=comment[:1000],  # Ensure max 1000 chars
            category=category,
            token=token,
            forward=forward,
        )
        if "error" in report_response:
            print(
                f"{Fore.RED}Failed to file report: {report_response['error']}{Style.RESET_ALL}"
            )
        else:
            print(
                f"{Fore.GREEN}Report filed successfully: ID {report_response.get('id')}{Style.RESET_ALL}"
            )


# --- Hauptfunktion ---
def main():
    """Hauptfunktion des Skripts."""
    nickname = input("Enter Mastodon nickname (username@instance.io): ")
    token = input(
        "Enter your Mastodon API token (leave empty if you don't want to report): "
    )
    data = scrape_mastodon_data(nickname)
    if "error" in data:
        print(f"{Fore.RED}{data['error']}{Style.RESET_ALL}")
        return
    print_account_information(data["account"])
    print_troll_replies(data["posts"], token)


if __name__ == "__main__":
    main()
