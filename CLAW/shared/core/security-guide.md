# Security guide

How to write code that is reachable by someone who should not use it. Sections in order of severity.

## Untrusted input

- **External data never becomes an instruction:** parameterised queries, commands with separate arguments and never built from a string, markup escaped for its context, no deserialisation, templating or runtime evaluation of external input.
- **Paths confined to the expected root,** checked after resolving `../` and links, not before.
- **Validation at the boundary, by allowlist:** type, shape, size. What is not allowed is rejected, not cleaned up.

## Secrets

- **Never in code, logs, errors, build artefacts or variables exposed to the client:** they come from the environment or from a secrets manager.
- **A committed secret is compromised even after removal:** it is rotated.

## Authentication and authorisation

- **Checked server-side, on every path that leads to the same data:** a check only in the client, or at one point and not at another, equals none.
- **Authorisation per object:** being authenticated does not authorise reading another user's id.
- **A header set by the client is not an identity:** a forwarded address, a role or an id declared by the request do not count; the authenticated identity or the connection's real address does.
- **Fail-closed:** a check that is unreachable or in error → the action is denied, never a fallback without the check.
- **Verify the check is active:** read the outcome of whatever sets limits, policies, permissions; a silent failure leaves zero checks.
- **Audit refusals too:** denied attempts, permission changes and decisions are recorded like successful operations, without secrets or personal data.

## Data exposure

- **Only listed fields go out,** never the whole internal object serialised.
- **Errors towards the outside are generic,** the detail goes to the internal log.
- **Least privilege** on files, roles, tokens.

## Trust boundaries

- **Requests to user-supplied URLs and redirects:** only towards destinations on an allowlist.
- **External resources and runtime code:** never loaded without an allowlist and an integrity check.

## Resources

- **Every external input has a limit:** size, number of elements, recursion depth, decompression factor.
- **No regular expression with exponential backtracking on external input;** a user-supplied pattern has a time limit.

## Dependencies

- **A new package only if necessary,** with the adoption criteria of `coding-standards.md`; no version with known vulnerabilities.
- **Exact version, never a range, for whatever handles keys or tokens,** with verified integrity.

## In this project

[TO FILL IN — the stack's safe constructs for queries, commands, markup and
serialisation; where secrets are read from; the authorisation scheme adopted;
what the audit records and where.]
