from datetime import date
from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ContributionDay, GitHubProfile
from .serializers import ContributionSerializer, GitHubProfileSerializer


class ModelTests(TestCase):
    """تست‌های مدل‌ها و اعتبارسنجی محدودیت‌های دیتابیس"""

    def setUp(self):
        self.profile = GitHubProfile.objects.create(username="test_dev", total_contributions=10)

    def test_profile_str(self):
        self.assertEqual(str(self.profile), "test_dev")

    def test_unique_profile_date_constraint(self):
        """بررسی جلوگیری از ثبت رکورد تکراری برای یک پروفایل در یک روز"""
        ContributionDay.objects.create(
            profile=self.profile,
            date=date(2026, 11, 1),
            contribution_count=3,
            contribution_level="FIRST_QUARTILE",
        )

        with self.assertRaises(IntegrityError):
            ContributionDay.objects.create(
                profile=self.profile,
                date=date(2026, 11, 1),
                contribution_count=5,
                contribution_level="SECOND_QUARTILE",
            )


class SerializerTests(TestCase):
    """تست خروجی و ساختار سریالایزرها"""

    def test_github_profile_serializer_empty_contributions(self):
        profile = GitHubProfile.objects.create(username="empty_user")
        serializer = GitHubProfileSerializer(profile)
        self.assertEqual(serializer.data["username"], "empty_user")
        self.assertEqual(serializer.data["contribution_days"], [])


class ProfileAPITests(APITestCase):
    """تست اندپوینت‌های GET برای پروفایل و مشارکت‌ها"""

    def setUp(self):
        self.profile = GitHubProfile.objects.create(username="atra", total_contributions=5)
        self.day = ContributionDay.objects.create(
            profile=self.profile,
            date=date(2026, 11, 1),
            contribution_count=5,
            contribution_level="FIRST_QUARTILE",
        )

    def test_get_profile_detail_success(self):
        url = reverse("contributions:profile-detail", kwargs={"username": "atra"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "atra")
        self.assertEqual(len(response.data["contribution_days"]), 1)

    def test_get_profile_detail_not_found(self):
        url = reverse("contributions:profile-detail", kwargs={"username": "unknown_user"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_contributions_list_success(self):
        url = reverse("contributions:profile-contributions-list", kwargs={"username": "atra"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_contributions_list_not_found(self):
        url = reverse("contributions:profile-contributions-list", kwargs={"username": "unknown_user"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SyncAPITests(APITestCase):
    """تست اندپوینت POST /sync/ با شبیه‌سازی (Mock) پاسخ گیت‌هاب"""

    @patch("contributions.services.GitHubService.fetch_user_contributions")
    def test_sync_profile_success(self, mock_fetch):
        # داده ساختگی شبیه‌سازی‌شده از گیت‌هاب
        mock_fetch.return_value = {
            "totalContributions": 15,
            "weeks": [
                {
                    "contributionDays": [
                        {
                            "date": "2026-11-01",
                            "contributionCount": 15,
                            "contributionLevel": "THIRD_QUARTILE",
                        }
                    ]
                }
            ],
        }

        url = reverse("contributions:profile-sync", kwargs={"username": "mocked_user"})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "mocked_user")
        self.assertEqual(response.data["total_contributions"], 15)

        # اعتبارسنجی در دیتابیس تست
        profile = GitHubProfile.objects.get(username="mocked_user")
        self.assertEqual(profile.total_contributions, 15)
        self.assertIsNotNone(profile.last_synced_at)
        self.assertEqual(profile.contribution_days.count(), 1)

    @patch("contributions.services.GitHubService.fetch_user_contributions")
    def test_sync_profile_user_not_found(self, mock_fetch):
        # شبیه‌سازی حالتی که کاربر در گیت‌هاب وجود ندارد
        mock_fetch.return_value = None

        url = reverse("contributions:profile-sync", kwargs={"username": "ghost_user"})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)