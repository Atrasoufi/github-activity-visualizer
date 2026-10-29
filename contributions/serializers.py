from rest_framework import serializers
from .models import GitHubProfile, ContributionDay

        
class ContributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContributionDay
        fields = ['date', 'contribution_count', 'contribution_level']
        
class GitHubProfileSerializer(serializers.ModelSerializer):
    contribution_days = ContributionSerializer(many=True, read_only=True)

    class Meta:
        model = GitHubProfile
        fields = ['username', 'total_contributions', 'last_synced_at', 'contribution_days']
        
