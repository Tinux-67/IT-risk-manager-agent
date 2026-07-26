# GitHub Issues Creator

A Python script to **automatically create GitHub Issues from a JSON template** and optionally add them to a Project Board.

## 📌 Features

- ✅ **Bulk Issue Creation**: Create multiple issues at once from a JSON template
- ✅ **Label Management**: Automatically creates labels if they don't exist
- ✅ **Milestone Management**: Automatically creates milestones if they don't exist
- ✅ **Project Board Integration**: Add issues to a GitHub Project Board (Kanban)
- ✅ **Dry Run Mode**: Test without making changes
- ✅ **Error Handling**: Graceful handling of API errors and rate limits

## 🚀 Usage

### **1. Install Dependencies**
```bash
pip install requests
```

### **2. Create a GitHub Personal Access Token**
1. Go to [GitHub Settings > Developer Settings > Personal Access Tokens](https://github.com/settings/tokens)
2. Click **"Generate new token"** (classic)
3. **Scopes:** Select `repo` and `project`
4. Click **"Generate token"** and copy it

### **3. Run the Script**

#### **Basic Usage (Create Issues Only)**
```bash
python scripts/create_github_issues.py \
    --repo Tinux-67/IT-risk-manager-agent \
    --token YOUR_GITHUB_TOKEN
```

#### **With Project Board Integration**
```bash
python scripts/create_github_issues.py \
    --repo Tinux-67/IT-risk-manager-agent \
    --token YOUR_GITHUB_TOKEN \
    --project "IT Risk Manager Agent - Refactoring & Optimizations" \
    --column "To do"
```

#### **Dry Run (Test Without Changes)**
```bash
python scripts/create_github_issues.py \
    --repo Tinux-67/IT-risk-manager-agent \
    --token YOUR_GITHUB_TOKEN \
    --dry-run
```

#### **Custom Template File**
```bash
python scripts/create_github_issues.py \
    --repo Tinux-67/IT-risk-manager-agent \
    --token YOUR_GITHUB_TOKEN \
    --template custom_issues.json
```

## 📁 Files

| File | Description |
|------|-------------|
| `create_github_issues.py` | Main script to create issues |
| `ISSUES_TEMPLATE.json` | Default template with 20 issues |

## 📝 JSON Template Format

The template file should be a JSON array of issue objects:

```json
[
  {
    "title": "Fix logging configuration",
    "body": "## Description\nThe logging configuration needs to be fixed.\n\n## Acceptance Criteria\n- [ ] Fix implemented\n- [ ] Tests pass",
    "labels": ["bug", "logging", "high-priority"],
    "milestone": "Milestone 1: Code Quality"
  }
]
```

### **Supported Fields**
- `title` (required): Issue title
- `body` (required): Issue description (markdown)
- `labels` (required): Array of label names
- `milestone` (optional): Milestone title

## 🎯 Example Workflow

### **1. Create a Project Board**
1. Go to your repository on GitHub
2. Click **"Projects"** tab
3. Click **"New project"** → Select **"Board"**
4. Name it: `IT Risk Manager Agent - Refactoring & Optimizations`
5. Add columns: `Backlog`, `To do`, `In Progress`, `Done`

### **2. Run the Script**
```bash
python scripts/create_github_issues.py \
    --repo Tinux-67/IT-risk-manager-agent \
    --token ghp_your_token_here \
    --project "IT Risk Manager Agent - Refactoring & Optimizations" \
    --column "To do"
```

### **3. Verify**
- Check your repository's **Issues** tab
- Check your **Project Board** to see the new issues

## 🔒 Security

### **Using Environment Variables (Recommended)**
Create a `.env` file in the `scripts/` directory:

```bash
# scripts/.env
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPO=Tinux-67/IT-risk-manager-agent
```

Then run:
```bash
# Load environment variables
set -a && source scripts/.env && set +a

python scripts/create_github_issues.py \
    --repo $GITHUB_REPO \
    --token $GITHUB_TOKEN \
    --project "IT Risk Manager Agent - Refactoring & Optimizations"
```

### **Or Use a .env File with python-dotenv**
Install python-dotenv:
```bash
pip install python-dotenv
```

Create `.env`:
```ini
# .env
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPO=Tinux-67/IT-risk-manager-agent
```

Modify the script to use dotenv (or create a wrapper):
```python
from dotenv import load_dotenv
import os

load_dotenv()

token = os.getenv("GITHUB_TOKEN")
repo = os.getenv("GITHUB_REPO", "Tinux-67/IT-risk-manager-agent")
```

## 🐛 Troubleshooting

### **Rate Limit Exceeded**
GitHub has rate limits for the API. If you hit the limit:
- Wait a few minutes and try again
- Use a Personal Access Token (higher rate limit)
- Check your rate limit status:
  ```bash
  curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit
  ```

### **Permission Denied**
Make sure your token has the required scopes:
- `repo` (for creating issues)
- `project` (for adding to project boards)

### **Project Not Found**
- Make sure the project name is **exactly** as it appears in GitHub
- Project boards are **case-sensitive**
- The project must exist in the **same repository**

### **Column Not Found**
- Check the exact column name in your project board
- Default columns are: `To do`, `In progress`, `Done`

## 📚 GitHub API Documentation

- [Issues API](https://docs.github.com/en/rest/issues/issues)
- [Projects API](https://docs.github.com/en/rest/projects/projects)
- [GraphQL API](https://docs.github.com/en/graphql)

## 🎨 Customization

### **Custom Labels**
You can define custom labels in your template. The script will:
1. Check if the label exists
2. Create it if it doesn't exist with a default color (`0075ca`)

To use custom colors, modify the `get_or_create_label` method:
```python
def get_or_create_label(self, label_name: str, color: str = "0075ca") -> Optional[Dict]:
    # Custom color mapping
    color_map = {
        "bug": "d73a4a",        # Red
        "enhancement": "0075ca", # Blue
        "documentation": "0075ca",
        "performance": "0075ca",
        "security": "d73a4a",     # Red
        "high-priority": "d73a4a",
        "medium-priority": "0075ca",
        "low-priority": "0075ca",
    }
    color = color_map.get(label_name, "0075ca")
    # ... rest of the method
```

### **Custom Milestones**
Milestones are created based on the `milestone` field in the template. You can customize the description:
```python
def get_or_create_milestone(self, title: str, description: str = "") -> Optional[Dict]:
    # Custom milestone descriptions
    milestone_descriptions = {
        "Milestone 1: Code Quality & Bugfixes": "Focus on code quality improvements and bug fixes",
        "Milestone 2: Performance Optimizations": "Improve performance for large datasets",
        # ... add more
    }
    description = milestone_descriptions.get(title, description)
    # ... rest of the method
```

## 🤝 Contributing

Feel free to:
- Report bugs or suggest improvements
- Add new features (e.g., auto-assign issues, add to multiple projects)
- Improve error handling

## 📄 License

This script is part of the **IT Risk Manager Agent** project and is licensed under the MIT License.
