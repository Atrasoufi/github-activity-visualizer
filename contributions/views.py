from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ContributionDay, GitHubProfile
from .serializers import ContributionSerializer, GitHubProfileSerializer
from .services import GitHubService


class GitHubProfileDetailView(RetrieveAPIView):
    queryset = GitHubProfile.objects.all()
    serializer_class = GitHubProfileSerializer
    lookup_field = "username"
    lookup_url_kwarg = "username"


class ContributionDayListView(ListAPIView):
    serializer_class = ContributionSerializer

    def get_queryset(self):
        username = self.kwargs.get("username")
        profile = get_object_or_404(GitHubProfile, username=username)
        return profile.contribution_days.all()


class GitHubProfileSyncView(APIView):
    """
    دریافت و ذخیره داده‌های زنده گیت‌هاب برای یک نام کاربری مشخص
    """
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