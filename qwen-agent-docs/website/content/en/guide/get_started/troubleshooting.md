# Troubleshooting

## `Publish to GitHub` reports that the branch update was rejected

If you are using the hosted Qwen Coder experience at `coder.qwen.ai`, the `Publish to GitHub` button can fail with an error similar to:

```text
The branch update was rejected by the remote server. Please verify the repository's status and ensure your GitHub credentials are correct and up to date.
```

This message means GitHub refused the branch update. It is usually caused by one of these repository states, rather than by Qwen-Agent's local Python package:

- The target branch already exists from an earlier publish attempt.
- A previous task created the branch but failed before opening or updating the pull request.
- The GitHub App or token no longer has write access to the repository.
- A branch protection rule, ruleset, or repository permission blocks force-pushes or direct updates.

When the failed publish left a stale remote branch behind, the practical meaning is: `Cannot push to an existing branch`. Remove or rename that branch, then try publishing again.

Try the following checks before starting a new task:

1. In GitHub, check the repository's **Branches** page for a stale branch created by the earlier Qwen Coder task. If it has no useful work, delete that branch and publish again.
2. Confirm that the GitHub App installation still has access to the repository and that the repository is selected in the app settings.
3. Review repository rulesets and branch protection settings for the branch name that Qwen Coder is trying to update.
4. If the workspace still has useful changes but publish keeps failing, ask Qwen Coder to show the current `git status`, `git branch --show-current`, and `git remote -v` output so you can identify the branch and recover the work manually.

Do not paste personal access tokens, SSH private keys, or other credentials into the chat. If you need a manual recovery path, prefer creating a temporary branch or using a GitHub deploy key with the minimum permissions needed, then remove it after the work is recovered.

If these checks do not resolve the problem, include the rejected branch name, repository ruleset details, and whether the branch already existed when reporting the issue.
