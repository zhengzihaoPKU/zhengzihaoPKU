# Setup

Upload these files into your profile repository `zhengzihaoPKU/zhengzihaoPKU`:

```text
README.md
.github/workflows/featured-projects.yml
.github/workflows/github-overview.yml
.github/workflows/profile-views.yml
.github/workflows/snake.yml
scripts/update_profile_views.py
tests/test_profile_views.py
profile/profile-views.svg
```

The workflows will create or refresh these generated files automatically:

```text
profile/
├── github-stats.svg
├── profile-views.svg
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

1. Commit all files above, including the profile views script, tests, and initial SVG, to the default branch (`master`).
2. Open **Actions**.
3. Run **Update Featured Project Cards** → **Run workflow**.
4. Run **Update GitHub Overview Cards** → **Run workflow**.
5. Run **Generate Contribution Snake** → **Run workflow**.
6. Run **Update Profile Views Badge** → **Run workflow**.
7. Return to the repository. The generated SVG files will be committed automatically.

The featured-project, GitHub overview, and contribution snake workflows run every
five minutes. The profile views workflow runs hourly at minute 17 (UTC). GitHub
Actions may delay scheduled runs during periods of high load.

Featured-project titles longer than 32 characters are shortened with `...`
after the cards are generated.

The GitHub overview workflow fetches the live star count for
`syswonder/robonix` and adds it to the generated Total Stars value.

## Profile views

The visible **PROFILE VIEWS** badge uses `profile/profile-views.svg` from this
repository. It shows the last successfully fetched Komarev count in full, without
`K` abbreviation. A separate invisible Komarev pixel in `README.md` continues
recording profile image loads through GitHub's Camo image proxy.

The hourly workflow fetches the current count with a non-Camo user agent. In
[Komarev's current source](https://github.com/antonkomarev/github-profile-views-counter/blob/master/public/index.php),
only requests whose user agent starts with `github-camo` increment the counter,
so the updater's direct requests do not add views. This relies on the service
continuing to follow that implementation.

The updater validates the count before replacing the local SVG. If Komarev is
unavailable, returns an invalid response, or reports a count lower than the saved
count, the workflow fails and retains the last good badge. The number can
therefore lag behind the live counter. No new
secret is needed; the workflow uses the repository's automatic `GITHUB_TOKEN`
to commit changed SVG files.

This count estimates image loads, not unique visitors. GitHub's image caching
and Komarev availability affect which loads are recorded; visits missed during
an outage cannot be recovered by the updater.

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
