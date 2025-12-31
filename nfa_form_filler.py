#!/usr/bin/env python3
"""Legacy wrapper.

This file used to contain a standalone client that embedded credentials.
It now delegates to the maintained runner in run_rental_nfa_batch.py.
"""

from __future__ import annotations

import asyncio


async def main() -> None:
    from run_rental_nfa_batch import main as run_main

    await run_main()


if __name__ == "__main__":
    asyncio.run(main())