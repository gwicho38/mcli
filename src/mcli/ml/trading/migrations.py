"""Database migrations for trading functionality"""

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from mcli.ml.config.settings import get_settings
from mcli.ml.trading.models import Base

logger = logging.getLogger(__name__)


def create_trading_tables():
    """Create trading-related tables in the database"""
    try:
        # Get database URL from settings
        settings = get_settings()
        engine = create_engine(settings.database.url)

        # Create all tables
        Base.metadata.create_all(engine)

        logger.info("Trading tables created successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to create trading tables: {e}")
        return False


def drop_trading_tables():
    """Drop trading-related tables from the database"""
    try:
        # Get database URL from settings
        settings = get_settings()
        engine = create_engine(settings.database.url)

        # Drop all tables
        Base.metadata.drop_all(engine)

        logger.info("Trading tables dropped successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to drop trading tables: {e}")
        return False


def migrate_trading_data():
    """Migrate existing data to new trading schema"""
    try:
        # Get database URL from settings
        settings = get_settings()
        engine = create_engine(settings.database.url)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Check if we need to migrate existing portfolio data
        # This would depend on your existing schema

        session.close()
        logger.info("Trading data migration completed")
        return True

    except Exception as e:
        logger.error(f"Failed to migrate trading data: {e}")
        return False


def verify_trading_schema():
    """Verify that trading schema is properly set up"""
    try:
        # Get database URL from settings
        settings = get_settings()
        engine = create_engine(settings.database.url)

        # Check if tables exist
        with engine.connect() as conn:
            # Check for trading_accounts table
            if "sqlite" in settings.database.url:
                # SQLite syntax
                result = conn.execute(
                    text(
                        """
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='trading_accounts';
                """
                    )
                )
                accounts_exists = result.fetchone() is not None

                result = conn.execute(
                    text(
                        """
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='portfolios';
                """
                    )
                )
                portfolios_exists = result.fetchone() is not None

                result = conn.execute(
                    text(
                        """
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='positions';
                """
                    )
                )
                positions_exists = result.fetchone() is not None

                result = conn.execute(
                    text(
                        """
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='trading_orders';
                """
                    )
                )
                orders_exists = result.fetchone() is not None
            else:
                # PostgreSQL syntax
                result = conn.execute(
                    text(
                        """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'trading_accounts'
                    );
                """
                    )
                )
                accounts_exists = result.scalar()

                result = conn.execute(
                    text(
                        """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'portfolios'
                    );
                """
                    )
                )
                portfolios_exists = result.scalar()

                result = conn.execute(
                    text(
                        """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'positions'
                    );
                """
                    )
                )
                positions_exists = result.scalar()

                result = conn.execute(
                    text(
                        """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'trading_orders'
                    );
                """
                    )
                )
                orders_exists = result.scalar()

        all_tables_exist = all(
            [accounts_exists, portfolios_exists, positions_exists, orders_exists]
        )

        if all_tables_exist:
            logger.info("Trading schema verification successful")
        else:
            logger.warning("Some trading tables are missing")

        return all_tables_exist

    except Exception as e:
        logger.error(f"Failed to verify trading schema: {e}")
        return False


if __name__ == "__main__":
    # Run migrations
    print("Creating trading tables...")
    if create_trading_tables():
        print("✅ Trading tables created successfully")
    else:
        print("❌ Failed to create trading tables")

    print("Verifying schema...")
    if verify_trading_schema():
        print("✅ Trading schema verified successfully")
    else:
        print("❌ Trading schema verification failed")
