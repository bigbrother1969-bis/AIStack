import importlib


def test_kernel_packages_exist() -> None:
    """
    The Kernel's package layout, asserted where the layout is
    the subject.

    `aistack.kernel.capabilities` was in this list until
    2026-08-29 and was removed with it. **The package held nine
    classes that could not be instantiated** — empty subclasses
    of an ABC with two abstract methods — and this assertion was
    the only thing that made its absence a failure.

    *An import that succeeds says a directory exists. It says
    nothing about what is in it, which is the distinction this
    heritage spent 2026-08-29 learning three times over:
    `issubclass` is true of a declaration, `import` is true of a
    directory, and neither is a claim about behaviour.*
    """

    assert importlib.import_module("aistack.kernel.engines")
    assert importlib.import_module("aistack.kernel.repositories")
