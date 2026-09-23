"""
Package Manager — the receiving dock for Knowledge Packages.

`ARCH-0013-Knowledge-Package-Architecture` documents a KnowledgePackage
lifecycle: Creation -> Transport -> Inspection -> Validation ->
Integration -> Archive. The Context Bundle Engine
(`aistack.context_bundle`, ADR-0005 to ADR-0007) already builds and
ships one kind of package — the Context Bundle. This package is the
other end: it receives a package, checks it against the governed
heritage, and applies what passes validation.

`ARCH-0009-Library-Architecture-Analogy` names the role this package
plays without building it: the Logistics department (`TransportService`)
that receives a delivery, extended on arrival by what an Acquisition
department (`KnowledgeService`) does in a real library — check the
delivery against the existing catalogue before it is shelved.

A Context Bundle is a KnowledgePackage, not a PackageManager under
another name. It is what this package would receive, not what receives
it.
"""
