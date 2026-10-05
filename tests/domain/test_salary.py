import unittest

from buscador_empleos.domain.salary import NO_SALARY, Salary, format_salary, parse_salary, to_cop_monthly


class ParseSalaryTest(unittest.TestCase):
    def test_colombian_formats(self):
        self.assertEqual(parse_salary("Salario: $ 3.000.000").min_cop, 3_000_000)
        self.assertEqual(parse_salary("$ 2.655.000,00 (Mensual)").min_cop, 2_655_000)
        self.assertEqual(parse_salary("Sueldo: $4.500.000 mensuales").min_cop, 4_500_000)

    def test_range_uses_the_lower_bound(self):
        self.assertEqual(parse_salary("$ 3.000.000 - $ 4.000.000 al mes").min_cop, 3_000_000)

    def test_millions_with_decimals(self):
        self.assertEqual(parse_salary("Salario: $3 a $3,5 millones").min_cop, 3_000_000)
        self.assertEqual(parse_salary("Salario: $1,5 a $2 millones").min_cop, 1_500_000)

    def test_keeps_the_original_text(self):
        self.assertEqual(parse_salary("Salario: $3 a $3,5 millones").text, "$3 a $3,5 millones")

    def test_missing_or_unspecified_salary(self):
        self.assertEqual(parse_salary("Salario: A convenir"), NO_SALARY)
        self.assertEqual(parse_salary("Sin datos de pago"), NO_SALARY)

    def test_ignores_amounts_too_small_to_be_a_monthly_salary(self):
        self.assertIsNone(parse_salary("Salario: $ 120.000").min_cop)

    def test_result_is_a_plain_tuple_too(self):
        text, minimum = parse_salary("Salario: $ 3.000.000")
        self.assertEqual((text, minimum), ("$ 3.000.000", 3_000_000))
        self.assertEqual(parse_salary("nada"), ("", None))


class CurrencyTest(unittest.TestCase):
    def test_conversion_to_monthly_cop(self):
        self.assertEqual(to_cop_monthly(3000, "USD", "month"), 12_000_000)
        self.assertEqual(to_cop_monthly(60000, "USD", "year"), 20_000_000)
        self.assertEqual(to_cop_monthly(40, "USD", "hour"), 25_600_000)
        self.assertEqual(to_cop_monthly(2_000_000, "COP", "month"), 2_000_000)

    def test_custom_rates_override_the_defaults(self):
        self.assertEqual(to_cop_monthly(1000, "USD", "month", rates={"USD": 3900}), 3_900_000)

    def test_currency_code_is_case_insensitive(self):
        self.assertEqual(to_cop_monthly(1000, "usd", "month"), 4_000_000)

    def test_unknown_currency_period_or_amount(self):
        self.assertIsNone(to_cop_monthly(100, "XXX", "month"))
        self.assertIsNone(to_cop_monthly(100, "USD", "decade"))
        self.assertIsNone(to_cop_monthly(0, "USD", "month"))
        self.assertIsNone(to_cop_monthly(None, "USD", "month"))

    def test_format_salary(self):
        self.assertEqual(format_salary(3000, 4500, "USD", "month"), "USD 3.000 - 4.500 / mes")
        self.assertEqual(format_salary(3000, None, "EUR", "year"), "EUR 3.000 / año")
        self.assertEqual(format_salary(3000, None, "EUR", "otra"), "EUR 3.000")
        self.assertEqual(format_salary(None, None, "USD", "month"), "")

    def test_salary_is_a_named_tuple(self):
        self.assertEqual(Salary("x", 1).min_cop, 1)


if __name__ == "__main__":
    unittest.main()
