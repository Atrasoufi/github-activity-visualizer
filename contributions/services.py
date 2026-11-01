import os
import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import GitHubProfile, ContributionDay
from datetime import date, timedelta
from typing import Dict, Any

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
    
    
class AnalyticsService:
    @staticmethod
    def calculate_stats(profile: GitHubProfile) -> Dict[str, Any]:
        days = list(profile.contribution_days.order_by("date"))

        if not days:
            return {
                "total_contributions": 0,
                "current_streak": 0,
                "longest_streak": 0,
                "most_active_day": None,
            }

        longest_streak = 0
        current_streak = 0
        temp_streak = 0
        prev_date = None
        most_active_day = None
        max_count = -1

        for day in days:
            # پیدا کردن پرکارترین روز
            if day.contribution_count > max_count:
                max_count = day.contribution_count
                most_active_day = {
                    "date": str(day.date),
                    "count": day.contribution_count,
                    "level": day.contribution_level,
                }

            # محاسبه استریک‌ها (روزهای متوالی با مشارکت > 0)
            if day.contribution_count > 0:
                if prev_date and (day.date - prev_date).days == 1:
                    temp_streak += 1
                else:
                    temp_streak = 1
                longest_streak = max(longest_streak, temp_streak)
                prev_date = day.date
            else:
                prev_date = None
                temp_streak = 0

        # محاسبه زنجیره فعلی تا امروز یا دیروز
        today = date.today()
        yesterday = today - timedelta(days=1)
        active_dates = {d.date for d in days if d.contribution_count > 0}

        curr_date = today if today in active_dates else (yesterday if yesterday in active_dates else None)
        while curr_date and curr_date in active_dates:
            current_streak += 1
            curr_date -= timedelta(days=1)

        return {
            "total_contributions": profile.total_contributions,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "most_active_day": most_active_day,
        }