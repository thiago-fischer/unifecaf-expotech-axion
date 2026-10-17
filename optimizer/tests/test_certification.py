from types import SimpleNamespace

import pytest
from ortools.sat.python import cp_model

from axion_optimizer import certification
from axion_optimizer.decoder import decode, priority
from axion_optimizer.domain import Item, Machine, PlanningError, Snapshot, Step, prepare


@pytest.mark.parametrize("bound,expected", [(12.99999999, 12), (13.0, 13), (0.0, 0)])
def test_conservative_bound_and_solver_parameters(
    monkeypatch: pytest.MonkeyPatch, bound: float, expected: int
) -> None:
    class ControlledSolver:
        def __init__(self) -> None:
            self.parameters = SimpleNamespace()
            self.best_objective_bound = bound

        def solve(self, model: cp_model.CpModel) -> int:
            assert model.validate() == ""
            assert len(model.proto.solution_hint.vars) == 5
            assert self.parameters.random_seed == 2_147_483_647
            assert self.parameters.num_search_workers == 1
            assert self.parameters.absolute_gap_limit == 0
            assert self.parameters.relative_gap_limit == 0
            assert self.parameters.max_time_in_seconds == 2
            return cp_model.UNKNOWN

        def status_name(self, status: int) -> str:
            return "UNKNOWN"

    monkeypatch.setattr(certification.cp_model, "CpSolver", ControlledSolver)
    problem = prepare(Snapshot((Item(123, "P", 2, (Step(1, 456, 10),)),), (Machine(456, "M"),)))
    result = certification.certify(problem, decode(problem, priority(problem)), 2_147_483_647, 2)
    assert result.lower_bound == expected
    assert result.plan is None


@pytest.mark.parametrize("bound", [float("inf"), float("nan")])
def test_nonfinite_solver_bound(monkeypatch: pytest.MonkeyPatch, bound: float) -> None:
    class ControlledSolver:
        parameters = SimpleNamespace()
        best_objective_bound = bound

        def solve(self, model: cp_model.CpModel) -> int:
            return cp_model.UNKNOWN

        def status_name(self, status: int) -> str:
            return "UNKNOWN"

    monkeypatch.setattr(certification.cp_model, "CpSolver", ControlledSolver)
    problem = prepare(Snapshot((Item(1, "P", 1, (Step(1, 1, 10),)),), (Machine(1, "M"),)))
    with pytest.raises(PlanningError):
        certification.certify(problem, decode(problem, priority(problem)), 0, 1)
