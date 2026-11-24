# Pull request pipeline

`.github/workflows/pr.yml` runs on every PR. I use a throwaway branch to show it going green (or red).

From `shoplite-app`:

```bash
git checkout main
git pull
git checkout -b test/pr-workflow
```

Make a tiny change if you need a commit (whitespace in a comment is enough), then:

```bash
git add -p
git commit -m "Test PR workflow"
git push -u origin test/pr-workflow
```

Open the PR on GitHub against `main`. Actions → **Pull Request**.

What that workflow does:

- Hadolint on the three Dockerfiles
- `helm lint` / `helm template` on `helm/shoplite`
- yamllint
- `terraform fmt -check`
- catalog-api pytest
- Trivy / image bits if they are in that file

Fix whatever fails on the PR, push again. Same workflow, new run.

When you are done:

```bash
git checkout main
git branch -d test/pr-workflow
git push origin --delete test/pr-workflow
```

Image builds + GitOps tag bumps are **not** this workflow. Those are `web.yml` / `catalog-api.yml` / `order-worker.yml` on push to `main`. They need the `GITOPS_TOKEN` secret on shoplite-app (a PAT that can write `shoplite-gitops`).
