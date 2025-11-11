# jafar/integrations/github_api.py

import os
import requests
import subprocess
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from rich.console import Console
from rich.panel import Panel

load_dotenv(find_dotenv())

console = Console()
TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_API_URL = "https://api.github.com"

HEADERS = {"Authorization": f"token {TOKEN}"} if TOKEN else {}


def get_git_status(project_name: str):
    project_path = Path.home() / "Projects" / project_name
    if not project_path.exists():
        console.print(
            Panel(f"❌ Проект [bold]{project_name}[/bold] не найден.", style="red")
        )
        return

    os.chdir(project_path)
    console.rule("[green]Git Status[/green]")

    result = subprocess.run(["git", "status"], capture_output=True, text=True)
    console.print(result.stdout)


def list_pull_requests(owner: str, repo: str):
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        console.print(
            Panel(f"❌ Ошибка получения PR: {response.status_code}", style="red")
        )
        return []

    return response.json()


def list_issues(owner: str, repo: str, mode="issues", project_number=None):
    if mode == "board":
        # Project Board через GraphQL
        # project_number (int): смотри в URL своей Project Board, например .../projects/1
        query = """
        query($owner: String!, $repo: String!, $projectNumber: Int!, $first: Int!) {
          repository(owner: $owner, name: $repo) {
            projectV2(number: $projectNumber) {
              items(first: $first) {
                nodes {
                  content {
                    ... on Issue {
                      number
                      title
                      body
                      url
                    }
                  }
                  fieldValues(first: 10) {
                    nodes {
                      value
                    }
                  }
                }
              }
            }
          }
        }
        """
        variables = {
            "owner": owner,
            "repo": repo,
            "projectNumber": int(
                project_number or 1
            ),  # по умолчанию 1, поменяй под себя!
            "first": 50,
        }
        resp = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables},
            headers=HEADERS,
        )
        if resp.status_code != 200:
            console.print(Panel(f"❌ Ошибка GraphQL: {resp.status_code}", style="red"))
            return []
        data = resp.json()
        items = data["data"]["repository"]["projectV2"]["items"]["nodes"]
        # Приведём к такому же виду, как обычные issues
        return [
            {
                "number": i["content"]["number"],
                "title": i["content"]["title"],
                "body": i["content"]["body"],
                "url": i["content"]["url"],
            }
            for i in items
            if i["content"]
        ]

    # По-старому: все открытые Issues (REST)
    issues = []
    page = 1
    while True:
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues?state=open&per_page=100&page={page}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            console.print(
                Panel(
                    f"❌ Ошибка получения Issues: {response.status_code}", style="red"
                )
            )
            return issues
        data = response.json()
        if not data:
            break
        issues.extend(data)
        if len(data) < 100:
            break
        page += 1
    return issues


def list_my_tasks(owner: str, repo: str):
    if not USERNAME:
        console.print(
            "[bold red]⚠️ Переменная окружения GITHUB_USERNAME не задана![/bold red]"
        )
        return []

    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues?assignee={USERNAME}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        console.print(
            Panel(f"❌ Ошибка получения задач: {response.status_code}", style="red")
        )
        return []

    return response.json()
