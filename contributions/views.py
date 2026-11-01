import logging
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import GitHubAPIException
from .models import ContributionDay, GitHubProfile
from .serializers import (
    ContributionSerializer,
    DateRangeFilterSerializer,
    GitHubProfileSerializer,
)
from .services import AnalyticsService, GitHubService

logger = logging.getLogger(__name__)


class GitHubProfileDetailView(generics.RetrieveAPIView):
    """دریافت اطلاعات کلی پروفایل گیت‌هاب"""
    queryset = GitHubProfile.objects.all()
    serializer_class = GitHubProfileSerializer
    lookup_field = "username"


class ContributionDayListView(generics.ListAPIView):
    """دریافت روزهای مشارکت یک پروفایل با فیلتر بازه تاریخی"""
    serializer_class = ContributionSerializer

    def get_queryset(self):
        username = self.kwargs["username"]
        profile = get_object_or_404(GitHubProfile, username=username)

        filter_serializer = DateRangeFilterSerializer(data=self.request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        validated_data = filter_serializer.validated_data

        queryset = ContributionDay.objects.filter(profile=profile)

        if "from_date" in validated_data:
            queryset = queryset.filter(date__gte=validated_data["from_date"])
        if "to_date" in validated_data:
            queryset = queryset.filter(date__lte=validated_data["to_date"])

        return queryset.order_by("date")


class GitHubProfileStatsView(APIView):
    """دریافت آمار تحلیلی استریک‌ها و فعال‌ترین روزها"""
    def get(self, request, username):
        profile = get_object_or_404(GitHubProfile, username=username)
        contribution_days = ContributionDay.objects.filter(profile=profile)
        stats = AnalyticsService.calculate_streaks(contribution_days)
        return Response(stats, status=status.HTTP_200_OK)


class GitHubProfileSyncView(APIView):
    """سینک و ذخیره‌سازی اطلاعات کاربر از گیت‌هاب"""
    def post(self, request, username):
        service = GitHubService()
        try:
            profile = service.sync_profile(username)
            if not profile:
                return Response(
                    {"error": {"code": "NotFound", "message": "GitHub user was not found."}},
                    status=status.HTTP_404_NOT_FOUND,
                )
            serializer = GitHubProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except GitHubAPIException as e:
            return Response(
                {"error": {"code": e.__class__.__name__, "message": str(e)}},
                status=e.status_code,
            )
        except Exception:
            logger.exception("Unexpected error during profile sync for %s", username)
            return Response(
                {"error": {"code": "InternalError", "message": "An unexpected error occurred."}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )