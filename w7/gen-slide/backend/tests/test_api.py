"""API tests for GenSlide backend."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create test client with isolated temp directory."""
    # Set environment variables BEFORE importing the app
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SLIDES_DIR", str(tmp_path / "slides"))
    monkeypatch.setenv("IMAGES_DIR", str(tmp_path / "images"))
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    # Clear all cached modules and services
    import sys

    modules_to_clear = [k for k in sys.modules if k.startswith("genslide")]
    for mod in modules_to_clear:
        del sys.modules[mod]

    # Now import fresh app
    from genslide.main import app

    return TestClient(app)


def test_health_check(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_get_project_not_found(client: TestClient):
    """Test getting a non-existent project."""
    response = client.get("/api/projects/non-existent-project")
    assert response.status_code == 404


def test_create_project(client: TestClient):
    """Test creating a project."""
    response = client.post(
        "/api/projects/test-project",
        json={"title": "Test Project"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "test-project"
    assert data["title"] == "Test Project"
    assert data["style"] is None
    assert data["slides"] == []
    assert data["total_cost"] == 0


def test_create_duplicate_project(client: TestClient):
    """Test creating a duplicate project."""
    # Create first project
    response = client.post(
        "/api/projects/dup-project",
        json={"title": "Test Project"},
    )
    assert response.status_code == 201

    # Try to create duplicate
    response = client.post(
        "/api/projects/dup-project",
        json={"title": "Another Title"},
    )
    assert response.status_code == 409


def test_get_project(client: TestClient):
    """Test getting a project."""
    # Create project first
    client.post(
        "/api/projects/my-project",
        json={"title": "My Project"},
    )

    # Get the project
    response = client.get("/api/projects/my-project")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "my-project"
    assert data["title"] == "My Project"


def test_update_project(client: TestClient):
    """Test updating a project."""
    # Create project first
    client.post(
        "/api/projects/update-test",
        json={"title": "Original Title"},
    )

    # Update the project
    response = client.patch(
        "/api/projects/update-test",
        json={"title": "New Title"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title"


def test_create_slide(client: TestClient):
    """Test creating a slide."""
    # Create project first
    client.post(
        "/api/projects/slide-test",
        json={"title": "Slide Test"},
    )

    # Create a slide
    response = client.post(
        "/api/projects/slide-test/slides",
        json={"content": "First slide content"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "First slide content"
    assert "sid" in data
    assert data["images"] == []
    assert data["has_matching_image"] is False


def test_update_slide(client: TestClient):
    """Test updating a slide."""
    # Create project and slide
    client.post(
        "/api/projects/slide-update-test",
        json={"title": "Slide Update Test"},
    )
    create_response = client.post(
        "/api/projects/slide-update-test/slides",
        json={"content": "Original content"},
    )
    sid = create_response.json()["sid"]

    # Update the slide
    response = client.patch(
        f"/api/projects/slide-update-test/slides/{sid}",
        json={"content": "Updated content"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Updated content"


def test_delete_slide(client: TestClient):
    """Test deleting a slide."""
    # Create project and slide
    client.post(
        "/api/projects/slide-delete-test",
        json={"title": "Slide Delete Test"},
    )
    create_response = client.post(
        "/api/projects/slide-delete-test/slides",
        json={"content": "To be deleted"},
    )
    sid = create_response.json()["sid"]

    # Delete the slide
    response = client.delete(f"/api/projects/slide-delete-test/slides/{sid}")
    assert response.status_code == 204

    # Verify it's deleted
    project_response = client.get("/api/projects/slide-delete-test")
    assert len(project_response.json()["slides"]) == 0


def test_reorder_slides(client: TestClient):
    """Test reordering slides."""
    # Create project and slides
    client.post(
        "/api/projects/reorder-test",
        json={"title": "Reorder Test"},
    )
    slide1 = client.post(
        "/api/projects/reorder-test/slides",
        json={"content": "Slide 1"},
    ).json()["sid"]
    slide2 = client.post(
        "/api/projects/reorder-test/slides",
        json={"content": "Slide 2"},
    ).json()["sid"]

    # Reorder
    response = client.put(
        "/api/projects/reorder-test/slides/order",
        json={"order": [slide2, slide1]},
    )
    assert response.status_code == 200
    assert response.json()["order"] == [slide2, slide1]


def test_get_cost(client: TestClient):
    """Test getting cost breakdown."""
    # Create project
    client.post(
        "/api/projects/cost-test",
        json={"title": "Cost Test"},
    )

    # Get cost
    response = client.get("/api/projects/cost-test/cost")
    assert response.status_code == 200
    data = response.json()
    assert data["total_cost"] == 0
    assert data["image_count"] == 0


def test_get_slide(client: TestClient):
    """Test getting a single slide."""
    # Create project and slide
    client.post(
        "/api/projects/get-slide-test",
        json={"title": "Get Slide Test"},
    )
    create_response = client.post(
        "/api/projects/get-slide-test/slides",
        json={"content": "Test slide content"},
    )
    sid = create_response.json()["sid"]

    # Get the slide
    response = client.get(f"/api/projects/get-slide-test/slides/{sid}")
    assert response.status_code == 200
    data = response.json()
    assert data["sid"] == sid
    assert data["content"] == "Test slide content"
    assert data["images"] == []
    assert "current_hash" in data
    assert data["has_matching_image"] is False


def test_get_slide_not_found(client: TestClient):
    """Test getting a non-existent slide."""
    # Create project
    client.post(
        "/api/projects/slide-not-found-test",
        json={"title": "Slide Not Found Test"},
    )

    # Try to get non-existent slide
    response = client.get("/api/projects/slide-not-found-test/slides/non-existent-sid")
    assert response.status_code == 404


def test_get_slide_project_not_found(client: TestClient):
    """Test getting a slide from non-existent project."""
    response = client.get("/api/projects/non-existent/slides/some-sid")
    assert response.status_code == 404


def test_slide_current_hash_changes_on_update(client: TestClient):
    """Test that current_hash changes when slide content is updated."""
    # Create project and slide
    client.post(
        "/api/projects/hash-test",
        json={"title": "Hash Test"},
    )
    create_response = client.post(
        "/api/projects/hash-test/slides",
        json={"content": "Original content"},
    )
    sid = create_response.json()["sid"]
    original_hash = create_response.json()["current_hash"]

    # Update the slide
    update_response = client.patch(
        f"/api/projects/hash-test/slides/{sid}",
        json={"content": "Updated content"},
    )
    updated_hash = update_response.json()["current_hash"]

    # Hash should be different
    assert original_hash != updated_hash


def test_slide_insert_after(client: TestClient):
    """Test inserting a slide after another slide."""
    # Create project and two slides
    client.post(
        "/api/projects/insert-after-test",
        json={"title": "Insert After Test"},
    )
    slide1 = client.post(
        "/api/projects/insert-after-test/slides",
        json={"content": "Slide 1"},
    ).json()["sid"]
    slide2 = client.post(
        "/api/projects/insert-after-test/slides",
        json={"content": "Slide 2"},
    ).json()["sid"]

    # Insert a new slide after slide1
    slide_between = client.post(
        "/api/projects/insert-after-test/slides",
        json={"content": "Slide Between", "after_sid": slide1},
    ).json()["sid"]

    # Verify order
    project = client.get("/api/projects/insert-after-test").json()
    sids = [s["sid"] for s in project["slides"]]
    assert sids == [slide1, slide_between, slide2]


def test_multiple_slides_have_unique_hashes(client: TestClient):
    """Test that slides with different content have different hashes."""
    # Create project and slides with different content
    client.post(
        "/api/projects/unique-hash-test",
        json={"title": "Unique Hash Test"},
    )
    slide1 = client.post(
        "/api/projects/unique-hash-test/slides",
        json={"content": "Content A"},
    ).json()
    slide2 = client.post(
        "/api/projects/unique-hash-test/slides",
        json={"content": "Content B"},
    ).json()

    # Hashes should be different
    assert slide1["current_hash"] != slide2["current_hash"]


def test_same_content_same_hash(client: TestClient):
    """Test that slides with identical content have the same hash."""
    # Create project and slides with same content
    client.post(
        "/api/projects/same-hash-test",
        json={"title": "Same Hash Test"},
    )
    slide1 = client.post(
        "/api/projects/same-hash-test/slides",
        json={"content": "Identical content"},
    ).json()
    slide2 = client.post(
        "/api/projects/same-hash-test/slides",
        json={"content": "Identical content"},
    ).json()

    # Hashes should be the same
    assert slide1["current_hash"] == slide2["current_hash"]
