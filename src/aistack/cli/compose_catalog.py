from __future__ import annotations

from pathlib import Path

from aistack.catalog.compose import ComposeRuntimeCatalogBuilder
from aistack.generators.compose import ComposeCatalogArtifactGenerator
from aistack.kernel.bootstrap import create_kernel_context


def main() -> None:
    ctx = create_kernel_context()
    observation = ctx.providers.get("compose").collect()
    catalog = ComposeRuntimeCatalogBuilder().build(observation)

    output_path = ComposeCatalogArtifactGenerator().generate(
        catalog=catalog,
        output_path=Path("reports/generated/compose-runtime-catalog.json"),
    )

    print(f"Compose runtime catalog written to {output_path}")


if __name__ == "__main__":
    main()
