# Setup

Upload these files into your profile repository `zhengzihaoPKU/zhengzihaoPKU`:

```text
README.md
.github/workflows/featured-projects.yml
.github/workflows/github-overview.yml
.github/workflows/snake.yml
```

The workflows will create these generated files automatically:

```text
profile/
├── github-stats.svg
├── top-langs.svg
└── projects/
    ├── robonix.svg
    ├── kerv.svg
    ├── roboecc.svg
    └── edge-moe.svg
```

## First run

1. Commit all files to the default branch (`master`).
2. Open **Actions**.
3. Run **Update Featured Project Cards** → **Run workflow**.
4. Run **Update GitHub Overview Cards** → **Run workflow**.
5. Run **Generate Contribution Snake** → **Run workflow**.
6. Return to the repository. The generated SVG files will be committed automatically.

All three workflows also run once per day.

## If push is denied

Open:

**Settings → Actions → General → Workflow permissions**

and enable **Read and write permissions**.

The workflow files already declare:

```yaml
permissions:
  contents: write
```

so in most repositories no additional token is needed.
