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
    ├── roboecc.svg
    ├── kerv.svg
    ├── awesome-embodied-trustworthy-execution.svg
    ├── edge-moe.svg
    └── circuit-modules-compendium.svg
```

## First run

1. Commit all files to the default branch (`master`).
2. Open **Actions**.
3. Run **Update Featured Project Cards** → **Run workflow**.
4. Run **Update GitHub Overview Cards** → **Run workflow**.
5. Run **Generate Contribution Snake** → **Run workflow**.
6. Return to the repository. The generated SVG files will be committed automatically.

All three workflows also run once per day.

Featured-project titles longer than 32 characters are shortened with `...`
after the cards are generated.

The GitHub overview workflow fetches the live star count for
`syswonder/robonix` and adds it to the generated Total Stars value.

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
