import pytest

from src.bank_inflow_salary_rules import try_deterministic_inflow_salary_rule


@pytest.mark.unit
class TestBankInflowSalaryRules:
    def test_pawel_case_insensitive(self):
        assert (
            try_deterministic_inflow_salary_rule(
                "SOFTWARE ENGINEERING PAWEŁ ŚWIERBLEWSKI"
            )
            == "pensja_pawel"
        )

    def test_pawel_ascii_swierblewski(self):
        assert (
            try_deterministic_inflow_salary_rule(
                "Software Engineering Pawel Swierblewski"
            )
            == "pensja_pawel"
        )

    def test_pern_case_insensitive(self):
        assert try_deterministic_inflow_salary_rule("PERN S.A.") == "pensja_ada"
        assert try_deterministic_inflow_salary_rule("pern sp z o o") == "pensja_ada"

    def test_pawel_before_pern_if_both_substrings_unlikely(self):
        assert (
            try_deterministic_inflow_salary_rule(
                "Software Engineering Paweł Świerblewski"
            )
            == "pensja_pawel"
        )

    def test_none_empty(self):
        assert try_deterministic_inflow_salary_rule(None) is None
        assert try_deterministic_inflow_salary_rule("") is None

    def test_no_match(self):
        assert try_deterministic_inflow_salary_rule("ZABKA SP Z O O") is None
