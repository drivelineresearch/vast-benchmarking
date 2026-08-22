# Public-release checklist

The current tree is structured for public review, but changing repository visibility is
an owner action. Before publication:

- Choose and add an open-source license. No license is selected by this repository.
- Review commit author names and email addresses in the complete Git history.
- Decide whether to rewrite historical commits containing former personal path defaults.
- Confirm GitHub secret scanning and push protection are enabled.
- Run CI and the Public safety workflow on the exact publication commit.
- Confirm `results/`, `.env`, private keys, SQLite files, and provider logs are absent.
- Confirm the live dashboard exposes only intended benchmark and marketplace metadata.

History rewriting changes commit IDs and requires a coordinated force-push, so it is not
part of normal release preparation.
