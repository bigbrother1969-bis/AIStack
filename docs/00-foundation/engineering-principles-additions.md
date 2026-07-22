## Technical Debt Is Contract Debt

### Principle

Technical debt is not primarily a property of the implementation.

It is primarily a property of the architectural contracts.

A governed architecture minimizes technical debt by ensuring that every concept is represented by a single, coherent, explicit and governed contract.

Implementations are expected to follow these contracts.

### Contract-Based Technical Debt

Technical debt is derived from violations of the contract architecture rather than from subjective code reviews.

Typical sources of technical debt include:

- Missing contracts
- Incorrect contracts
- Duplicated contracts
- Orphan contracts (no implementation)
- Orphan implementations (no governing contract)
- Contracts violating the Single Responsibility Principle
- Contracts describing obsolete or unused concepts

### Technical Debt Evaluation

Technical debt becomes measurable rather than subjective.

It can be evaluated from explicit architectural observations such as:

- Number of missing contracts
- Number of duplicated contracts
- Number of orphan contracts
- Number of orphan implementations
- Number of contract responsibility violations

The objective is not merely to reduce implementation complexity.

The objective is to maintain a coherent governed conceptual model.

### Engineering Consequence

In Governed Heritage Engineering, architecture quality is primarily determined by the quality of its contracts.

Well-designed contracts naturally lead to simple implementations.

Poor contracts inevitably generate technical debt, regardless of implementation quality.

Therefore, reducing technical debt consists first in improving the contract architecture rather than refactoring implementation details.


## Contract First Engineering

The primary deliverable of software engineering is not code.

It is a coherent, governed set of architectural contracts.

Once contracts are stable, implementations become largely mechanical.

Engineering effort should therefore focus primarily on discovering concepts, assigning responsibilities and designing contracts before writing implementation code.

This approach minimizes avoidable technical debt and naturally produces maintainable software.
