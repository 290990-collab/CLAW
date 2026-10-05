# Coding standards

How code is structured, independently of the language, plus the block for this project's stack. The conventions of form — names, commits, comments — live in `conventions.md`.

## Functions

- **One level of abstraction per function:** if it alternates low-level details and high-level decisions, it is two functions.
- **Few nested conditions:** returning early on degenerate cases leaves the main path flat.
- **Boolean arguments that change behaviour** are two functions disguised as one.
- **Returning a value *and* modifying observable state:** separate them where possible.
- **"Not found" and "not applicable"** are explicit cases of the return value, never an ambiguous special value.
- **States as a closed set:** a type with only the possible cases, exhaustiveness checked by the compiler where the language allows it; never combinable flags that yield impossible states.

## State and mutability

- Immutable by default; mutable only where needed and in a narrow scope.
- **No mutable global state:** it makes tests order-dependent and defects irreproducible.
- No data structure left in an invalid intermediate state, not even temporarily, if someone else can observe it.

## Errors

- **Expected error:** part of the contract, in the return type or in the declared exception. **Unexpected error:** it propagates.
- **You catch only what you know how to handle:** catching everything and carrying on turns a fault into silent corruption.
- **Context on the way up:** which operation, on which datum — never the secret or the personal datum.
- **Resource cleanup guaranteed on the error path too**, with the construct the language provides.
- **Mandatory configuration validated at startup:** if it is missing or invalid the program does not start, instead of finding out at the first request.

## Dependencies

- Every dependency is a permanent cost — maintenance, security, updates: for a few lines of code, you write the lines.
- External dependencies are isolated behind a project boundary: replacing them must touch a single point.
- **Adoption criteria:** active maintenance, verifiable publisher, compatibility with the project's versions. One is missing, it does not get in.
- **No installation without the user's explicit confirmation.**

## Concurrency

- Share as little as possible; where you share, an explicit and documented access protocol.
- No assumption about execution order that is not guaranteed.
- Every wait has a time limit; every retry has a maximum.
- **State read before a wait is re-checked after it:** in the meantime it may have changed or no longer exist.
- **The external call goes last:** preconditions → internal state → external call, and never inside an open transaction.

## Readability

- New code imitates the file it lives in: consistency before preferences.
- Automatic formatting where a tool exists: it is not argued by hand.
- **The only complexity allowed is the problem's:** a function hard to read on an easy problem is a wrong function.

## In this project

[TO FILL IN — languages and versions, formatting and static analysis tools with
their commands, stack-specific conventions, patterns adopted and patterns
explicitly discarded, runtime constraints that limit what can be used.]
