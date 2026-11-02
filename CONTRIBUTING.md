# Contributing

Run `python -m unittest discover -s tests -v`. Keep the core dependency-free and the adapter interface minimal. Add tests for policy denial, callback exceptions, malformed declarations, payload limits, adapter exceptions, and deterministic descriptors. Do not add real third-party adapters without reviewing their licenses, permissions, data handling, and threat model. Do not mark dependencies tested without reproducible integration evidence.
