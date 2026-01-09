import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.snow_checker import (
    geocode_postal_code,
    reverse_geocode,
    check_snow_removal,
    check_postal_code,
    calculate_distance
)


class TestGeocodePostalCode:
    def test_valid_postal_code(self):
        result = geocode_postal_code('G1R2K8')
        assert result is not None
        assert 'lat' in result
        assert 'lon' in result
        # Quebec City coordinates should be around 46.8, -71.2
        assert 46 < result['lat'] < 47
        assert -72 < result['lon'] < -71

    def test_postal_code_with_space(self):
        result = geocode_postal_code('G1R 2K8')
        assert result is not None
        assert 'lat' in result

    def test_lowercase_postal_code(self):
        result = geocode_postal_code('g1r2k8')
        assert result is not None
        assert 'lat' in result

    def test_invalid_postal_code(self):
        result = geocode_postal_code('XXXXXX')
        # May return None or a location far from Quebec
        # Just verify it doesn't crash
        assert result is None or 'lat' in result


class TestReverseGeocode:
    def test_valid_coordinates(self):
        # Quebec City coordinates
        street = reverse_geocode(46.802925, -71.220033)
        assert isinstance(street, str)
        assert len(street) > 0

    def test_returns_string_always(self):
        # Even with invalid coords, should return string
        street = reverse_geocode(0, 0)
        assert isinstance(street, str)


class TestCalculateDistance:
    def test_same_point(self):
        dist = calculate_distance(46.8, -71.2, 46.8, -71.2)
        assert dist == 0

    def test_known_distance(self):
        # ~1km apart approximately
        dist = calculate_distance(46.8, -71.2, 46.809, -71.2)
        assert 900 < dist < 1100  # Should be around 1000m


class TestCheckSnowRemoval:
    def test_returns_dict(self):
        result = check_snow_removal(46.802925, -71.220033)
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = check_snow_removal(46.802925, -71.220033)
        assert 'success' in result
        assert result['success'] is True

    def test_found_has_lights(self):
        result = check_snow_removal(46.802925, -71.220033)
        if result.get('found'):
            assert 'lights' in result
            assert isinstance(result['lights'], list)
            if result['lights']:
                light = result['lights'][0]
                assert 'station' in light
                assert 'status' in light
                assert 'street' in light


class TestCheckPostalCode:
    def test_returns_tuple(self):
        result = check_postal_code('G1R2K8')
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_first_element_is_bool(self):
        has_op, streets = check_postal_code('G1R2K8')
        assert isinstance(has_op, bool)

    def test_second_element_is_list(self):
        has_op, streets = check_postal_code('G1R2K8')
        assert isinstance(streets, list)

    def test_invalid_postal_returns_false(self):
        has_op, streets = check_postal_code('XXXXXX')
        assert has_op is False
        assert streets == []
