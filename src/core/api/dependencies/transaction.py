from collections.abc import AsyncGenerator, Callable
from typing import Annotated

from fastapi import Depends

from src.core.db import Transaction


def get_transaction_factory() -> Callable[[], AsyncGenerator[Transaction]]:
    async def _get_transaction() -> AsyncGenerator[Transaction]:
        async with Transaction() as transaction:
            yield transaction

    return _get_transaction


TransactionDependency = Annotated[Transaction, Depends(get_transaction_factory())]
