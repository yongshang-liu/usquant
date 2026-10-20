# Viewing and editing the project on GitHub

The repository is private and accessible to its owner and explicitly invited collaborators.

- **Code:** browse source files. Start with README for setup and `docs/research.md` for platform and license comparisons.
- **Editing:** open a file and use the pencil button. Explain the change in the commit message. Prefer a new branch and a pull request to review differences.
- **Actions:** inspect automated checks for each push. Green indicates success; open failed jobs to read logs. CI uses a temporary MySQL service and does not connect to a trading account.
- **Issues:** record bugs, questions, and feature ideas.
- **Local workflow:** commit and push local changes to publish them to the repository. Pull remote changes before editing the local copy.

Never commit `.env`, databases, brokerage journals, or virtual environments. On a new computer, recreate local configuration and start the required services.
