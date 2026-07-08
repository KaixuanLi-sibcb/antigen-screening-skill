# Input Type: Gene List

Treat a gene list as candidate discovery only. Require protein feature evidence before antigen eligibility calls.

Minimum handling:

- preserve original symbol
- normalize species
- mark disease relevance as `uncertain` unless context or user evidence is provided
- do not infer surface localization from symbol alone
