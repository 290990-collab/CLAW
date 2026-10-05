# Architecture guide

Boundaries, contracts and the direction of dependencies. Reference material for whoever designs or reviews a structural change.

## Boundaries

A well-placed boundary answers three questions without opening the code: **what this unit does, how it is used, what it depends on.** If you have to read the implementation, it is not a boundary.

Signs that a boundary is missing or in the wrong place:

- a file that grows and that you cannot describe in one sentence;
- two units always changed together;
- a unit that knows how another is built internally;
- an internal change that breaks its users;
- the same concept represented differently in two places.

**What changes together stays together:** you divide by responsibility, never by technical category. Separating by "kind of file" produces units that can neither be understood nor changed on their own.

## Direction of dependencies

- **Domain logic does not know what surrounds it** — interface, database, transport format, external provider. They depend on it.
- **Practical test:** the logic can be exercised without starting anything. If testing a rule needs a server, a browser or a connection, the rule is coupled to a detail.
- **Inversion:** where the natural direction would be wrong, the interface is defined by the side that uses it, not by the side that implements it.

## Contracts

Contract = everything someone else relies on: public signatures, persisted formats, protocols, schemas, key names, URLs, error codes, and **observable behaviours** even undocumented ones.

Before changing one:

1. What is the contract, exactly?
2. Who uses it? Search everywhere, including what the compiler does not see.
3. Am I breaking compatibility or observable behaviour?
4. If so: migration? new version? a period in which both work?

A contract changed silently is a fault deferred to when nobody will remember why.

## Deferred decisions

A choice not yet made — which provider, format, source — is kept **behind an interface** instead of guessed: it costs one level of indirection, and when the decision comes it touches a single point. This holds only for decisions that are **really open**: abstracting what will never change is pure complexity.

## State

Less shared state, fewer ways to be inconsistent. Where it is needed: **one single source of truth**, the other copies avowedly derived and rebuildable. Two points that can diverge will diverge.

## In this project

[TO FILL IN — map of the modules with the responsibility of each, the
boundaries that must not be crossed, the declared contracts and who consumes
them, the decisions deliberately deferred and what keeps them open, the
architectural choices already made that are not reopened without a mandate.]
