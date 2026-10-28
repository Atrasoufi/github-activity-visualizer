from django.db import models
from django.utils import timezone


class GitHubProfile(models.Model):
    username = models.CharField(max_length=255, unique=True)
    total_contributions = models.PositiveIntegerField(default=0)
    last_synced_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.username


class ContributionDay(models.Model):
    LEVEL_CHOICES = [
        ("NONE", "None"),
        ("FIRST_QUARTILE", "First Quartile"),
        ("SECOND_QUARTILE", "Second Quartile"),
        ("THIRD_QUARTILE", "Third Quartile"),
        ("FOURTH_QUARTILE", "Fourth Quartile"),
    ]

    profile = models.ForeignKey(
        GitHubProfile,
        on_delete=models.CASCADE,
        related_name="contribution_days"
    )
    date = models.DateField()
    contribution_count = models.PositiveIntegerField(default=0)
    contribution_level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default="NONE"
    )

    class Meta:
        unique_together = ("profile", "date")
        ordering = ["date"]

    def __str__(self):
        return f"{self.profile.username} - {self.date}"