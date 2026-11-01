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
        

class DateRangeFilterSerializer(serializers.Serializer):
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)

    def validate(self, attrs):
        from_date = attrs.get('from_date')
        to_date = attrs.get('to_date')
        if from_date and to_date and from_date > to_date:
            raise serializers.ValidationError("from_date cannot be later than to_date.")
        return attrs