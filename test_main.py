import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app


# Separate in-memory database for testing
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


@pytest.fixture
def client():
    # Create fresh test tables
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Tell FastAPI to use the test database
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)


# Test 1: Home API
def test_home(client):
    response = client.get("/")

    assert response.status_code == 200

    assert response.json() == {
        "message": "FastAPI CRUD running successfully!"
    }


# Test 2: Create Product API
def test_create_product(client):

    product_data = {
        "name": "Laptop",
        "price": 45000,
        "quantity": 2
    }

    response = client.post("/products", json=product_data)

    assert response.status_code == 201

    result = response.json()

    assert result["name"] == "Laptop"
    assert result["price"] == 45000
    assert result["quantity"] == 2
    assert "id" in result



# Test 3: Invalid product price
def test_create_product_invalid_price(client):

    product_data = {
        "name": "Laptop",
        "price": -500,
        "quantity": 2
    }

    response = client.post("/products", json=product_data)

    assert response.status_code == 422




# Test 4: Get product by ID
def test_get_product(client):

    # First, create a product in the test database
    product_data = {
        "name": "Mouse",
        "price": 500,
        "quantity": 5
    }

    create_response = client.post(
        "/products",
        json=product_data
    )

    assert create_response.status_code == 201

    # Get the ID of the newly created product
    product_id = create_response.json()["id"]

    # Call GET API using that product ID
    response = client.get(f"/products/{product_id}")

    assert response.status_code == 200

    result = response.json()

    assert result["id"] == product_id
    assert result["name"] == "Mouse"
    assert result["price"] == 500
    assert result["quantity"] == 5



# Test 5: Product not found
def test_get_product_not_found(client):

    response = client.get("/products/99999")

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Product not found"
    }




# Test 6: Update Product API
def test_update_product(client):

    # Step 1: Create a product
    product_data = {
        "name": "Mouse",
        "price": 500,
        "quantity": 5
    }

    create_response = client.post(
        "/products",
        json=product_data
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    # Step 2: Prepare updated product details
    updated_data = {
        "name": "Wireless Mouse",
        "price": 800,
        "quantity": 10
    }

    # Step 3: Call PUT API
    response = client.put(
        f"/products/{product_id}",
        json=updated_data
    )

    # Step 4: Verify response
    assert response.status_code == 200

    result = response.json()

    assert result["name"] == "Wireless Mouse"
    assert result["price"] == 800
    assert result["quantity"] == 10

    # Step 5: Fetch product again
    get_response = client.get(f"/products/{product_id}")

    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Wireless Mouse"
    assert get_response.json()["price"] == 800
    assert get_response.json()["quantity"] == 10



# Test 7: Delete Product API
def test_delete_product(client):

    # Step 1: Create a product
    product_data = {
        "name": "Keyboard",
        "price": 1200,
        "quantity": 3
    }

    create_response = client.post(
        "/products",
        json=product_data
    )

    assert create_response.status_code == 201

    product_id = create_response.json()["id"]

    # Step 2: Delete the product
    delete_response = client.delete(
        f"/products/{product_id}"
    )

    assert delete_response.status_code == 200

    assert delete_response.json() == {
        "message": "Product deleted successfully"
    }

    # Step 3: Verify product no longer exists
    get_response = client.get(
        f"/products/{product_id}"
    )

    assert get_response.status_code == 404



# Test 8: Get all products
def test_get_products(client):

    # Step 1: Create two products
    products = [
        {
            "name": "Laptop",
            "price": 45000,
            "quantity": 2
        },
        {
            "name": "Mouse",
            "price": 500,
            "quantity": 5
        }
    ]

    for product in products:
        response = client.post("/products", json=product)
        assert response.status_code == 201

    # Step 2: Call GET all products API
    response = client.get("/products")

    assert response.status_code == 200

    # Step 3: Verify returned products
    result = response.json()

    assert len(result) == 2

    assert {item["name"] for item in result} == {
        "Laptop",
        "Mouse"
    }