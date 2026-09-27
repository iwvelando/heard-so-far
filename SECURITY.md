# Security policy

Report vulnerabilities privately through GitHub's private vulnerability
reporting: open the repository's **Security** tab and choose **Report a
vulnerability**. Please do not open a public issue for a suspected vulnerability.

Relevant reports include a helper reading or writing outside its designated
directories, cleanup deleting data it should preserve, transcription or the
journal exposing audio or prose beyond the saved listening limit, private files
passing the public-file check, and setup or reading commands making unexpected
network requests.

Spoiler limits in AGENTS.md are instructions to an agent, not an access-control
boundary; see [the configuration notes](companion/LOCAL_ONLY.md). An agent that
ignores those instructions is a protocol problem better reported as an issue,
unless a helper script itself permits it.

Never include audiobook audio, transcripts, journal answers, publisher metadata,
personal paths, or credentials in a report. Use synthetic timestamps and invented
passages to reproduce the problem.
