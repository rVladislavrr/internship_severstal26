import logging

from fastapi import status
import pytest


class TestSubjects:

    @staticmethod
    @pytest.mark.parametrize(
        "length", [None, -1, -0.1, 0, 0.1, 1, 10, 100, 100.1, 100000, 100000.1])
    @pytest.mark.parametrize(
        "weight", [None, -1, -0.1, 0, 0.1, 1, 10, 100, 100.1, 100000, 100000.1]
    )
    @pytest.mark.asyncio
    async def test_create_subject(async_client, length: float, weight: float, caplog):
        caplog.set_level(logging.DEBUG)
        data = {"length": length, "weight": weight}
        response = await async_client.post(
            "/api/subjects",
            json=data
        )
        if length and weight and (length > 0 and weight > 0):
            assert response.status_code == 201
        else:
            assert response.status_code == 422

        if response.status_code == 200:
            result = response.json()
            assert result == data
            assert result.get('id') is not None
            assert result.get('is_active') == True

        for record in caplog.records:
            print(f"{record.levelname} - {record.name}: {record.message}")

    @staticmethod
    @pytest.mark.asyncio
    async def test_delete_subject(async_client, test_subject: int, caplog):
        caplog.set_level(logging.DEBUG)

        response = await async_client.get(f'/api/subjects?id_min={test_subject}&id_max={test_subject}')
        assert response.status_code == status.HTTP_200_OK
        assert response.json()[0].get('is_active') == True

        response = await async_client.delete(
            "/api/subjects/{}".format(test_subject),
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json().get('id') == test_subject
        assert response.json().get('is_active') == False

        response = await async_client.delete(
            "/api/subjects/{}".format(test_subject),
        )
        assert response.status_code == status.HTTP_409_CONFLICT

        response = await async_client.delete(
            "/api/subjects/{}".format(test_subject + 1),
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

        for record in caplog.records:
            print(f"{record.levelname} - {record.name}: {record.message}")

    @staticmethod
    @pytest.mark.parametrize("params,expected_count", [
        ({"weight_min": 13}, 1),
        ({"weight_max": 12}, 4),
        ({"weight_min": 12, "weight_max": 12}, 3),
        ({"is_active": True}, 2),
        ({"is_active": False}, 3),
        ({"created_after": "2026-12-08"}, 2),
        ({"created_before": "2026-12-07"}, 3),
        ({"created_after": "2026-12-07", "created_before": "2026-12-08"}, 2),
        ({"weight_min": 12, "is_active": False, "created_after": "2026-12-08"}, 2),
        ({}, 5),
    ])
    @pytest.mark.asyncio
    async def test_get_filter_query_with_fixture(params, expected_count, async_client, test_subjects_for_get):
        response = await async_client.get("/api/subjects", params=params)

        assert response.status_code == 200
        data = response.json()
        response = await async_client.get("/api/subjects")
        assert len(data) == expected_count

        if "weight_min" in params:
            for item in data:
                assert item["weight"] >= params["weight_min"]

        if "weight_max" in params:
            for item in data:
                assert item["weight"] <= params["weight_max"]

        if "is_active" in params:
            for item in data:
                assert item["is_active"] == params["is_active"]

    @staticmethod
    @pytest.mark.asyncio
    async def test_get_edge_cases(async_client, test_subjects_for_get):
        params = {"weight_min": 100}
        result = await async_client.get("/api/subjects", params=params)
        assert len(result.json()) == 0

        params = {"id_min": 1, "id_max": 3}
        result = await async_client.get("/api/subjects", params=params)
        for item in result.json():
            assert 1 <= item["id"] <= 3

    @staticmethod
    @pytest.mark.asyncio
    async def test_stat(async_client, test_subjects_for_get):

        response = await async_client.get("/api/subjects/statistics?end_date=2027-01-01")
        result = response.json()
        assert response.status_code == status.HTTP_200_OK

        assert result.get('added_count') == 5
        assert result.get("deleted_count") == 0
        assert result.get("average_length") == 22
        assert result.get("average_weight") == 12
        assert result.get("max_length") == 23
        assert result.get("min_length") == 21
        assert result.get("max_weight") == 13
        assert result.get("min_weight") == 11
        assert result.get("total_weight") == 60
        assert result.get("total_count") == 5
