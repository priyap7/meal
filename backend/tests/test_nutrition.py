import pytest
from app.nutrition import calculate

def test_portion_scaling():
    result=calculate("apple", 200)
    assert result["calories"] == 104
    assert result["protein_g"] == 0.6

def test_distinguishes_pomegranate_and_pizza():
    pomegranate=calculate("pomegranate",100)
    pizza=calculate("pizza",100)
    assert pomegranate["food_name"] != pizza["food_name"]
    assert pomegranate["calories"] != pizza["calories"]

def test_unknown_food_does_not_invent_values():
    with pytest.raises(KeyError): calculate("mystery thali",250)

def test_rejects_invalid_portion():
    with pytest.raises(ValueError): calculate("apple",0)
