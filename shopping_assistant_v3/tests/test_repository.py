"""Repository tests for product and price_estimate persistence.

All tests use the isolated temp SQLite from conftest.py. No network, no model calls.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from backend.database.repository import (
    create_conversation,
    create_job,
    create_price_estimate,
    create_product,
    get_price_estimates_by_product_ids,
    get_products_by_job_id,
)
from backend.database.schema import Job, PriceEstimate
from backend.shared.config import DEMO_USER_ID


def _create_job_with_conversation(session: Session) -> Job:
    conv = create_conversation(session, user_id=DEMO_USER_ID)
    session.commit()
    job = create_job(
        session,
        user_id=DEMO_USER_ID,
        conversation_id=conv.id,
        request_payload={"message": "test"},
    )
    session.commit()
    return job


class TestProductRepository:
    def test_create_and_retrieve_by_job_id(self, db_session: Session) -> None:
        job = _create_job_with_conversation(db_session)
        prod = create_product(
            db_session,
            job_id=job.id,
            source="Amazon",
            title="Test Laptop",
            brand="TestBrand",
            sale_price_usd=599.99,
            url="https://amazon.com/test",
            features="16GB RAM",
            raw_source_payload={"sku": "ABC123"},
        )
        db_session.commit()

        assert prod.id is not None
        assert prod.source == "Amazon"

        products = get_products_by_job_id(db_session, job.id)
        assert len(products) == 1
        assert products[0].title == "Test Laptop"
        assert products[0].sale_price_usd == 599.99
        raw = json.loads(products[0].raw_source_payload)
        assert raw["sku"] == "ABC123"

    def test_get_products_by_job_id_empty(self, db_session: Session) -> None:
        assert get_products_by_job_id(db_session, "no-such-job") == []

    def test_multiple_products_for_same_job(self, db_session: Session) -> None:
        job = _create_job_with_conversation(db_session)
        create_product(db_session, job_id=job.id, source="Amazon", title="Product A")
        create_product(db_session, job_id=job.id, source="BestBuy", title="Product B")
        db_session.commit()

        products = get_products_by_job_id(db_session, job.id)
        assert len(products) == 2

    def test_nulls_allowed_for_optional_fields(self, db_session: Session) -> None:
        job = _create_job_with_conversation(db_session)
        prod = create_product(
            db_session, job_id=job.id, source="Amazon", title="Minimal Product"
        )
        db_session.commit()
        assert prod.brand is None
        assert prod.sale_price_usd is None
        assert prod.url is None
        assert prod.features is None
        assert prod.raw_source_payload is None


class TestPriceEstimateRepository:
    def test_create_and_retrieve(self, db_session: Session) -> None:
        job = _create_job_with_conversation(db_session)
        prod = create_product(
            db_session, job_id=job.id, source="Amazon", title="Test"
        )
        db_session.commit()

        est = create_price_estimate(
            db_session,
            product_id=prod.id,
            estimated_value_usd=899.99,
            discount_usd=200.00,
            deal_score="hot",
            confidence=None,
            model_breakdown={"frontier": 900.0, "specialist": 850.0, "neural": 880.0},
            warnings=["test warning"],
        )
        db_session.commit()

        assert est.id is not None
        assert est.deal_score == "hot"

        estimates = get_price_estimates_by_product_ids(db_session, [prod.id])
        assert len(estimates) == 1
        assert estimates[0].estimated_value_usd == 899.99

        mb = json.loads(estimates[0].model_breakdown)
        assert mb["frontier"] == 900.0
        w = json.loads(estimates[0].warnings)
        assert w == ["test warning"]

    def test_get_by_empty_product_ids(self, db_session: Session) -> None:
        assert get_price_estimates_by_product_ids(db_session, []) == []

    def test_get_by_nonexistent_product_ids(self, db_session: Session) -> None:
        assert get_price_estimates_by_product_ids(db_session, ["no-such-id"]) == []

    def test_cascade_delete_job_deletes_products_and_estimates(
        self, db_session: Session
    ) -> None:
        job = _create_job_with_conversation(db_session)
        prod = create_product(
            db_session, job_id=job.id, source="Amazon", title="Cascade Test"
        )
        db_session.commit()
        create_price_estimate(
            db_session,
            product_id=prod.id,
            estimated_value_usd=100.0,
            discount_usd=10.0,
            deal_score="ok",
            model_breakdown={"frontier": 100.0, "specialist": 90.0, "neural": 95.0},
        )
        db_session.commit()

        assert len(get_products_by_job_id(db_session, job.id)) == 1
        assert len(get_price_estimates_by_product_ids(db_session, [prod.id])) == 1

        db_session.delete(job)
        db_session.commit()

        assert get_products_by_job_id(db_session, job.id) == []
        remaining_estimates = (
            db_session.query(PriceEstimate).filter_by(product_id=prod.id).all()
        )
        assert remaining_estimates == []
