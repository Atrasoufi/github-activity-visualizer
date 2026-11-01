from django.urls import path
from .views import ContributionDayListView, GitHubProfileDetailView

app_name = "contributions"

urlpatterns = [
    path("profiles/<str:username>/", GitHubProfileDetailView.as_view(), name="profile-detail"),
    path("profiles/<str:username>/contributions/", ContributionDayListView.as_view(), name="profile-contributions-list"),
]