import os
import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import GitHubProfile, ContributionDay

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
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(f"GitHub API error: status {response.status_code}")

        data = response.json()

        if "errors" in data:
            raise Exception(f"GraphQL Errors: {data['errors']}")

        user_data = data.get("data", {}).get("user")
        if not user_data:
            return None

        return user_data["contributionsCollection"]["contributionCalendar"]

    def sync_profile(self, username: str) -> GitHubProfile:
        """
        دریافت داده از گیت‌هاب و ذخیره/بروزرسانی در دیتابیس با تراکنش امن
        """
        calendar = self.fetch_user_contributions(username)
        if calendar is None:
            return None

        # استفاده از Atomic Transaction: یا همه ذخیره می‌شوند یا هیچ‌چیز ناقص ذخیره نمی‌شود
        with transaction.atomic():
            profile, _ = GitHubProfile.objects.get_or_create(username=username)
            profile.total_contributions = calendar["totalContributions"]

            # پیمایش هفته‌ها و روزها و ثبت بدون رکورد تکراری
            for week in calendar["weeks"]:
                for day in week["contributionDays"]:
                    ContributionDay.objects.update_or_create(
                        profile=profile,
                        date=day["date"],
                        defaults={
                            "contribution_count": day["contributionCount"],
                            "contribution_level": day["contributionLevel"]
                        }
                    )

            # بروزرسانی زمان سینک فقط در صورت موفقیت کامل
            profile.last_synced_at = timezone.now()
            profile.save()

        return profile