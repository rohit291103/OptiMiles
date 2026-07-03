"""User-layer reads + ALL database writes, owned by the orchestrator.
Engines stay pure — that is what makes them fixture-testable. Catalog reads
live in knowledge/, not here."""
