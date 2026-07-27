#!/usr/bin/env python3
"""
Script to automatically create GitHub Issues from a JSON template.
Uses the GitHub API to create issues in bulk and optionally add them to a project board.

Usage:
    python scripts/create_github_issues.py --repo Tinux-67/IT-risk-manager-agent --token YOUR_GITHUB_TOKEN

Requirements:
    - Python 3.11+
    - requests library (pip install requests)
    - A GitHub Personal Access Token with 'repo' and 'project' scopes
"""

import argparse
import json
import sys
from pathlib import Path

import requests

# GitHub API base URL
GITHUB_API_URL = "https://api.github.com"


class GitHubIssuesCreator:
    """Class to create GitHub issues from a JSON template."""

    def __init__(self, repo: str, token: str, dry_run: bool = False) -> None:
        """
        Initialize the GitHub Issues Creator.

        Args:
            repo: Repository in format 'owner/repo'
            token: GitHub Personal Access Token
            dry_run: If True, only print what would be done without making changes
        """
        self.repo = repo
        self.token = token
        self.dry_run = dry_run
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        self.created_issues: list[dict] = []
        self.skipped_issues: list[dict] = []

    def _api_request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict | list[dict] | None:
        """
        Make a request to the GitHub API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/repos/owner/repo/issues')
            data: Request body data
            params: Query parameters

        Returns:
            Response JSON or None if failed
        """
        url = f"{GITHUB_API_URL}{endpoint}"
        try:
            if self.dry_run:
                print(f"[DRY RUN] {method} {url}")  # noqa: T201
                if data:
                    print(f"  Data: {json.dumps(data, indent=2)}")  # noqa: T201
                # Return mock data for dry run
                if endpoint.endswith("/labels"):
                    return []  # Return empty list for labels in dry run
                elif endpoint.endswith("/milestones"):
                    return []  # Return empty list for milestones in dry run
                elif "/issues" in endpoint and method == "POST":
                    return {"id": 0, "number": 0, "node_id": ""}  # Mock issue
                return {"id": 0, "node_id": ""}

            response = self.session.request(
                method,
                url,
                json=data,
                params=params,
                timeout=30,
            )

            if response.status_code == 200 or response.status_code == 201:
                return response.json()
            elif response.status_code == 403:
                print(
                    f"\u274c Rate limit exceeded or permission denied: {response.text}"
                )  # noqa: T201
                return None
            elif response.status_code == 404:
                print(f"\u274c Not found: {url}")  # noqa: T201
                return None
            else:
                print(f"\u274c API Error {response.status_code}: {response.text}")  # noqa: T201
                return None
        except requests.exceptions.RequestException as e:
            print(f"\u274c Request failed: {e}")  # noqa: T201
            return None

    def get_repo_info(self) -> dict | None:
        """Get repository information."""
        endpoint = f"/repos/{self.repo}"
        return self._api_request("GET", endpoint)

    def get_or_create_label(self, label_name: str, color: str = "0075ca") -> dict | None:
        """
        Get an existing label or create a new one.

        Args:
            label_name: Name of the label
            color: Hex color code for the label

        Returns:
            Label data or None
        """
        # List existing labels
        endpoint = f"/repos/{self.repo}/labels"
        response = self._api_request("GET", endpoint)

        # Handle case where response is not a list (e.g., string or None)
        if response is None:
            return None
        if isinstance(response, str):
            print(
                f"\u26a0\ufe0f Unexpected response type for labels: {type(response)}"
            )  # noqa: T201
            return None

        # Ensure response is a list
        if not isinstance(response, list):
            print("\u26a0\ufe0f Unexpected response format for labels")  # noqa: T201
            return None

        # Check if label exists
        for label in response:
            if isinstance(label, dict) and label.get("name") == label_name:
                return label

        # Create new label
        if not self.dry_run:
            data = {
                "name": label_name,
                "color": color,
            }
            return self._api_request("POST", endpoint, data=data)
        return {"name": label_name, "color": color}

    def get_or_create_milestone(self, title: str, description: str = "") -> dict | None:
        """
        Get an existing milestone or create a new one.

        Args:
            title: Title of the milestone
            description: Description of the milestone

        Returns:
            Milestone data or None
        """
        endpoint = f"/repos/{self.repo}/milestones"
        response = self._api_request("GET", endpoint, params={"state": "all"})

        # Handle case where response is not a list
        if response is None:
            return None
        if isinstance(response, str):
            print(
                f"\u26a0\ufe0f Unexpected response type for milestones: {type(response)}"
            )  # noqa: T201
            return None
        if not isinstance(response, list):
            print("\u26a0\ufe0f Unexpected response format for milestones")  # noqa: T201
            return None

        # Check if milestone exists
        for milestone in response:
            if isinstance(milestone, dict) and milestone.get("title") == title:
                return milestone

        # Create new milestone
        if not self.dry_run:
            data = {
                "title": title,
                "description": description,
                "state": "open",
            }
            return self._api_request("POST", endpoint, data=data)
        return {"title": title, "number": 0}

    def create_issue(
        self,
        title: str,
        body: str,
        labels: list[str],
        milestone_title: str | None = None,
    ) -> dict | None:
        """
        Create a new GitHub issue.

        Args:
            title: Issue title
            body: Issue body (markdown)
            labels: List of label names
            milestone_title: Title of the milestone to assign

        Returns:
            Created issue data or None
        """
        # Get or create labels
        label_objects = []
        for label_name in labels:
            label = self.get_or_create_label(label_name)
            if label and isinstance(label, dict):
                label_objects.append(label["name"])

        # Get or create milestone
        milestone_number = None
        if milestone_title:
            milestone = self.get_or_create_milestone(milestone_title)
            if milestone and isinstance(milestone, dict):
                milestone_number = milestone.get("number")

        # Create issue data
        issue_data = {
            "title": title,
            "body": body,
            "labels": label_objects,
        }
        if milestone_number:
            issue_data["milestone"] = milestone_number

        # Create the issue
        endpoint = f"/repos/{self.repo}/issues"
        issue = self._api_request("POST", endpoint, data=issue_data)

        if issue and isinstance(issue, dict):
            print(f"\u2705 Created issue: #{issue.get('number')} - {title}")  # noqa: T201
            self.created_issues.append(issue)
        else:
            print(f"\u274c Failed to create issue: {title}")  # noqa: T201
            self.skipped_issues.append({"title": title, "error": "API failed"})

        return issue

    def add_issue_to_project(
        self,
        issue_number: int,
        project_id: int,
        column_name: str = "To do",
    ) -> bool:
        """
        Add an issue to a project board.

        Args:
            issue_number: The issue number
            project_id: The project ID
            column_name: The column name to add the issue to

        Returns:
            True if successful, False otherwise
        """
        # Get project columns
        endpoint = f"/projects/{project_id}/columns"
        columns = self._api_request("GET", endpoint)

        # Handle response
        if columns is None:
            return False
        if not isinstance(columns, list):
            print("\u26a0\ufe0f Unexpected response format for project columns")  # noqa: T201
            return False

        # Find the column by name
        target_column = None
        for column in columns:
            if isinstance(column, dict) and column.get("name") == column_name:
                target_column = column
                break

        if not target_column:
            print(f"\u274c Column '{column_name}' not found in project")  # noqa: T201
            return False

        # Get the issue node ID
        issue_endpoint = f"/repos/{self.repo}/issues/{issue_number}"
        issue = self._api_request("GET", issue_endpoint, params={"fields": "id"})
        if issue is None or not isinstance(issue, dict):
            return False

        # Add issue to column using GraphQL (more reliable for projects)
        graphql_query = """
        mutation AddProjectCard($projectId: ID!, $contentId: ID!, $columnId: ID!) {
            addProjectCard(input: {
                projectId: $projectId
                contentId: $contentId
                columnId: $columnId
            }) {
                cardEdge {
                    node {
                        id
                    }
                }
            }
        }
        """

        variables = {
            "projectId": project_id,
            "contentId": issue.get("node_id"),
            "columnId": target_column.get("node_id"),
        }

        response = self._api_request(
            "POST",
            "/graphql",
            data={"query": graphql_query, "variables": variables},
        )

        if response and isinstance(response, dict) and "errors" not in response:
            print(
                f"\u2705 Added issue #{issue_number} to project column '{column_name}'"
            )  # noqa: T201
            return True
        else:
            print(f"\u274c Failed to add issue to project: {response}")  # noqa: T201
            return False

    def get_project_id(self, project_name: str) -> int | None:
        """
        Get the project ID by name.

        Args:
            project_name: Name of the project

        Returns:
            Project ID or None
        """
        # Get all projects for the repository
        endpoint = f"/repos/{self.repo}/projects"
        response = self._api_request("GET", endpoint, params={"state": "all"})

        # Handle response
        if response is None:
            return None
        if not isinstance(response, list):
            print("\u26a0\ufe0f Unexpected response format for projects")  # noqa: T201
            return None

        for project in response:
            if isinstance(project, dict) and project.get("name") == project_name:
                return project.get("id")

        return None

    def create_issues_from_template(self, template_path: str) -> None:
        """
        Create issues from a JSON template file.

        Args:
            template_path: Path to the JSON template file
        """
        # Load the template
        with open(template_path, encoding="utf-8") as f:
            issues_template = json.load(f)

        print(f"\ud83d\udcc4 Loaded {len(issues_template)} issues from template")  # noqa: T201

        # Create issues
        for issue_data in issues_template:
            self.create_issue(
                title=issue_data["title"],
                body=issue_data["body"],
                labels=issue_data["labels"],
                milestone_title=issue_data.get("milestone"),
            )

        print("\n\ud83d\udcca Summary:")  # noqa: T201
        print(f"   \u2705 Created: {len(self.created_issues)} issues")  # noqa: T201
        print(f"   \u274c Skipped: {len(self.skipped_issues)} issues")  # noqa: T201

    def create_issues_and_add_to_project(
        self,
        template_path: str,
        project_name: str,
        column_name: str = "To do",
    ) -> None:
        """
        Create issues from template and add them to a project board.

        Args:
            template_path: Path to the JSON template file
            project_name: Name of the project board
            column_name: Column name to add issues to
        """
        # Get project ID
        project_id = self.get_project_id(project_name)
        if project_id is None:
            print(f"\u274c Project '{project_name}' not found")  # noqa: T201
            print("   Creating issues without project board...")  # noqa: T201
            self.create_issues_from_template(template_path)
            return

        print(f"\ud83c\udfaf Found project: {project_name} (ID: {project_id})")  # noqa: T201

        # Create issues
        self.create_issues_from_template(template_path)

        # Add issues to project
        if self.created_issues:
            print("\n\ud83d\udccb Adding issues to project board...")  # noqa: T201
            for issue in self.created_issues:
                if isinstance(issue, dict):
                    self.add_issue_to_project(
                        issue_number=issue.get("number", 0),
                        project_id=project_id,
                        column_name=column_name,
                    )


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Create GitHub issues from a JSON template")
    parser.add_argument(
        "--repo",
        type=str,
        required=True,
        help="Repository in format 'owner/repo' (e.g., 'Tinux-67/IT-risk-manager-agent')",
    )
    parser.add_argument(
        "--token",
        type=str,
        required=True,
        help="GitHub Personal Access Token with 'repo' and 'project' scopes",
    )
    parser.add_argument(
        "--template",
        type=str,
        default=".github/ISSUES_TEMPLATE.json",
        help="Path to the JSON template file (default: .github/ISSUES_TEMPLATE.json)",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Name of the project board to add issues to (optional)",
    )
    parser.add_argument(
        "--column",
        type=str,
        default="To do",
        help="Column name in the project board (default: 'To do')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be done without making changes",
    )
    args = parser.parse_args()

    # Check if template file exists
    template_path = Path(args.template)
    if not template_path.exists():
        print(f"\u274c Template file not found: {template_path}")  # noqa: T201
        sys.exit(1)

    # Initialize creator
    creator = GitHubIssuesCreator(
        repo=args.repo,
        token=args.token,
        dry_run=args.dry_run,
    )

    print("\ud83d\ude80 Starting GitHub Issues Creator")  # noqa: T201
    print(f"   Repository: {args.repo}")  # noqa: T201
    print(f"   Template: {template_path}")  # noqa: T201
    print(f"   Dry run: {args.dry_run}")  # noqa: T201
    if args.project:
        print(f"   Project: {args.project}")  # noqa: T201
        print(f"   Column: {args.column}")  # noqa: T201
    print()  # noqa: T201

    # Create issues
    if args.project:
        creator.create_issues_and_add_to_project(
            template_path=str(template_path),
            project_name=args.project,
            column_name=args.column,
        )
    else:
        creator.create_issues_from_template(str(template_path))

    print("\n\u2728 Done!")  # noqa: T201


if __name__ == "__main__":
    main()
