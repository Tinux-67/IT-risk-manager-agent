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
from typing import Dict, List, Optional

import requests


# GitHub API base URL
GITHUB_API_URL = "https://api.github.com"


class GitHubIssuesCreator:
    """Class to create GitHub issues from a JSON template."""

    def __init__(self, repo: str, token: str, dry_run: bool = False):
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
        self.session.headers.update({
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        self.created_issues: List[Dict] = []
        self.skipped_issues: List[Dict] = []

    def _api_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Optional[Dict]:
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
                print(f"[DRY RUN] {method} {url}")
                if data:
                    print(f"  Data: {json.dumps(data, indent=2)}")
                return {"id": 0, "number": 0}  # Mock response for dry run

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
                print(f"❌ Rate limit exceeded or permission denied: {response.text}")
                return None
            elif response.status_code == 404:
                print(f"❌ Not found: {url}")
                return None
            else:
                print(f"❌ API Error {response.status_code}: {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None

    def get_repo_info(self) -> Optional[Dict]:
        """Get repository information."""
        endpoint = f"/repos/{self.repo}"
        return self._api_request("GET", endpoint)

    def get_or_create_label(self, label_name: str, color: str = "0075ca") -> Optional[Dict]:
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
        if response is None:
            return None

        # Check if label exists
        for label in response:
            if label["name"] == label_name:
                return label

        # Create new label
        if not self.dry_run:
            data = {
                "name": label_name,
                "color": color,
            }
            return self._api_request("POST", endpoint, data=data)
        return {"name": label_name, "color": color}

    def get_or_create_milestone(self, title: str, description: str = "") -> Optional[Dict]:
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
        if response is None:
            return None

        # Check if milestone exists
        for milestone in response:
            if milestone["title"] == title:
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
        labels: List[str],
        milestone_title: Optional[str] = None,
    ) -> Optional[Dict]:
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
            if label:
                label_objects.append(label["name"])

        # Get or create milestone
        milestone_number = None
        if milestone_title:
            milestone = self.get_or_create_milestone(milestone_title)
            if milestone:
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

        if issue:
            print(f"✅ Created issue: #{issue.get('number')} - {title}")
            self.created_issues.append(issue)
        else:
            print(f"❌ Failed to create issue: {title}")
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
        if columns is None:
            return False

        # Find the column by name
        target_column = None
        for column in columns:
            if column["name"] == column_name:
                target_column = column
                break

        if not target_column:
            print(f"❌ Column '{column_name}' not found in project")
            return False

        # Get the issue node ID
        issue_endpoint = f"/repos/{self.repo}/issues/{issue_number}"
        issue = self._api_request("GET", issue_endpoint, params={"fields": "id"})
        if issue is None:
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
            "contentId": issue["node_id"],
            "columnId": target_column["node_id"],
        }

        response = self._api_request(
            "POST",
            "/graphql",
            data={"query": graphql_query, "variables": variables},
        )

        if response and "errors" not in response:
            print(f"✅ Added issue #{issue_number} to project column '{column_name}'")
            return True
        else:
            print(f"❌ Failed to add issue to project: {response}")
            return False

    def get_project_id(self, project_name: str) -> Optional[int]:
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
        if response is None:
            return None

        for project in response:
            if project["name"] == project_name:
                return project["id"]

        return None

    def create_issues_from_template(self, template_path: str) -> None:
        """
        Create issues from a JSON template file.

        Args:
            template_path: Path to the JSON template file
        """
        # Load the template
        with open(template_path, "r", encoding="utf-8") as f:
            issues_template = json.load(f)

        print(f"📄 Loaded {len(issues_template)} issues from template")

        # Create issues
        for issue_data in issues_template:
            self.create_issue(
                title=issue_data["title"],
                body=issue_data["body"],
                labels=issue_data["labels"],
                milestone_title=issue_data.get("milestone"),
            )

        print(f"\n📊 Summary:")
        print(f"   ✅ Created: {len(self.created_issues)} issues")
        print(f"   ❌ Skipped: {len(self.skipped_issues)} issues")

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
            print(f"❌ Project '{project_name}' not found")
            print("   Creating issues without project board...")
            self.create_issues_from_template(template_path)
            return

        print(f"🎯 Found project: {project_name} (ID: {project_id})")

        # Create issues
        self.create_issues_from_template(template_path)

        # Add issues to project
        if self.created_issues:
            print(f"\n📋 Adding issues to project board...")
            for issue in self.created_issues:
                self.add_issue_to_project(
                    issue_number=issue["number"],
                    project_id=project_id,
                    column_name=column_name,
                )


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Create GitHub issues from a JSON template"
    )
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
        print(f"❌ Template file not found: {template_path}")
        sys.exit(1)

    # Initialize creator
    creator = GitHubIssuesCreator(
        repo=args.repo,
        token=args.token,
        dry_run=args.dry_run,
    )

    print(f"🚀 Starting GitHub Issues Creator")
    print(f"   Repository: {args.repo}")
    print(f"   Template: {template_path}")
    print(f"   Dry run: {args.dry_run}")
    if args.project:
        print(f"   Project: {args.project}")
        print(f"   Column: {args.column}")
    print()

    # Create issues
    if args.project:
        creator.create_issues_and_add_to_project(
            template_path=str(template_path),
            project_name=args.project,
            column_name=args.column,
        )
    else:
        creator.create_issues_from_template(str(template_path))

    print(f"\n✨ Done!")


if __name__ == "__main__":
    main()
