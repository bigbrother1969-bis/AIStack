"""A declaration a person changes goes through a transaction (`ADR-0027` § 11)."""

from aistack.declaration.change import DeclarationNotWritten, write_declaration

__all__ = ["DeclarationNotWritten", "write_declaration"]
