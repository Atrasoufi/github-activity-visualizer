from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from .models import ContributionDay, GitHubProfile
from .serializers import ContributionSerializer, GitHubProfileSerializer
from .services import AnalyticsService, GitHubService


class GitHubProfileDetailView(RetrieveAPIView):
    """
    دریافت مشخصات کلی کاربر به همراه تمام روزهای مشارکت
    """
    queryset = GitHubProfile.objects.all()
    serializer_class = GitHubProfileSerializer
    lookup_field = "username"
    lookup_url_kwarg = "username"


class ContributionDayListView(ListAPIView):
    """
    لیست روزهای مشارکت با امکان فیلتر بازه زمانی:
    ?from_date=2026-01-01&to_date=2026-12-31
    """
    serializer_class = ContributionSerializer

    def get_queryset(self):
        username = self.kwargs.get("username")
        profile = get_object_or_404(GitHubProfile, username=username)
        queryset = profile.contribution_days.all()

        from_date = self.request.query_params.get("from_date")
        to_date = self.request.query_params.get("to_date")

        if from_date:
            queryset = queryset.filter(date__gte=from_date)
        if to_date:
            queryset = queryset.filter(date__lte=to_date)

        return queryset


class GitHubProfileStatsView(APIView):
    """
    محاسبه آمار تحلیلی کاربر: استریک فعلی، طولانی‌ترین استریک و پرکارترین روز
    """
    def get(self, request, username):
        profile = get_object_or_404(GitHubProfile, username=username)
        stats = AnalyticsService.calculate_stats(profile)
        return Response(stats, status=status.HTTP_200_OK)


class GitHubProfileSyncView(APIView):
    """
    دریافت و ذخیره اطلاعات زنده از گیت‌هاب
    """
    serializer_class = GitHubProfileSerializer

    @extend_schema(responses={200: GitHubProfileSerializer})
    def post(self, request, username):
        service = GitHubService()
        try:
            profile = service.sync_profile(username)
            if profile is None:
                return Response(
                    {"detail": f"GitHub user '{username}' not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
            serializer = GitHubProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)