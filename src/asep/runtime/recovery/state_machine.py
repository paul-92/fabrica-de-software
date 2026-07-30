"""Máquina de estados independente para execuções supervisionadas."""

from asep.runtime.recovery.exceptions import InvalidStateTransitionError
from asep.runtime.recovery.models import SupervisedExecutionState

TRANSITIONS = {
    SupervisedExecutionState.PENDING: {
        SupervisedExecutionState.PLANNING,
        SupervisedExecutionState.READY,
        SupervisedExecutionState.CANCELLED,
    },
    SupervisedExecutionState.PLANNING: {
        SupervisedExecutionState.READY,
        SupervisedExecutionState.FAILED,
        SupervisedExecutionState.CANCELLED,
    },
    SupervisedExecutionState.READY: {
        SupervisedExecutionState.RUNNING,
        SupervisedExecutionState.CANCELLED,
    },
    SupervisedExecutionState.RUNNING: {
        SupervisedExecutionState.RETRYING,
        SupervisedExecutionState.RECOVERING,
        SupervisedExecutionState.SUCCEEDED,
        SupervisedExecutionState.FAILED,
        SupervisedExecutionState.CANCELLED,
    },
    SupervisedExecutionState.RETRYING: {
        SupervisedExecutionState.RUNNING,
        SupervisedExecutionState.RECOVERING,
        SupervisedExecutionState.FAILED,
        SupervisedExecutionState.CANCELLED,
    },
    SupervisedExecutionState.RECOVERING: {
        SupervisedExecutionState.RUNNING,
        SupervisedExecutionState.SUCCEEDED,
        SupervisedExecutionState.FAILED,
        SupervisedExecutionState.ROLLED_BACK,
        SupervisedExecutionState.CANCELLED,
    },
    SupervisedExecutionState.SUCCEEDED: set(),
    SupervisedExecutionState.FAILED: set(),
    SupervisedExecutionState.CANCELLED: set(),
    SupervisedExecutionState.ROLLED_BACK: set(),
}


class ExecutionStateMachine:
    def __init__(
        self,
        initial: SupervisedExecutionState = (
            SupervisedExecutionState.PENDING
        ),
    ) -> None:
        self._state = initial
        self._history = [initial]

    @property
    def state(self) -> SupervisedExecutionState:
        return self._state

    @property
    def history(self) -> tuple[SupervisedExecutionState, ...]:
        return tuple(self._history)

    def transition(
        self, target: SupervisedExecutionState
    ) -> SupervisedExecutionState:
        if target not in TRANSITIONS[self._state]:
            raise InvalidStateTransitionError(
                f"Transição inválida: {self._state} -> {target}."
            )
        self._state = target
        self._history.append(target)
        return target


__all__ = ["ExecutionStateMachine", "TRANSITIONS"]
