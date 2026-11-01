from datetime import date
from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .exceptions import GitHubRateLimitException
from .models import ContributionDay, GitHubProfile
from .serializers import GitHubProfileSerializer


class ModelTests(TestCase):
    """تست‌های مدل‌ها و محدودیت‌های دیتابیس"""

    def setUp(self):
        self.profile = GitHubProfile.objects.create(
            username="test_dev",
            total_contributions=10
        )

    def test_profile_str(self):
        self.assertEqual(str(self.profile), "test_dev")

    def test_unique_profile_date_constraint(self):
        """تست عدم امکان ثبت دو رکورد مشارکت در یک تاریخ برای یک کاربر"""
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
    """تست‌های ساختار خروجی Serializer"""

    def test_github_profile_serializer_empty_contributions(self):
        profile = GitHubProfile.objects.create(username="empty_user")
        serializer = GitHubProfileSerializer(profile)
        self.assertEqual(serializer.data["username"], "empty_user")
        self.assertEqual(serializer.data["contribution_days"], [])


class ProfileAPITests(APITestCase):
    """تست اندپوینت‌های خواندنی پروفایل و لیست مشارکت‌ها"""

    def setUp(self):
        self.profile = GitHubProfile.objects.create(
            username="atra",
            total_contributions=5
        )
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
    """تست اندپوینت POST /sync/ و ذخیره در دیتابیس با Mock"""

    @patch("contributions.services.GitHubService.fetch_user_contributions")
    def test_sync_profile_success(self, mock_fetch):
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

        profile = GitHubProfile.objects.get(username="mocked_user")
        self.assertEqual(profile.total_contributions, 15)
        self.assertIsNotNone(profile.last_synced_at)
        self.assertEqual(profile.contribution_days.count(), 1)

    @patch("contributions.services.GitHubService.fetch_user_contributions")
    def test_sync_profile_user_not_found(self, mock_fetch):
        mock_fetch.return_value = None

        url = reverse("contributions:profile-sync", kwargs={"username": "ghost_user"})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class NegativeAndEdgeCaseAPITests(APITestCase):
    """تست اعتبارسنجی ورودی‌ها و ارورهای API خارجی"""

    def setUp(self):
        self.profile = GitHubProfile.objects.create(username="testuser")

    def test_invalid_date_format_in_contributions_filter(self):
        url = reverse("contributions:profile-contributions-list", kwargs={"username": "testuser"})
        response = self.client.get(f"{url}?from_date=2026-99-99")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("from_date", response.data)

    def test_date_range_inverted(self):
        url = reverse("contributions:profile-contributions-list", kwargs={"username": "testuser"})
        response = self.client.get(f"{url}?from_date=2026-10-10&to_date=2026-10-01")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("contributions.services.GitHubService.fetch_user_contributions")
    def test_sync_github_rate_limit(self, mock_fetch):
        mock_fetch.side_effect = GitHubRateLimitException()

        url = reverse("contributions:profile-sync", kwargs={"username": "testuser"})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data["error"]["code"], "GitHubRateLimitException")