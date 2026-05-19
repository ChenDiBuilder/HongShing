"""Integration tests for rewards."""

from sqlalchemy import select

from app.models import QRCampaign, Reward, RewardTemplate


class TestRewardClaim:
    async def test_reward_template_creation(self, db_session):
        template = RewardTemplate(
            name="$5 Off First Order",
            code_prefix="HS",
            reward_type="fixed",
            reward_value=500,
            valid_days=30,
        )
        db_session.add(template)
        await db_session.flush()
        assert template.id is not None
        assert template.code_prefix == "HS"
        assert template.reward_value == 500

    async def test_reward_code_exists(self, db_session, customer_user):
        """Reward code is stored and retrievable."""
        template = RewardTemplate(
            name="Test", code_prefix="HS", reward_type="fixed", reward_value=500
        )
        db_session.add(template)
        await db_session.flush()

        reward = Reward(
            user_id=customer_user.id,
            reward_template_id=template.id,
            code="HS-ABC123",
            status="issued",
        )
        db_session.add(reward)
        await db_session.flush()

        assert reward.code == "HS-ABC123"
        assert reward.status == "issued"

    async def test_reward_source_attribution(self, db_session, customer_user):
        from sqlalchemy import select

        campaign = QRCampaign(name="Test", source_code="receipt", active=True)
        db_session.add(campaign)
        await db_session.flush()

        template = RewardTemplate(
            name="Test Reward", code_prefix="HS", reward_type="fixed", reward_value=500
        )
        db_session.add(template)
        await db_session.flush()

        reward = Reward(
            user_id=customer_user.id,
            reward_template_id=template.id,
            code="HS-TSTA1",
            source_code="receipt",
            qr_campaign_id=campaign.id,
            status="issued",
        )
        db_session.add(reward)
        await db_session.flush()

        result = await db_session.execute(
            select(Reward).where(Reward.user_id == customer_user.id)
        )
        rewards = result.scalars().all()
        assert len(rewards) == 1
        assert rewards[0].source_code == "receipt"
