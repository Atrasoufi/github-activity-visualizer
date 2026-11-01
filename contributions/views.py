from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from .models import ContributionDay, GitHubProfile
from .serializers import ContributionSerializer, GitHubProfileSerializer
class GitHubProfileDetailView(RetrieveAPIView):
    """
    دریافت اطلاعات یک پروفایل به همراه روزهای مشارکت بر اساس نام کاربری
    """
    queryset = GitHubProfile.objects.all()
    serializer_class = GitHubProfileSerializer
    lookup_field = "username"
    lookup_url_kwarg = "username"
    
    
class ContributionDayListView(ListAPIView):
    """
    دریافت لیست روزهای مشارکت برای یک پروفایل مشخص
    """
    serializer_class = ContributionSerializer

    def get_queryset(self):
        username = self.kwargs.get("username")
        # ابتدا بررسی می‌کنیم پروفایل وجود داشته باشد؛ در غیر این صورت 404 برمی‌گرداند
        profile = get_object_or_404(GitHubProfile, username=username)
        return profile.contribution_days.all()