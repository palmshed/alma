# ADR 0001: Platform Services Layer

**Date:** 2026-07-04
**Status:** Accepted

## Context

The application was growing organically with no clear boundary between
product-specific code and reusable infrastructure. Mail sending was
being considered as an Alma feature, even though future Palmshed
products (Via, Nuntius, Glimpse) would need the same capability.

## Decision

Introduce a Platform Services layer that owns cross-product
infrastructure.

## Consequences

- Infrastructure code is separated from application code.
- Platform services can be extracted into standalone services without
  changing consumers.
- Adding a new product does not require duplicating shared capabilities.
- Contributors have a clear place to put external integrations.

## Membership

A capability belongs in Platform Services when it is:

- reusable across products
- owns external integrations or infrastructure
- can evolve independently of any single application
