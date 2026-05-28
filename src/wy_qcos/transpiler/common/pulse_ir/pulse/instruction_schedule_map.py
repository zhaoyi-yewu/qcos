#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

# pylint: disable=unused-import

"""A convenient way to track reusable subschedules by name and qubit.

This can be used for scheduling circuits with custom definitions, for
instance::

    inst_map = InstructionScheduleMap()
    inst_map.add("new_inst", 0, qubit_0_new_inst_schedule)

    sched = schedule(quantum_circuit, backend, inst_map)

An instance of this class is instantiated by Pulse-enabled backends and
populated with defaults (if available)::

    inst_map = backend.defaults().instruction_schedule_map

"""

from __future__ import annotations
import functools
import warnings
from collections import defaultdict
from collections.abc import Iterable, Callable
from typing import Any

from wy_qcos.transpiler.cmss.circuit.parameterexpression import (
    ParameterExpression,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.calibration_entries import (
    CalibrationEntry,
    ScheduleDef,
    CallableDef,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.exceptions import PulseError
from wy_qcos.transpiler.common.pulse_ir.pulse.schedule import (
    Schedule,
    ScheduleBlock,
)
from wy_qcos.transpiler.common.pulse_ir.utils.deprecate_pulse import (
    deprecate_pulse_func,
)


class InstructionScheduleMap:
    """Map instruction names and qubits to reusable pulse schedules.

    This maps
    :py:class:`~wy_qcos.transpiler.cmss.circuit.quantum_circuit.QuantumCircuit`
    :py:class:`wy_qcos.transpiler.cmss.circuit.Instruction` names and qubits
    to :py:class:`~wy_qcos.pulse.Schedule` instances. In particular, the
    mapping is formatted as type::

         Dict[str, Dict[Tuple[int], Schedule]]

    where the first key is the name of a circuit instruction, such as
    ``'u1'`` or ``'measure'``, the second key is a tuple of qubit indices,
    and the final value is a Schedule implementing the requested
    instruction.

    These can usually be seen as gate calibrations.
    """

    @deprecate_pulse_func
    def __init__(self):
        """Initialize a circuit instruction to schedule mapper instance."""
        # The processed and reformatted circuit instruction definitions

        # Do not use a lambda for nested defaultdict construction, e.g.
        # lambda: defaultdict(CalibrationEntry). This crashes qiskit parallel
        # because the framework passes args as pickled objects, and lambda
        # functions cannot be pickled.
        self._map: dict[
            str | Any,
            dict[tuple, CalibrationEntry],
        ] = defaultdict(functools.partial(defaultdict, CalibrationEntry))

        # A backwards mapping from qubit to supported instructions
        self._qubit_instructions: dict[tuple[int, ...], set] = defaultdict(set)

    def has_custom_gate(self) -> bool:
        """Return ``True`` if the map has user provided instruction."""
        for qubit_inst in self._map.values():
            for entry in qubit_inst.values():
                if entry.user_provided:
                    return True
        return False

    @property
    def instructions(self) -> list[str]:
        """Return all instructions which have definitions.

        By default, these are typically the basis gates along with other
        instructions such as measure and reset.

        Returns:
            The names of all the circuit instructions which have Schedule
            definitions in this.
        """
        return list(self._map.keys())

    def qubits_with_instruction(
        self, instruction: str | Any
    ) -> list[int | tuple[int, ...]]:
        """Return qubits for which the given instruction is defined.

        Single-qubit instructions return a flat list, and multi-qubit
        instructions return a list of ordered tuples.

        Args:
            instruction: The name of the circuit instruction.

        Returns:
            Qubit indices that have the given instruction defined. This is a
            list of tuples if the instruction has an arity greater than 1, or
            a flat list of ints otherwise.

        Raises:
            PulseError: If the instruction is not found.
        """
        instruction = _get_instruction_string(instruction)
        if instruction not in self._map:
            return []
        return [
            qubits[0] if len(qubits) == 1 else qubits
            for qubits in sorted(self._map[instruction].keys())
        ]

    def qubit_instructions(self, qubits: int | Iterable[int]) -> list[str]:
        """Return instruction names defined by the backend for given qubits.

        Args:
            qubits: A qubit index, or a list or tuple of indices.

        Returns:
            All the instructions which are defined on the qubits.

            For 1 qubit, all 1Q instructions are returned. For multiple
            qubits, all instructions that apply to that whole set of qubits
            are returned, for example ``qubits=[0, 1]`` may return
            ``['cx']``.
        """
        if _to_tuple(qubits) in self._qubit_instructions:
            return list(self._qubit_instructions[_to_tuple(qubits)])
        return []

    def has(
        self,
        instruction: str | Any,
        qubits: int | Iterable[int],
    ) -> bool:
        """Is the instruction defined for the given qubits?

        Args:
            instruction: The instruction for which to look.
            qubits: The specific qubits for the instruction.

        Returns:
            True iff the instruction is defined.
        """
        instruction = _get_instruction_string(instruction)
        return (
            instruction in self._map
            and _to_tuple(qubits) in self._map[instruction]
        )

    def assert_has(
        self,
        instruction: str | Any,
        qubits: int | Iterable[int],
    ) -> None:
        """Error if the given instruction is not defined.

        Args:
            instruction: The instruction for which to look.
            qubits: The specific qubits for the instruction.

        Raises:
            PulseError: If the instruction is not defined on the qubits.
        """
        instruction = _get_instruction_string(instruction)
        if not self.has(instruction, _to_tuple(qubits)):
            # TODO: PulseError is deprecated, this code will be removed in 2.0.
            # In the meantime, we catch the deprecation
            # warning not to overload users with non-actionable messages
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    category=DeprecationWarning,
                    message=".*The entire Qiskit Pulse package*",
                    module="qiskit",
                )
                if instruction in self._map:
                    raise PulseError(
                        f"Operation '{instruction}' exists, but is only "
                        "defined for qubits "
                        f"{self.qubits_with_instruction(instruction)}."
                    )
                raise PulseError(
                    f"Operation '{instruction}' is not defined for this "
                    "system."
                )

    def get(
        self,
        instruction: str | Any,
        qubits: int | Iterable[int],
        *params: complex | ParameterExpression,
        **kwparams: complex | ParameterExpression,
    ) -> Schedule | ScheduleBlock:
        """Return the defined schedule for an instruction on given qubits.

        This returns a :py:class:`~wy_qcos.pulse.Schedule` or
        :py:class:`~wy_qcos.pulse.ScheduleBlock` for the given instruction and
        qubits.

        If all keys are not specified, this method returns a schedule with
        unbound parameters.

        Args:
            instruction: Name of the instruction or the instruction itself.
            qubits: The qubits for the instruction.
            *params: Command parameters for generating the output schedule.
            **kwparams: Keyword command parameters for generating the
                schedule.

        Returns:
            The Schedule defined for the input.
        """
        return self._get_calibration_entry(instruction, qubits).get_schedule(
            *params, **kwparams
        )

    def _get_calibration_entry(
        self,
        instruction: str | Any,
        qubits: int | Iterable[int],
    ) -> CalibrationEntry:
        """Return the :class:`.CalibrationEntry` without generating schedule.

        When calibration entry is an unparsed Pulse Qobj, this returns the
        calibration
        without parsing it. :meth:`CalibrationEntry.get_schedule` method
        must be manually called with assigned parameters to get the
        corresponding pulse schedule.

        This method is expected to be used directly by the V2 backend
        converter for faster loading of backend calibrations.

        Args:
            instruction: Name of the instruction or the instruction itself.
            qubits: The qubits for the instruction.

        Returns:
            The calibration entry.
        """
        instruction = _get_instruction_string(instruction)
        self.assert_has(instruction, qubits)

        return self._map[instruction][_to_tuple(qubits)]

    def add(
        self,
        instruction: str | Any,
        qubits: int | Iterable[int],
        schedule: Schedule
        | ScheduleBlock
        | Callable[..., Schedule | ScheduleBlock],
        arguments: list[str] | None = None,
    ) -> None:
        """Add a known instruction and its pulse schedule for given qubits.

        This adds a new instruction mapping for the specified qubits.

        Args:
            instruction: The name of the instruction to add.
            qubits: The qubits which the instruction applies to.
            schedule: The Schedule that implements the given instruction.
            arguments: List of parameter names used to create a
                parameter-bound schedule from the associated gate
                instruction. If :py:meth:`get` is called with positional
                arguments rather than keyword arguments, this parameter list
                is used to map the input arguments to parameter objects
                stored in the target schedule.

        Raises:
            PulseError: If the qubits are provided as an empty iterable.
        """
        instruction = _get_instruction_string(instruction)

        # validation of target qubit
        qubits = _to_tuple(qubits)
        if not qubits:
            raise PulseError(
                f"Cannot add definition {instruction} with no target qubits."
            )

        # generate signature
        if isinstance(schedule, (Schedule, ScheduleBlock)):
            entry: CalibrationEntry = ScheduleDef(arguments)
        elif callable(schedule):
            if arguments:
                warnings.warn(
                    "Arguments are overruled by the callback function "
                    "signature. "
                    "Input `arguments` are ignored.",
                    UserWarning,
                )
            entry = CallableDef()
        else:
            raise PulseError(
                "Supplied schedule must be one of Schedule, ScheduleBlock, "
                "or a "
                "callable that outputs a schedule."
            )
        entry.define(schedule, user_provided=True)
        self._add(instruction, qubits, entry)

    def _add(
        self,
        instruction_name: str,
        qubits: tuple[int, ...],
        entry: CalibrationEntry,
    ):
        """A method to resister calibration entry.

        .. note::

            This is internal fast-path function, and caller must ensure
            the entry is properly formatted. This function may be used by
            other programs that load backend calibrations to create a
            Qiskit representation of it.

        Args:
            instruction_name: Name of instruction.
            qubits: List of qubits that this calibration is applied.
            entry: Calibration entry to register.

        :meta public:
        """
        self._map[instruction_name][qubits] = entry
        self._qubit_instructions[qubits].add(instruction_name)

    def remove(
        self,
        instruction: str | Any,
        qubits: int | Iterable[int],
    ) -> None:
        """Remove an instruction from the definitions stored in this map.

        This removes the given instruction for the specified qubits.

        Args:
            instruction: The name of the instruction to add.
            qubits: The qubits which the instruction applies to.
        """
        instruction = _get_instruction_string(instruction)
        qubits = _to_tuple(qubits)
        self.assert_has(instruction, qubits)

        del self._map[instruction][qubits]
        if not self._map[instruction]:
            del self._map[instruction]

        self._qubit_instructions[qubits].remove(instruction)
        if not self._qubit_instructions[qubits]:
            del self._qubit_instructions[qubits]

    def pop(
        self,
        instruction: str | Any,
        qubits: int | Iterable[int],
        *params: complex | ParameterExpression,
        **kwparams: complex | ParameterExpression,
    ) -> Schedule | ScheduleBlock:
        """Remove and return a schedule for the given instruction.

        This removes and returns the defined schedule for the given qubits.

        Args:
            instruction: Name of the instruction.
            qubits: The qubits for the instruction.
            *params: Command parameters for generating the output schedule.
            **kwparams: Keyword command parameters for generating the
                schedule.

        Returns:
            The Schedule defined for the input.
        """
        instruction = _get_instruction_string(instruction)
        schedule = self.get(instruction, qubits, *params, **kwparams)
        self.remove(instruction, qubits)
        return schedule

    def get_parameters(
        self,
        instruction: str | Any,
        qubits: int | Iterable[int],
    ) -> tuple[str, ...]:
        """Return parameter names required by the given instruction.

        This returns the parameter names for the given qubits.

        Args:
            instruction: Name of the instruction.
            qubits: The qubits for the instruction.

        Returns:
            The names of the parameters required by the instruction.
        """
        instruction = _get_instruction_string(instruction)

        self.assert_has(instruction, qubits)
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=DeprecationWarning)
            # Prevent `get_signature` from emitting pulse package
            # deprecation warnings.
            signature = self._map[instruction][
                _to_tuple(qubits)
            ].get_signature()
        return tuple(signature.parameters.keys())

    def __str__(self):
        single_q_insts = "1Q instructions:\n"
        multi_q_insts = "Multi qubit instructions:\n"
        for qubits, insts in self._qubit_instructions.items():
            if len(qubits) == 1:
                single_q_insts += f"  q{qubits[0]}: {insts}\n"
            else:
                multi_q_insts += f"  {qubits}: {insts}\n"
        instructions = single_q_insts + multi_q_insts
        return f"<{self.__class__.__name__}({instructions})>"

    def __eq__(self, other):
        if not isinstance(other, InstructionScheduleMap):
            return False

        for inst in self.instructions:
            for qinds in self.qubits_with_instruction(inst):
                try:
                    if (
                        self._map[inst][_to_tuple(qinds)]
                        != other._map[inst][_to_tuple(qinds)]
                    ):
                        return False
                except KeyError:
                    return False
        return True


def _to_tuple(values: int | Iterable[int]) -> tuple[int, ...]:
    """Return the input as a tuple.

    Args:
        values: An integer, or iterable of integers.

    Returns:
        The input values as a sorted tuple.
    """
    if isinstance(values, int):
        return (values,)
    return tuple(values)


def _get_instruction_string(
    inst: str | Any,
) -> str:
    if isinstance(inst, str):
        return inst
    else:
        try:
            return inst.name
        except AttributeError as ex:
            raise PulseError(
                'Input "inst" has no attribute "name". '
                'This should be a circuit "Instruction".'
            ) from ex
