"""
Manufacturing Business Rules Engine.

Implements manufacturing-specific business rules and validations
that go beyond basic data constraints.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from app.models.mes_operation import MESOperation
from app.exceptions.mes_exceptions import InvalidQuantityException, InvalidOperationStateException

logger = logging.getLogger(__name__)


class ManufacturingRules:
    """
    Encapsulates manufacturing business rules and validations.

    This class contains industry-specific rules for manufacturing
    operations that ensure data integrity and business logic compliance.
    """

    # Manufacturing constants
    MAX_EFFICIENCY_THRESHOLD = Decimal('2.5')  # 250% efficiency cap
    MIN_PROCESSING_TIME_MINUTES = Decimal('0.1')  # Minimum meaningful processing time
    MAX_DAILY_CAPACITY_HOURS = Decimal('24')  # Maximum hours per day
    SCRAP_RATE_WARNING_THRESHOLD = Decimal('0.05')  # 5% scrap rate warning

    def __init__(self):
        self.validation_rules = self._initialize_validation_rules()

    def validate_operation_data(self, operation_data: Dict[str, Any]) -> List[str]:
        """
        Validate operation data against manufacturing business rules.

        Args:
            operation_data: Dictionary containing operation fields

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        for rule_name, rule_func in self.validation_rules.items():
            try:
                rule_errors = rule_func(operation_data)
                if rule_errors:
                    errors.extend(rule_errors)
            except Exception as e:
                logger.error(f"Error in validation rule {rule_name}: {str(e)}")
                errors.append(f"Validation error in rule {rule_name}")

        return errors

    def validate_quantity_relationships(self, operation_data: Dict[str, Any]) -> List[str]:
        """Validate quantity relationships follow manufacturing logic."""
        errors = []

        qty_desired = operation_data.get('qty_desired')
        qty_processed = operation_data.get('qty_processed')
        qty_scrap = operation_data.get('qty_scrap')

        if qty_desired is not None and qty_desired <= 0:
            errors.append("Desired quantity must be positive")

        if qty_processed is not None and qty_processed < 0:
            errors.append("Processed quantity cannot be negative")

        if qty_scrap is not None and qty_scrap < 0:
            errors.append("Scrap quantity cannot be negative")

        # Processed quantity validation
        if qty_desired and qty_processed and qty_processed > qty_desired:
            errors.append(f"Processed quantity ({qty_processed}) cannot exceed desired quantity ({qty_desired})")

        # Scrap quantity validation
        if qty_processed and qty_scrap and qty_scrap > qty_processed:
            errors.append(f"Scrap quantity ({qty_scrap}) cannot exceed processed quantity ({qty_processed})")

        # Scrap rate warning
        if qty_processed and qty_scrap and qty_processed > 0:
            scrap_rate = Decimal(str(qty_scrap)) / Decimal(str(qty_processed))
            if scrap_rate > self.SCRAP_RATE_WARNING_THRESHOLD:
                logger.warning(f"High scrap rate detected: {scrap_rate:.2%}")

        return errors

    def validate_time_relationships(self, operation_data: Dict[str, Any]) -> List[str]:
        """Validate time relationships and constraints."""
        errors = []

        # Planned times validation
        planned_start = operation_data.get('planned_start_at')
        planned_end = operation_data.get('planned_end_at')

        if planned_start and planned_end:
            if planned_start >= planned_end:
                errors.append("Planned start time must be before planned end time")

            # Check for reasonable duration
            duration = planned_end - planned_start
            if duration > timedelta(days=30):
                errors.append("Planned duration exceeds 30 days - please verify")

        # Actual times validation
        actual_start = operation_data.get('actual_start_at')
        actual_end = operation_data.get('actual_end_at')

        if actual_start and actual_end:
            if actual_start >= actual_end:
                errors.append("Actual start time must be before actual end time")

        # Time component validation
        t_target_processing = operation_data.get('t_target_processing_min')
        t_target_setup = operation_data.get('t_target_setup_min')
        t_target_lead = operation_data.get('t_target_lead_min')

        t_actual_processing = operation_data.get('t_actual_processing_min')
        t_actual_setup = operation_data.get('t_actual_setup_min')
        t_actual_lead = operation_data.get('t_actual_lead_min')

        # Validate positive time values
        time_fields = [
            ('t_target_processing_min', t_target_processing),
            ('t_target_setup_min', t_target_setup),
            ('t_target_lead_min', t_target_lead),
            ('t_actual_processing_min', t_actual_processing),
            ('t_actual_setup_min', t_actual_setup),
            ('t_actual_lead_min', t_actual_lead)
        ]

        for field_name, value in time_fields:
            if value is not None:
                if value < 0:
                    errors.append(f"{field_name} cannot be negative")
                elif value < self.MIN_PROCESSING_TIME_MINUTES and value > 0:
                    errors.append(f"{field_name} is too small to be meaningful")

        # Lead time should include processing and setup time
        if (t_target_processing and t_target_setup and t_target_lead and
            t_target_lead < (t_target_processing + t_target_setup)):
            errors.append("Target lead time should be at least the sum of processing and setup times")

        # Efficiency validation
        if t_target_processing and t_actual_processing and t_actual_processing > 0:
            efficiency = t_target_processing / t_actual_processing
            if efficiency > self.MAX_EFFICIENCY_THRESHOLD:
                logger.warning(f"Unusually high efficiency: {efficiency:.2f}")

        return errors

    def validate_status_constraints(self, operation_data: Dict[str, Any]) -> List[str]:
        """Validate status-specific constraints."""
        errors = []

        status = operation_data.get('status')
        qty_processed = operation_data.get('qty_processed')
        actual_start = operation_data.get('actual_start_at')
        actual_end = operation_data.get('actual_end_at')

        if status == 'IN_PROGRESS':
            if not actual_start:
                errors.append("Operations in progress must have an actual start time")

        elif status == 'FINISHED':
            if not actual_start:
                errors.append("Finished operations must have an actual start time")
            if not actual_end:
                errors.append("Finished operations must have an actual end time")
            if not qty_processed:
                errors.append("Finished operations must have processed quantity > 0")

        return errors

    def validate_workplace_constraints(self, operation_data: Dict[str, Any]) -> List[str]:
        """Validate workplace and asset constraints."""
        errors = []

        asset_id = operation_data.get('asset_id')
        workplace_name = operation_data.get('workplace_name')

        if asset_id and asset_id <= 0:
            errors.append("Asset ID must be positive")

        if workplace_name and len(workplace_name.strip()) == 0:
            errors.append("Workplace name cannot be empty")

        return errors

    def validate_operation_sequence(self, operation_data: Dict[str, Any]) -> List[str]:
        """Validate operation sequencing and dependencies."""
        errors = []

        order_no = operation_data.get('order_no')
        operation_no = operation_data.get('operation_no')

        if order_no and len(order_no.strip()) == 0:
            errors.append("Order number cannot be empty")

        if operation_no and len(operation_no.strip()) == 0:
            errors.append("Operation number cannot be empty")

        # Validate operation number format (should be numeric-like)
        if operation_no:
            try:
                # Check if it's a valid operation sequence (like 0010, 0020, etc.)
                op_num = operation_no.strip()
                if not op_num.isdigit():
                    logger.info(f"Operation number {op_num} is not purely numeric (may be valid)")
            except Exception:
                pass

        return errors

    def calculate_operation_metrics(self, operation: MESOperation) -> Dict[str, Any]:
        """Calculate manufacturing metrics for an operation."""
        metrics = {}

        # Efficiency calculations
        if operation.t_target_processing_min and operation.t_actual_processing_min:
            if operation.t_actual_processing_min > 0:
                efficiency = float(operation.t_target_processing_min) / float(operation.t_actual_processing_min)
                metrics['processing_efficiency'] = round(efficiency, 3)

        # Throughput calculations
        if operation.qty_processed and operation.t_actual_processing_min:
            if operation.t_actual_processing_min > 0:
                throughput = float(operation.qty_processed) / (float(operation.t_actual_processing_min) / 60)  # per hour
                metrics['throughput_per_hour'] = round(throughput, 2)

        # Quality metrics
        if operation.qty_processed and operation.qty_scrap:
            if operation.qty_processed > 0:
                scrap_rate = float(operation.qty_scrap) / float(operation.qty_processed)
                metrics['scrap_rate'] = round(scrap_rate, 4)
                metrics['quality_rate'] = round(1 - scrap_rate, 4)

        # Schedule adherence
        if operation.planned_start_at and operation.actual_start_at:
            start_variance = (operation.actual_start_at - operation.planned_start_at).total_seconds() / 3600
            metrics['start_time_variance_hours'] = round(start_variance, 2)

        if operation.planned_end_at and operation.actual_end_at:
            end_variance = (operation.actual_end_at - operation.planned_end_at).total_seconds() / 3600
            metrics['end_time_variance_hours'] = round(end_variance, 2)

        # Completion percentage
        if operation.qty_desired and operation.qty_processed:
            completion = float(operation.qty_processed) / float(operation.qty_desired)
            metrics['completion_percentage'] = round(min(completion, 1.0), 3)

        return metrics

    def _initialize_validation_rules(self) -> Dict[str, callable]:
        """Initialize the validation rules registry."""
        return {
            'quantity_relationships': self.validate_quantity_relationships,
            'time_relationships': self.validate_time_relationships,
            'status_constraints': self.validate_status_constraints,
            'workplace_constraints': self.validate_workplace_constraints,
            'operation_sequence': self.validate_operation_sequence
        }

    def recommend_optimizations(self, operation: MESOperation) -> List[str]:
        """Provide optimization recommendations based on operation data."""
        recommendations = []

        # Efficiency recommendations
        if operation.t_target_processing_min and operation.t_actual_processing_min:
            if operation.t_actual_processing_min > 0:
                efficiency = float(operation.t_target_processing_min) / float(operation.t_actual_processing_min)
                if efficiency < 0.8:
                    recommendations.append("Consider process optimization - efficiency below 80%")
                elif efficiency > 1.2:
                    recommendations.append("Consider updating standard times - consistently exceeding targets")

        # Scrap rate recommendations
        if operation.qty_processed and operation.qty_scrap and operation.qty_processed > 0:
            scrap_rate = float(operation.qty_scrap) / float(operation.qty_processed)
            if scrap_rate > 0.1:
                recommendations.append("High scrap rate detected - review quality processes")

        # Setup time recommendations
        if operation.t_target_setup_min and operation.t_actual_setup_min:
            if operation.t_actual_setup_min > operation.t_target_setup_min * Decimal('1.5'):
                recommendations.append("Setup time significantly over target - consider SMED techniques")

        return recommendations