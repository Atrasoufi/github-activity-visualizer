from django.urls import path
from .views import ContributionDayListView, GitHubProfileDetailView, GitHubProfileSyncView

app_name = "contributions"

urlpatterns = [
    path("profiles/<str:username>/", GitHubProfileDetailView.as_view(), name="profile-detail"),
    path("profiles/<str:username>/contributions/", ContributionDayListView.as_view(), name="profile-contributions-list"),
    path("profiles/<str:username>/sync/", GitHubProfileSyncView.as_view(), name="profile-sync"),
]