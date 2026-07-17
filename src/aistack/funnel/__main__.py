from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import FunnelError, decapsulate, encapsulate, inspect


def _read_bytes(path: str | None) -> bytes:
    return Path(path).read_bytes() if path else sys.stdin.buffer.read()


def _read_text(path: str | None) -> str:
    return Path(path).read_text(encoding="ascii") if path else sys.stdin.read()


def _write_bytes(data: bytes, path: str | None) -> None:
    if path:
        Path(path).write_bytes(data)
    else:
        sys.stdout.buffer.write(data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aistack-funnel",
        description="Transport bytes through an integrity-checked ASCII envelope.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    pack = sub.add_parser("pack", help="encapsulate bytes")
    pack.add_argument("-i", "--input")
    pack.add_argument("-o", "--output")

    unpack = sub.add_parser("unpack", help="decapsulate and verify bytes")
    unpack.add_argument("-i", "--input")
    unpack.add_argument("-o", "--output")

    verify = sub.add_parser("verify", help="verify an envelope without extracting it")
    verify.add_argument("-i", "--input")

    version = sub.add_parser("version", help="show Funnel version")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "pack":
            envelope = encapsulate(_read_bytes(args.input))
            if args.output:
                Path(args.output).write_text(envelope, encoding="ascii")
            else:
                sys.stdout.write(envelope)
            return 0

        if args.command == "version":
            print("Encapsulated Funnel")
            print("Version : 1.0")
            print("API     : 1")
            print("Status  : OK")
            return 0

        envelope = _read_text(args.input)

        if args.command == "unpack":
            _write_bytes(decapsulate(envelope), args.output)
            return 0

        metadata = inspect(envelope)
        print(f"OK length={metadata.length} sha256={metadata.sha256}")
        return 0
    except (OSError, FunnelError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
