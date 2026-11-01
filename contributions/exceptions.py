class GitHubAPIException(Exception):
    """خطای پایه ارتباط با API گیت‌هاب"""
    default_message = "Failed to communicate with GitHub API."
    status_code = 502

    def __init__(self, message=None):
        super().__init__(message or self.default_message)

class GitHubRateLimitException(GitHubAPIException):
    default_message = "GitHub API rate limit exceeded. Please try again later."
    status_code = 429

class GitHubUserNotFoundException(GitHubAPIException):
    default_message = "GitHub user was not found."
    status_code = 404

class GitHubAuthException(GitHubAPIException):
    default_message = "Invalid or expired GitHub authentication token."
    status_code = 401