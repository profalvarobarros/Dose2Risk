import pytest
import math
import logging
from dose2risk.core.risk_calculator import CalculadoraRisco

# Mock configuration for BEIR V tests
MOCK_BEIR_V_CONFIG_THYROID = {
    "model_type": "thyroid_age_dependent",
    "params": {
        "threshold_age": 18,
        "coef_young": 7.5,
        "coef_adult": 0.5
    }
}

MOCK_BEIR_V_CONFIG_LEUKEMIA = {
    "model_type": "leukemia_lq",
    "params": {
        "alpha2": 0.243,
        "alpha3": 0.271
    }
}

class TestRiskCalculatorUnit:

    @pytest.fixture
    def calculator(self, tmp_path):
        """Returns a CalculadoraRisco instance with dummy file paths."""
        return CalculadoraRisco(
            input_csv=str(tmp_path / "dummy_input.csv"),
            params_file=str(tmp_path / "dummy_params.json"),
            output_folder=str(tmp_path / "output"),
            exposure_age=30,
            current_age=50
        )

    def test_beir_v_thyroid_young(self, calculator):
        """Test BEIR V Thyroid logic for young patients (< 18)."""
        dose = 0.5 # 500 mSv (High Dose)
        age_exposicao = 10 # Young
        
        err, eq, params = calculator.beir_v_risk(
            dose_Sv=dose,
            age_exp=age_exposicao,
            age_att=50,
            gender='female',
            beir_v_config=MOCK_BEIR_V_CONFIG_THYROID
        )
        
        # Expect ERR = 7.5 * dose
        expected_err = 7.5 * dose
        assert math.isclose(err, expected_err), f"Expected {expected_err}, got {err}"
        assert "7.5" in eq

    def test_beir_v_thyroid_adult(self, calculator):
        """Test BEIR V Thyroid logic for adults (>= 18)."""
        dose = 0.5
        age_exposicao = 20 # Adult
        
        err, eq, params = calculator.beir_v_risk(
            dose_Sv=dose,
            age_exp=age_exposicao,
            age_att=50,
            gender='female',
            beir_v_config=MOCK_BEIR_V_CONFIG_THYROID
        )
        
        # Expect ERR = 0.5 * dose
        expected_err = 0.5 * dose
        assert math.isclose(err, expected_err)
        assert "0.5" in eq

    def test_beir_v_leukemia_lq(self, calculator):
        """Test BEIR V Leukemia Linear-Quadratic model."""
        dose = 1.0 # 1 Sv
        age_exp = 30
        age_att = 40 # t = 10 years since exposure
        
        # For age_exp > 20 and t <= 25, beta = 2.367 (Defined in code logic)
        # Formula: (alpha2*D + alpha3*D^2) * exp(beta)
        
        err, eq, params = calculator.beir_v_risk(
            dose_Sv=dose,
            age_exp=age_exp,
            age_att=age_att,
            gender='male',
            beir_v_config=MOCK_BEIR_V_CONFIG_LEUKEMIA
        )
        
        alpha2 = 0.243
        alpha3 = 0.271
        beta = 2.367 # Hardcoded logic for adult leukemia time factor in code
        
        term_quad = (alpha2 * dose + alpha3 * (dose**2))
        term_exp = math.exp(beta)
        expected_err = term_quad * term_exp
        
        assert math.isclose(err, expected_err, rel_tol=1e-3)

    def test_beir_vii_solid_simple(self, calculator):
        """Test BEIR VII Solid Cancer formula manually."""
        # ERR = beta * dose * exp(gamma * e_star) * (a/60)^eta / ddref
        
        beta = 0.5
        gamma = 0
        eta = 0
        dose = 0.05 # 50 mSv (Low Dose)
        ddref = 1.5
        age_att = 60
        e_star = 0
        
        err, eq = calculator.beir_vii_risk(
            beta=beta, gamma=gamma, eta=eta,
            dose_Sv=dose, age_exp=30, age_att=age_att,
            model_type='solid', latency=5, ddref=ddref,
            beta_M=0, beta_F=0, theta=0, delta=0, phi=0, e_star=e_star
        )
        
        # With gamma=0, eta=0, formula simplifies to: beta * dose / ddref
        expected = (beta * dose) / ddref
        
        assert math.isclose(err, expected)
        assert "ERR =" in eq

    def test_invalid_negative_time(self, calculator):
        """Risk should be 0 if current age < exposure age (Impossible time travel)."""
        err, msg, _ = calculator.beir_v_risk(
            dose_Sv=1.0, age_exp=50, age_att=40, gender='M', beir_v_config={}
        )
        assert err == 0.0
