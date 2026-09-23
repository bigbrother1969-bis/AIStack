"""
Package Manager — the receiving dock for Governance Proposals.

`ARCH-0013-Knowledge-Package-Architecture` names a PackageManager: the
role that receives something, inspects it, and orchestrates validation
and integration before anything reaches the governed heritage.

What this package receives is a **Governance Proposal** (`FDN-0002`):
a proposed change to the governed heritage, validated before it
becomes governed knowledge. It is not a KnowledgePackage. `FDN-0002`
states that the Context Bundle *is* the Knowledge Package of AIStack
(decided 2026-08-29 by the owner); receiving one is `ARCH-0013`'s
package lifecycle, and nothing here builds it.

`ARCH-0009-Library-Architecture-Analogy` names the role this package
plays: the Logistics department (`TransportService`) that receives a
delivery, extended on arrival by what an Acquisition department
(`KnowledgeService`) does in a real library — check the delivery
against the existing catalogue before it is shelved.

*Named `KnowledgePackage` from 2026-09-23 (`87febe3`) until the owner's
decision of the same day, `GOV-0002/OS-060`: a set of proposed
documentation edits is not a Knowledge Package, and calling it one gave
the concept a fourth declaration.*
"""
