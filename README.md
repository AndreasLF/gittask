# GitTask ⚡️

**Seamlessly integrate your Git workflow with Asana.**
Track time, manage tasks, and link your development work directly to Asana without leaving your terminal.

## 🚀 A Day in the Life with GitTask

Imagine this: You grab your coffee ☕ and sit down to tackle a new feature.

1.  **Start Working**: `gt checkout -b feature/login-page`
    *   You create a branch, and *boom*, GitTask asks if you want to create a corresponding Asana task. You say yes, add some tags, and you're off! Time tracking starts automatically. ⏱️

2.  **Code & Chill**: You code away. Need a lunch break? Just `gt stop` (or switch branches). When you're back, `gt start` resumes the timer. No more guessing how long you worked!

3.  **Ship It**: `gt push`
    *   Your code goes up, and GitTask posts a neat summary of your commits directly to the Asana task. Your PM loves you. 💖

4.  **Review Time**: `gt pr create`
    *   Opens a PR on GitHub and links it to your Asana task instantly.

5.  **The Grand Finale**: `gt finish`
    *   The feature is approved. This command stops the timer, syncs your actual time to Asana, merges the PR, closes the Asana task, and even deletes your local branch. It's like magic. ✨

## 🛠️ Setup Guide

### 1. Installation

```bash
pip install gittask-cli
```

### 2. Authentication

#### 🟣 Asana Setup
1.  Go to the [Asana Developer Console](https://app.asana.com/0/my-apps) -> **"+ New access token"**.
2.  Name it "GitTask CLI" and copy the token.
3.  Run:
    ```bash
    gittask auth login
    ```

#### 🐙 GitHub Setup (Optional)
Required for Pull Request features.
1.  Go to [GitHub Tokens](https://github.com/settings/tokens?type=beta) -> **"Generate new token"**.
2.  Select **"All repositories"** (or specific ones).
3.  **Permissions**: Read/Write for `Contents` and `Pull requests`.
4.  Run:
    ```bash
    gittask auth login --github
    ```

### 3. Initialization
Select your default workspace and project:
```bash
gittask init
```

## 📖 Command Reference

### 🔄 Core Workflow

| Command | Description |
| :--- | :--- |
| `gt checkout -b <branch>` | **Start here.** Creates a branch, links/creates an Asana task, and starts the timer. |
| `gt track` | Track time on an Asana task without linking to a branch (e.g., meetings, code reviews). |
| `gt status` | Shows current branch, task, and session duration. |
| `gt finish` | **The magic command.** Stops timer, syncs time, merges PR, closes task, and deletes branch. |

### ⏱️ Time Management

| Command | Description |
| :--- | :--- |
| `gt stop` | Pause the timer (e.g., lunch break). |
| `gt start` | Resume the timer. |
| `gt sync` | Push local time logs to Asana. |

### 🐙 Git & Collaboration

| Command | Description |
| :--- | :--- |
| `gt commit -m "msg"` | Commits changes. |
| `gt push` | Pushes to remote and posts a summary comment on the Asana task. |
| `gt pr create` | Creates a GitHub PR linked to the Asana task. |
| `gt pr list` | Lists open PRs. |

### 🏷️ Task Extras

| Command | Description |
| :--- | :--- |
| `gt tags add` | Add tags to the current task. |
| `gt tags list` | View tags on the current task. |

### 🖥️ GUI (Experimental)

| Command | Description |
| :--- | :--- |
| `gt gui` | Launch the terminal-based graphical interface for visual task management. |

---
*Happy Coding!* 🚀
