import os
import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import GitHubProfile, ContributionDay
from datetime import date, timedelta
from typing import Dict, Any

from .exceptions import (
    GitHubAPIException,
    GitHubRateLimitException,
    GitHubUserNotFoundException,
    GitHubAuthException,
)

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

    def fetch_user_contributions(self, username: str):
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.post(
                "https://api.github.com/graphql",
                json={"query": self.QUERY, "variables": {"username": username}},
                headers=headers,
                timeout=10
            )
        except requests.RequestException:
            raise GitHubAPIException("Connection to GitHub timed out or failed.")

        if response.status_code == 401:
            raise GitHubAuthException()
        if response.status_code == 403:
            raise GitHubRateLimitException()
        if response.status_code != 200:
            raise GitHubAPIException(f"GitHub returned unexpected status {response.status_code}")

        payload = response.json()
        if "errors" in payload:
            error_msg = payload["errors"][0].get("message", "")
            if "Could not resolve to a User" in error_msg:
                raise GitHubUserNotFoundException()
            raise GitHubAPIException("Error in GraphQL query evaluation.")

        user_data = payload.get("data", {}).get("user")
        if not user_data:
            raise GitHubUserNotFoundException()

        return user_data

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
    
    
class AnalyticsService:
    @staticmethod
    def calculate_streaks(contribution_days):
        days = list(contribution_days.order_by('date'))
        if not days:
            return {"current_streak": 0, "longest_streak": 0}

        longest_streak = 0
        temp_streak = 0
        prev_date = None

        for day in days:
            if day.count > 0:
                if prev_date is None or day.date == prev_date + timedelta(days=1):
                    temp_streak += 1
                else:
                    temp_streak = 1
                prev_date = day.date
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 0
                prev_date = day.date

        today = date.today()
        yesterday = today - timedelta(days=1)
        active_days = {d.date: d.count for d in days if d.count > 0}

        current_streak = 0
        check_date = today if today in active_days else (yesterday if yesterday in active_days else None)

        if check_date:
            while check_date in active_days:
                current_streak += 1
                check_date -= timedelta(days=1)

        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak
        }