"""
State Machine for Manufacturing Operations.

Implements the state transitions and business rules for manufacturing
operations following industry best practices.
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OperationStatus(Enum):
    """Valid operation statuses in manufacturing workflow."""
    PLANNED = "PLANNED"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"


@dataclass
class StateTransition:
    """Represents a state transition with conditions and effects."""
    from_state: OperationStatus
    to_state: OperationStatus
    conditions: List[str]
    effects: List[str]
    requires_confirmation: bool = False


class OperationStateMachine:
    """
    State machine for manufacturing operation lifecycle.

    Manages valid state transitions, business rules, and automatic
    state updates based on manufacturing events.
    """

    def __init__(self):
        self._transitions = self._define_transitions()
        self._terminal_states = {OperationStatus.FINISHED, OperationStatus.CANCELLED}

    def _define_transitions(self) -> Dict[OperationStatus, List[StateTransition]]:
        """Define all valid state transitions with conditions."""
        return {
            OperationStatus.PLANNED: [
                StateTransition(
                    from_state=OperationStatus.PLANNED,
                    to_state=OperationStatus.RELEASED,
                    conditions=["has_required_materials", "machine_available"],
                    effects=["notify_operator", "reserve_capacity"]
                ),
                StateTransition(
                    from_state=OperationStatus.PLANNED,
                    to_state=OperationStatus.CANCELLED,
                    conditions=["authorized_cancellation"],
                    effects=["release_reservations", "update_schedule"],
                    requires_confirmation=True
                )
            ],

            OperationStatus.RELEASED: [
                StateTransition(
                    from_state=OperationStatus.RELEASED,
                    to_state=OperationStatus.IN_PROGRESS,
                    conditions=["operator_available", "setup_complete"],
                    effects=["start_time_tracking", "update_machine_status"]
                ),
                StateTransition(
                    from_state=OperationStatus.RELEASED,
                    to_state=OperationStatus.ON_HOLD,
                    conditions=["hold_reason_provided"],
                    effects=["pause_schedule", "notify_planning"]
                ),
                StateTransition(
                    from_state=OperationStatus.RELEASED,
                    to_state=OperationStatus.CANCELLED,
                    conditions=["authorized_cancellation"],
                    effects=["release_reservations", "update_schedule"],
                    requires_confirmation=True
                )
            ],

            OperationStatus.IN_PROGRESS: [
                StateTransition(
                    from_state=OperationStatus.IN_PROGRESS,
                    to_state=OperationStatus.FINISHED,
                    conditions=["quality_approved", "quantity_complete"],
                    effects=["calculate_actuals", "update_inventory", "release_capacity"]
                ),
                StateTransition(
                    from_state=OperationStatus.IN_PROGRESS,
                    to_state=OperationStatus.ON_HOLD,
                    conditions=["hold_reason_provided"],
                    effects=["pause_time_tracking", "notify_planning"]
                ),
                StateTransition(
                    from_state=OperationStatus.IN_PROGRESS,
                    to_state=OperationStatus.CANCELLED,
                    conditions=["authorized_cancellation", "work_stoppage_approved"],
                    effects=["handle_wip", "calculate_partial_actuals"],
                    requires_confirmation=True
                )
            ],

            OperationStatus.ON_HOLD: [
                StateTransition(
                    from_state=OperationStatus.ON_HOLD,
                    to_state=OperationStatus.IN_PROGRESS,
                    conditions=["hold_reason_resolved", "resources_available"],
                    effects=["resume_time_tracking", "update_machine_status"]
                ),
                StateTransition(
                    from_state=OperationStatus.ON_HOLD,
                    to_state=OperationStatus.CANCELLED,
                    conditions=["authorized_cancellation"],
                    effects=["handle_wip", "release_reservations"],
                    requires_confirmation=True
                )
            ],

            # Terminal states have no outgoing transitions
            OperationStatus.FINISHED: [],
            OperationStatus.CANCELLED: []
        }

    def can_transition(
        self,
        from_state: str,
        to_state: str,
        context: Dict = None
    ) -> bool:
        """
        Check if a state transition is valid.

        Args:
            from_state: Current operation status
            to_state: Desired operation status
            context: Additional context for condition checking

        Returns:
            True if transition is valid, False otherwise
        """
        try:
            from_status = OperationStatus(from_state)
            to_status = OperationStatus(to_state)
        except ValueError:
            logger.warning(f"Invalid status values: {from_state} -> {to_state}")
            return False

        if from_status == to_status:
            return True  # No transition needed

        valid_transitions = self._transitions.get(from_status, [])
        for transition in valid_transitions:
            if transition.to_state == to_status:
                return self._check_conditions(transition, context or {})

        return False

    def get_valid_transitions(self, current_state: str) -> List[str]:
        """Get all valid next states from the current state."""
        try:
            current_status = OperationStatus(current_state)
        except ValueError:
            return []

        transitions = self._transitions.get(current_status, [])
        return [t.to_state.value for t in transitions]

    def transition(
        self,
        from_state: str,
        to_state: str,
        context: Dict = None,
        user_id: str = None
    ) -> Dict:
        """
        Execute a state transition with all associated effects.

        Args:
            from_state: Current operation status
            to_state: Desired operation status
            context: Additional context for the transition
            user_id: User executing the transition

        Returns:
            Dictionary with transition results and effects

        Raises:
            ValueError: If transition is not valid
        """
        if not self.can_transition(from_state, to_state, context):
            raise ValueError(f"Invalid transition: {from_state} -> {to_state}")

        try:
            from_status = OperationStatus(from_state)
            to_status = OperationStatus(to_state)
        except ValueError as e:
            raise ValueError(f"Invalid status values: {e}")

        # Find the transition definition
        transition = None
        for t in self._transitions.get(from_status, []):
            if t.to_state == to_status:
                transition = t
                break

        if not transition:
            raise ValueError(f"Transition not found: {from_state} -> {to_state}")

        # Execute transition effects
        effects_executed = self._execute_effects(transition, context or {}, user_id)

        result = {
            "from_state": from_state,
            "to_state": to_state,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "effects_executed": effects_executed,
            "requires_confirmation": transition.requires_confirmation
        }

        logger.info(f"State transition executed: {from_state} -> {to_state}", extra=result)
        return result

    def is_terminal_state(self, state: str) -> bool:
        """Check if a state is terminal (no further transitions possible)."""
        try:
            status = OperationStatus(state)
            return status in self._terminal_states
        except ValueError:
            return False

    def get_state_description(self, state: str) -> str:
        """Get human-readable description of a state."""
        descriptions = {
            "PLANNED": "Operation is scheduled but not yet released for production",
            "RELEASED": "Operation is ready to start and resources are allocated",
            "IN_PROGRESS": "Operation is currently being executed",
            "ON_HOLD": "Operation is temporarily paused due to issues or constraints",
            "FINISHED": "Operation has been completed successfully",
            "CANCELLED": "Operation has been cancelled and will not be completed"
        }
        return descriptions.get(state, "Unknown state")

    def _check_conditions(self, transition: StateTransition, context: Dict) -> bool:
        """Check if all conditions for a transition are met."""
        # In a real implementation, this would check actual business conditions
        # For now, we'll implement basic checks that can be extended

        condition_checkers = {
            "has_required_materials": lambda ctx: ctx.get("materials_available", True),
            "machine_available": lambda ctx: ctx.get("machine_status") != "DOWN",
            "authorized_cancellation": lambda ctx: ctx.get("user_role") in ["supervisor", "manager"],
            "operator_available": lambda ctx: ctx.get("operator_assigned", True),
            "setup_complete": lambda ctx: ctx.get("setup_status") == "COMPLETE",
            "hold_reason_provided": lambda ctx: bool(ctx.get("hold_reason")),
            "quality_approved": lambda ctx: ctx.get("quality_status") == "APPROVED",
            "quantity_complete": lambda ctx: ctx.get("qty_processed", 0) >= ctx.get("qty_desired", 1),
            "hold_reason_resolved": lambda ctx: ctx.get("hold_resolved", False),
            "resources_available": lambda ctx: ctx.get("resources_ready", True),
            "work_stoppage_approved": lambda ctx: ctx.get("stoppage_approved", False)
        }

        for condition in transition.conditions:
            checker = condition_checkers.get(condition)
            if checker and not checker(context):
                logger.debug(f"Condition failed: {condition}")
                return False

        return True

    def _execute_effects(self, transition: StateTransition, context: Dict, user_id: str) -> List[str]:
        """Execute the effects of a state transition."""
        # In a real implementation, these would trigger actual business processes
        # For now, we'll log the effects and return what was executed

        executed = []
        for effect in transition.effects:
            try:
                self._execute_single_effect(effect, context, user_id)
                executed.append(effect)
                logger.debug(f"Effect executed: {effect}")
            except Exception as e:
                logger.error(f"Failed to execute effect {effect}: {str(e)}")

        return executed

    def _execute_single_effect(self, effect: str, context: Dict, user_id: str):
        """Execute a single effect - placeholder for actual implementations."""
        effect_handlers = {
            "notify_operator": lambda: logger.info("Operator notified"),
            "reserve_capacity": lambda: logger.info("Capacity reserved"),
            "release_reservations": lambda: logger.info("Reservations released"),
            "update_schedule": lambda: logger.info("Schedule updated"),
            "start_time_tracking": lambda: logger.info("Time tracking started"),
            "update_machine_status": lambda: logger.info("Machine status updated"),
            "pause_schedule": lambda: logger.info("Schedule paused"),
            "notify_planning": lambda: logger.info("Planning notified"),
            "calculate_actuals": lambda: logger.info("Actual times calculated"),
            "update_inventory": lambda: logger.info("Inventory updated"),
            "release_capacity": lambda: logger.info("Capacity released"),
            "pause_time_tracking": lambda: logger.info("Time tracking paused"),
            "handle_wip": lambda: logger.info("Work-in-progress handled"),
            "calculate_partial_actuals": lambda: logger.info("Partial actuals calculated"),
            "resume_time_tracking": lambda: logger.info("Time tracking resumed"),
        }

        handler = effect_handlers.get(effect)
        if handler:
            handler()
        else:
            logger.warning(f"Unknown effect: {effect}")