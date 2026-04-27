"""
EVM trace implementation that counts how many times each opcode is executed.
"""

from collections import defaultdict

from ethereum.trace import EvmTracer, OpStart, TraceEvent

from .protocols import Evm


class CountTracer(EvmTracer):
    """
    EVM trace implementation that counts how many times each opcode is
    executed.

    Counts from regular block transactions are kept separately from those
    produced by system transactions (e.g. EIP-4788 beacon root, EIP-2935
    history storage, EIP-7002 withdrawal requests, EIP-7251 consolidation
    requests). System-transaction counts are bucketed by target address so
    they do not pollute the regular per-block opcode totals.
    """

    active_traces: defaultdict[str, int]
    system_traces: dict[str, dict[str, int]]

    def __init__(self) -> None:
        self.active_traces = defaultdict(lambda: 0)
        self.system_traces = {}

    def __call__(self, evm: object, event: TraceEvent) -> None:
        """
        Create a trace of the event.
        """
        if not isinstance(event, OpStart):
            return

        assert isinstance(evm, Evm)

        if evm.message.tx_env.tx_hash is None:
            address_key = "0x" + bytes(evm.message.current_target).hex()
            bucket = self.system_traces.get(address_key)
            if bucket is None:
                bucket = defaultdict(lambda: 0)
                self.system_traces[address_key] = bucket
            bucket[event.op.name] += 1
        else:
            self.active_traces[event.op.name] += 1

    def results(self) -> dict[str, int]:
        """
        Return and clear the current opcode counts for regular transactions.
        """
        results = self.active_traces
        self.active_traces = defaultdict(lambda: 0)
        return results

    def system_results(self) -> dict[str, dict[str, int]]:
        """
        Return and clear the opcode counts collected from system
        transactions, keyed by the system contract's target address.
        """
        results = self.system_traces
        self.system_traces = {}
        return results
