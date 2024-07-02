# Security Policy

## Supported Versions

As of April 2024 (and until this document is updated), only the v0.4.x releases of Flask-Tenants are supported for updates and bug fixes. Any previous versions are currently not supported and users are advised to use them "at their own risk".

## Reporting a Vulnerability

Please report (suspected) security vulnerabilities via GitHub's security advisory reporting system:
Submit your vulnerability via [this link](https://github.com/Flask-Tenants/flask-tenants/security/advisories/new)

Please note the following requirements (all are required):

- Summary of the suspected vulnerability
- Detailed information as to what the suspected vulnerability does and what it has access to
- Proof of Concept (Code samples at minimum, reproduction video optional)
  - POC must include how the vulnerability can actually access sensitive data
- Impact summary (who does this impact and how)

Optionally you may also add your estimated CVSS 3.1 score, though we may adjust. There is no need to submit a CVE request as we will do that as part of the advisory process.

You will receive a response from us within 72 hours. If the issue is confirmed, we will release a patch as soon as possible depending on complexity but historically within a few days.

Please note that we follow a very strict internal and public disclosure policy, typically a patch will be issued and included in a release. We then will place a warning that a security vulnerability has been patched and delay detailed disclosure from 2 to 8 weeks depending on the severity of the issue. If you have any resources such as blog posts that you intend to publish on and would like us to include these in our disclosure please advise us ASAP.

Before doing any public disclosure we do ask that you speak to us first to ensure we are not releasing too much information before a patch is available and time has been given to users to upgrade their projects.

## Security Process Summary

Below is a breakdown of our security process in order to set expectations:

- Initial submission of vulnerability via GitHub's Advisory system
- Begin internal tracking and communication to reporter
- Internal validation of vulnerability
- Internal notification and scheduling for patch development
- Begin development of patch
- Validation of patch (Internal and with the reporter)
- GitHub advisory cleanup
- Requesting of CVE via GitHub
- Disclosure and communication draft
- Patch released with initial warning via patch notes
- Mandatory waiting period (between 2 to 8 weeks)
- Publishing GitHub Advisory & CVE
- Public disclosure (via blog post)

## Other reporting platforms and bounties

Flask-Tenants does not support other reporting platforms, all security vulnerabilities must be made via GitHub Advisory system. If you are unable to report via this method you may open a security ticket with us by emailing security@flasktenants.com and we will create one on your behalf but if you do not have a GitHub user account we will not be able to share the private fork, pull request, or any other information with you during the process.

List of some (though not all) platforms **we do not support**:

- huntr.dev
- Direct email or communication to Flask Tenants contributors (Discord, Slack, or Email)
- Stack Overflow

**Flask Tenants does not currently and has no plans to offer any bug bounties, swag, or any other reward for reporting vulnerabilities.** At most during our public disclosure we can give credit to the reporter and link to any social accounts you wish to have us add including linking to your own blog post detailing the vulnerability if you wish.
