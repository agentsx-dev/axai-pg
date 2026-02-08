"""
Integration tests for LLM Usage models.

These tests verify that LLMUsage and LLMModelPricing models work correctly
with a real PostgreSQL database, including constraints, relationships, and cascade deletes.
"""

import pytest
import uuid
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from axai_pg import Organization, User, Document
from axai_pg.data.models import LLMUsage, LLMModelPricing


@pytest.mark.integration
@pytest.mark.db
class TestLLMUsageModel:
    """Test LLMUsage model operations."""

    def _create_test_document(self, db_session):
        """Helper to create a test organization, user, and document."""
        org = Organization(name="Test Organization")
        db_session.add(org)
        db_session.flush()

        user = User(username="testuser", email="test@example.com", org_uuid=org.uuid)
        db_session.add(user)
        db_session.flush()

        content = "Test document content"
        document = Document(
            title="Test Document",
            content=content,
            owner_uuid=user.uuid,
            org_uuid=org.uuid,
            document_type="text",
            status="draft",
            filename="test.txt",
            file_path="/test/path/test.txt",
            size=len(content),
            content_type="text/plain",
        )
        db_session.add(document)
        db_session.flush()

        return org, user, document

    def test_create_llm_usage_with_valid_data(self, db_session):
        """Test creating LLMUsage record with valid data."""
        org, user, document = self._create_test_document(db_session)

        usage = LLMUsage(
            document_uuid=document.uuid,
            user_uuid=user.uuid,
            org_uuid=org.uuid,
            operation_type="summary",
            tool_name="summary-generator",
            model_name="gpt-4o",
            model_provider="azure",
            input_tokens=1000,
            output_tokens=500,
            total_tokens=1500,
            processing_time_seconds=Decimal("2.5"),
            estimated_cost_usd=Decimal("0.015"),
            job_id="job-123",
            usage_metadata={"source": "test"},
        )
        db_session.add(usage)
        db_session.flush()

        assert usage.uuid is not None
        assert isinstance(usage.uuid, uuid.UUID)
        assert usage.id is not None
        assert isinstance(usage.id, str)
        assert len(usage.id) == 8
        assert usage.document_uuid == document.uuid
        assert usage.user_uuid == user.uuid
        assert usage.org_uuid == org.uuid
        assert usage.operation_type == "summary"
        assert usage.tool_name == "summary-generator"
        assert usage.model_name == "gpt-4o"
        assert usage.model_provider == "azure"
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        assert usage.total_tokens == 1500
        assert usage.processing_time_seconds == Decimal("2.5")
        assert usage.estimated_cost_usd == Decimal("0.015")
        assert usage.job_id == "job-123"
        assert usage.usage_metadata == {"source": "test"}
        assert usage.created_at is not None

    def test_create_llm_usage_with_all_operation_types(self, db_session):
        """Test creating LLMUsage records with all valid operation types."""
        org, user, document = self._create_test_document(db_session)

        valid_operation_types = [
            "summary",
            "graph_extraction",
            "text_cleaning",
            "email_analysis",
            "other",
        ]

        for op_type in valid_operation_types:
            usage = LLMUsage(
                document_uuid=document.uuid,
                user_uuid=user.uuid,
                org_uuid=org.uuid,
                operation_type=op_type,
                model_name="gpt-4o",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
            )
            db_session.add(usage)
            db_session.flush()
            assert usage.operation_type == op_type

    def test_llm_usage_constraint_invalid_operation_type(self, db_session):
        """Test that invalid operation_type is rejected by check constraint."""
        org, user, document = self._create_test_document(db_session)

        usage = LLMUsage(
            document_uuid=document.uuid,
            user_uuid=user.uuid,
            org_uuid=org.uuid,
            operation_type="invalid_operation",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
        db_session.add(usage)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.flush()
        assert "llm_usage_valid_operation_type" in str(exc_info.value)

    def test_llm_usage_constraint_negative_input_tokens(self, db_session):
        """Test that negative input_tokens is rejected by check constraint."""
        org, user, document = self._create_test_document(db_session)

        usage = LLMUsage(
            document_uuid=document.uuid,
            operation_type="summary",
            model_name="gpt-4o",
            input_tokens=-1,
            output_tokens=50,
            total_tokens=49,
        )
        db_session.add(usage)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.flush()
        assert "llm_usage_input_tokens_non_negative" in str(exc_info.value)

    def test_llm_usage_constraint_negative_output_tokens(self, db_session):
        """Test that negative output_tokens is rejected by check constraint."""
        org, user, document = self._create_test_document(db_session)

        usage = LLMUsage(
            document_uuid=document.uuid,
            operation_type="summary",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=-1,
            total_tokens=99,
        )
        db_session.add(usage)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.flush()
        assert "llm_usage_output_tokens_non_negative" in str(exc_info.value)

    def test_llm_usage_constraint_negative_total_tokens(self, db_session):
        """Test that negative total_tokens is rejected by check constraint."""
        org, user, document = self._create_test_document(db_session)

        usage = LLMUsage(
            document_uuid=document.uuid,
            operation_type="summary",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            total_tokens=-1,
        )
        db_session.add(usage)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.flush()
        assert "llm_usage_total_tokens_non_negative" in str(exc_info.value)

    def test_llm_usage_allows_zero_tokens(self, db_session):
        """Test that zero token values are allowed."""
        org, user, document = self._create_test_document(db_session)

        usage = LLMUsage(
            document_uuid=document.uuid,
            operation_type="summary",
            model_name="gpt-4o",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
        )
        db_session.add(usage)
        db_session.flush()

        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0

    def test_llm_usage_relationship_to_document(self, db_session):
        """Test relationship navigation from LLMUsage to Document."""
        org, user, document = self._create_test_document(db_session)

        usage = LLMUsage(
            document_uuid=document.uuid,
            user_uuid=user.uuid,
            org_uuid=org.uuid,
            operation_type="summary",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
        db_session.add(usage)
        db_session.flush()

        # Navigate from usage to document
        assert usage.document.uuid == document.uuid
        assert usage.document.title == "Test Document"

    def test_llm_usage_relationship_to_user(self, db_session):
        """Test relationship navigation from LLMUsage to User."""
        org, user, document = self._create_test_document(db_session)

        usage = LLMUsage(
            document_uuid=document.uuid,
            user_uuid=user.uuid,
            org_uuid=org.uuid,
            operation_type="summary",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
        db_session.add(usage)
        db_session.flush()

        # Navigate from usage to user
        assert usage.user.uuid == user.uuid
        assert usage.user.username == "testuser"

    def test_llm_usage_relationship_to_organization(self, db_session):
        """Test relationship navigation from LLMUsage to Organization."""
        org, user, document = self._create_test_document(db_session)

        usage = LLMUsage(
            document_uuid=document.uuid,
            user_uuid=user.uuid,
            org_uuid=org.uuid,
            operation_type="summary",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
        db_session.add(usage)
        db_session.flush()

        # Navigate from usage to organization
        assert usage.organization.uuid == org.uuid
        assert usage.organization.name == "Test Organization"

    def test_document_llm_usage_records_relationship(self, db_session):
        """Test relationship navigation from Document to LLMUsage records."""
        org, user, document = self._create_test_document(db_session)

        # Create multiple usage records for the same document
        usage1 = LLMUsage(
            document_uuid=document.uuid,
            operation_type="summary",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
        usage2 = LLMUsage(
            document_uuid=document.uuid,
            operation_type="graph_extraction",
            model_name="gpt-4o",
            input_tokens=200,
            output_tokens=100,
            total_tokens=300,
        )
        db_session.add_all([usage1, usage2])
        db_session.flush()

        # Navigate from document to usage records
        usage_records = list(document.llm_usage_records)
        assert len(usage_records) == 2
        operation_types = {r.operation_type for r in usage_records}
        assert operation_types == {"summary", "graph_extraction"}

    def test_user_llm_usage_records_relationship(self, db_session):
        """Test relationship navigation from User to LLMUsage records."""
        org, user, document = self._create_test_document(db_session)

        # Create multiple usage records for the same user
        usage1 = LLMUsage(
            document_uuid=document.uuid,
            user_uuid=user.uuid,
            operation_type="summary",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
        usage2 = LLMUsage(
            document_uuid=document.uuid,
            user_uuid=user.uuid,
            operation_type="text_cleaning",
            model_name="gpt-3.5-turbo",
            input_tokens=50,
            output_tokens=25,
            total_tokens=75,
        )
        db_session.add_all([usage1, usage2])
        db_session.flush()

        # Navigate from user to usage records (dynamic relationship)
        usage_records = list(user.llm_usage_records)
        assert len(usage_records) == 2
        total_tokens = sum(r.total_tokens for r in usage_records)
        assert total_tokens == 225

    def test_cascade_delete_document_removes_usage_records(self, db_session):
        """Test that deleting a document cascades to remove associated usage records."""
        org, user, document = self._create_test_document(db_session)
        document_uuid = document.uuid

        # Create usage records
        usage1 = LLMUsage(
            document_uuid=document.uuid,
            operation_type="summary",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
        usage2 = LLMUsage(
            document_uuid=document.uuid,
            operation_type="graph_extraction",
            model_name="gpt-4o",
            input_tokens=200,
            output_tokens=100,
            total_tokens=300,
        )
        db_session.add_all([usage1, usage2])
        db_session.flush()

        # Verify usage records exist
        usage_count = (
            db_session.query(LLMUsage).filter_by(document_uuid=document_uuid).count()
        )
        assert usage_count == 2

        # Delete the document
        db_session.delete(document)
        db_session.flush()

        # Verify usage records were cascade deleted
        usage_count = (
            db_session.query(LLMUsage).filter_by(document_uuid=document_uuid).count()
        )
        assert usage_count == 0

    def test_user_delete_sets_null_on_usage(self, db_session):
        """Test that deleting a user sets user_uuid to NULL on usage records.

        Note: We need to use a separate user for the usage record who is NOT the document owner,
        because deleting the document owner would cascade delete the document and all usage records.
        """
        org, doc_owner, document = self._create_test_document(db_session)

        # Create a second user who will be associated with the usage record
        api_user = User(username="api_user", email="api@example.com", org_uuid=org.uuid)
        db_session.add(api_user)
        db_session.flush()

        # Create usage record with the api_user (not the document owner)
        usage = LLMUsage(
            document_uuid=document.uuid,
            user_uuid=api_user.uuid,
            operation_type="summary",
            model_name="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
        db_session.add(usage)
        db_session.flush()
        usage_uuid = usage.uuid

        # Delete the api_user (not the document owner)
        db_session.delete(api_user)
        db_session.flush()

        # Verify usage record still exists but user_uuid is NULL
        updated_usage = db_session.query(LLMUsage).filter_by(uuid=usage_uuid).first()
        assert updated_usage is not None
        assert updated_usage.user_uuid is None


@pytest.mark.integration
@pytest.mark.db
class TestLLMModelPricingModel:
    """Test LLMModelPricing model operations."""

    def test_create_llm_model_pricing_with_valid_data(self, db_session):
        """Test creating LLMModelPricing record with valid data."""
        pricing = LLMModelPricing(
            model_name="gpt-4o",
            model_provider="azure",
            input_cost_per_1k=Decimal("0.005"),
            output_cost_per_1k=Decimal("0.015"),
        )
        db_session.add(pricing)
        db_session.flush()

        assert pricing.uuid is not None
        assert isinstance(pricing.uuid, uuid.UUID)
        assert pricing.id is not None
        assert isinstance(pricing.id, str)
        assert len(pricing.id) == 8
        assert pricing.model_name == "gpt-4o"
        assert pricing.model_provider == "azure"
        assert pricing.input_cost_per_1k == Decimal("0.005")
        assert pricing.output_cost_per_1k == Decimal("0.015")
        assert pricing.effective_from is not None
        assert pricing.effective_until is None  # Current pricing
        assert pricing.created_at is not None
        assert pricing.updated_at is not None

    def test_llm_model_pricing_unique_constraint(self, db_session):
        """Test that model_name has a unique constraint."""
        pricing1 = LLMModelPricing(
            model_name="gpt-4o",
            model_provider="azure",
            input_cost_per_1k=Decimal("0.005"),
            output_cost_per_1k=Decimal("0.015"),
        )
        db_session.add(pricing1)
        db_session.flush()

        # Attempt to create another pricing with the same model_name
        pricing2 = LLMModelPricing(
            model_name="gpt-4o",
            model_provider="openai",  # Different provider
            input_cost_per_1k=Decimal("0.006"),
            output_cost_per_1k=Decimal("0.016"),
        )
        db_session.add(pricing2)

        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_llm_model_pricing_with_validity_period(self, db_session):
        """Test creating LLMModelPricing with effective_until set."""
        from datetime import datetime, timezone, timedelta

        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=30)

        pricing = LLMModelPricing(
            model_name="gpt-4",
            model_provider="azure",
            input_cost_per_1k=Decimal("0.03"),
            output_cost_per_1k=Decimal("0.06"),
            effective_from=start_date,
            effective_until=end_date,
        )
        db_session.add(pricing)
        db_session.flush()

        assert pricing.effective_from is not None
        assert pricing.effective_until is not None
        assert pricing.effective_until > pricing.effective_from

    def test_llm_model_pricing_multiple_models(self, db_session):
        """Test creating pricing for multiple different models."""
        models = [
            ("gpt-4o", "azure", "0.005", "0.015"),
            ("gpt-4o-mini", "azure", "0.00015", "0.0006"),
            ("gpt-4", "azure", "0.03", "0.06"),
            ("gpt-3.5-turbo", "azure", "0.0005", "0.0015"),
        ]

        for model_name, provider, input_cost, output_cost in models:
            pricing = LLMModelPricing(
                model_name=model_name,
                model_provider=provider,
                input_cost_per_1k=Decimal(input_cost),
                output_cost_per_1k=Decimal(output_cost),
            )
            db_session.add(pricing)

        db_session.flush()

        # Verify all models were created
        count = db_session.query(LLMModelPricing).count()
        assert count == 4

        # Query specific model
        gpt4o = db_session.query(LLMModelPricing).filter_by(model_name="gpt-4o").first()
        assert gpt4o is not None
        assert gpt4o.input_cost_per_1k == Decimal("0.005")

    def test_llm_model_pricing_query_by_model_name(self, db_session):
        """Test querying pricing by model name."""
        pricing = LLMModelPricing(
            model_name="claude-3-sonnet",
            model_provider="anthropic",
            input_cost_per_1k=Decimal("0.003"),
            output_cost_per_1k=Decimal("0.015"),
        )
        db_session.add(pricing)
        db_session.flush()

        # Query by model name
        result = (
            db_session.query(LLMModelPricing)
            .filter_by(model_name="claude-3-sonnet")
            .first()
        )
        assert result is not None
        assert result.model_provider == "anthropic"
        assert result.input_cost_per_1k == Decimal("0.003")
        assert result.output_cost_per_1k == Decimal("0.015")
