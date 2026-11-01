# GitHub Activity Visualizer 📊

A Django & Django REST Framework (DRF) backend application designed to fetch, store, and serve GitHub user contribution statistics and daily activity calendars.

## 🚀 Features

- **GitHub Profile Tracking:** Stores usernames, total contribution counts, and last synchronization timestamps.
- **Daily Activity Logging:** Tracks daily contribution counts alongside GitHub-style activity levels (`NONE`, `FIRST_QUARTILE`, `SECOND_QUARTILE`, `THIRD_QUARTILE`, `FOURTH_QUARTILE`).
- **RESTful Endpoints Ready:** Includes serializers for nested representations of profiles and their daily contribution breakdown.

## 🛠️ Tech Stack

- **Language:** Python 3.14+
- **Framework:** Django
- **API Engine:** Django REST Framework (DRF)
- **Database:** SQLite (development)

## 📁 Project Structure

```text
github-activity-visualizer/
├── config/                 # Project configuration & settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── contributions/          # Core app for profile and contribution data
│   ├── models.py           # GitHubProfile & ContributionDay
│   ├── serializers.py      # REST serializers
│   └── views.py            # API views
├── manage.py
└── .gitignore