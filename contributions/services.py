import os
import requests
from django.conf import settings

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

GRAPHQL_QUERY = """
query($username: String!) {
  user(login: $username) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""


class GitHubService:
    def __init__(self, token: str = None):
        self.token = token or os.getenv("GITHUB_TOKEN") or getattr(settings, "GITHUB_TOKEN", None)

    def fetch_user_contributions(self, username: str) -> dict:
        """
        ارسال کوئری به گیت‌هاب و دریافت خام اطلاعات تقویم مشارکت
        """
        if not self.token:
            raise ValueError("GitHub Token is not set. Please set GITHUB_TOKEN.")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "GitHub-Activity-Visualizer"
        }

        response = requests.post(
            GITHUB_GRAPHQL_URL,
            json={"query": GRAPHQL_QUERY, "variables": {"username": username}},
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            raise Exception(f"GitHub API error: status {response.status_code}")

        data = response.json()

        # بررسی خطاهای ساختاری GraphQL یا نبود کاربر
        if "errors" in data:
            raise Exception(f"GraphQL Errors: {data['errors']}")

        user_data = data.get("data", {}).get("user")
        if not user_data:
            return None  # کاربر در گیت‌هاب وجود ندارد

        return user_data["contributionsCollection"]["contributionCalendar"]