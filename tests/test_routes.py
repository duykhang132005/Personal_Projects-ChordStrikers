import pytest

def test_home_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"ChordStrikers" in response.data

def test_explore_route(client):
    response = client.get('/explore')
    assert response.status_code == 200
    assert b"Test Song" in response.data

def test_explore_route_filter(client):
    response = client.get('/explore?query=Test')
    assert response.status_code == 200
    assert b"Test Song" in response.data

    response_empty = client.get('/explore?query=NonExistentSong')
    assert response_empty.status_code == 200
    assert b"Test Song" not in response_empty.data

def test_creator_route(client):
    response = client.get('/creator')
    assert response.status_code == 200
    assert b"Create New Song" in response.data
