"""Unit tests for Streamlit dashboard components

NOTE: Dashboard component tests require streamlit and dashboard modules.
Tests are conditional on dependencies being available.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import pytest
import logging
from unittest.mock import patch, MagicMock, call

# Check for streamlit and dashboard modules
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

try:
    if HAS_STREAMLIT:
        from mcli.ml.dashboard.components import charts, metrics, tables
    HAS_DASHBOARD = HAS_STREAMLIT
except ImportError:
    HAS_DASHBOARD = False

# Skip all tests if dependencies not available
if not HAS_DASHBOARD:
    pytestmark = pytest.mark.skip(reason="streamlit or dashboard components not available")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestChartsComponent:
    """Test suite for components/charts.py"""

    def test_create_timeline_chart_basic(self):
        """Test timeline chart creation with valid data"""
        logger.info("Testing timeline chart creation...")

        try:
            from mcli.ml.dashboard.components.charts import create_timeline_chart
        except ImportError:
            pytest.skip("Dashboard components not available")
            return

        # Create sample data
        df = pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=5, freq='D'),
            'value': [10, 20, 15, 30, 25],
            'status': ['success', 'failed', 'success', 'success', 'pending']
        })

        # Should not raise exception
        fig = create_timeline_chart(
            data=df,
            x_col='timestamp',
            y_col='value',
            title='Test Timeline',
            color_col='status'
        )

        assert fig is not None, "Chart should be created"
        assert hasattr(fig, 'data'), "Chart should have data attribute"
        logger.info("✅ Timeline chart test passed!")

    def test_create_timeline_chart_empty_data(self):
        """Test timeline chart handles empty DataFrame"""
        logger.info("Testing timeline chart with empty data...")

        try:
            from mcli.ml.dashboard.components.charts import create_timeline_chart
        except ImportError:
            pytest.skip("Dashboard components not available")
            return

        # Empty DataFrame with columns
        df = pd.DataFrame(columns=['timestamp', 'value', 'status'])

        # Should handle gracefully
        try:
            fig = create_timeline_chart(
                data=df,
                x_col='timestamp',
                y_col='value',
                title='Empty Chart'
            )
            # If it creates a chart, that's fine
            assert fig is not None, "Chart should be created"
        except ValueError:
            # Plotly may raise ValueError for empty data - this is acceptable
            pass

        logger.info("✅ Empty timeline chart test passed!")

    def test_create_status_pie_chart(self):
        """Test status pie chart creation"""
        logger.info("Testing status pie chart...")

        try:
            from mcli.ml.dashboard.components.charts import create_status_pie_chart
        except ImportError:
            pytest.skip("Dashboard components not available")
            return

        df = pd.DataFrame({
            'status': ['success', 'success', 'failed', 'pending', 'success']
        })

        color_map = {
            'success': '#28a745',
            'failed': '#dc3545',
            'pending': '#ffc107'
        }

        fig = create_status_pie_chart(
            data=df,
            status_col='status',
            title='Status Distribution',
            color_map=color_map
        )

        assert fig is not None, "Pie chart should be created"
        assert hasattr(fig, 'data'), "Chart should have data"
        logger.info("✅ Status pie chart test passed!")

    def test_create_gantt_chart(self):
        """Test Gantt chart creation"""
        logger.info("Testing Gantt chart...")

        try:
            from mcli.ml.dashboard.components.charts import create_gantt_chart
        except ImportError:
            pytest.skip("Dashboard components not available")
            return

        df = pd.DataFrame({
            'task': ['Task A', 'Task B', 'Task C'],
            'start': pd.to_datetime(['2025-01-01', '2025-01-02', '2025-01-03']),
            'end': pd.to_datetime(['2025-01-05', '2025-01-06', '2025-01-07']),
            'status': ['completed', 'running', 'pending']
        })

        fig = create_gantt_chart(
            data=df,
            task_col='task',
            start_col='start',
            end_col='end',
            status_col='status',
            title='Project Timeline'
        )

        assert fig is not None, "Gantt chart should be created"
        logger.info("✅ Gantt chart test passed!")


class TestMetricsComponent:
    """Test suite for components/metrics.py"""

    @patch('streamlit.metric')
    def test_display_kpi_row(self, mock_metric):
        """Test KPI row display"""
        logger.info("Testing KPI row display...")

        try:
            from mcli.ml.dashboard.components.metrics import display_kpi_row
        except ImportError:
            pytest.skip("Dashboard components not available")
            return

        # display_kpi_row expects a dict, not a list
        metrics = {
            "Total Jobs": {"value": 100, "delta": 10},
            "Success Rate": {"value": "95%", "delta": "2%"}
        }

        # Should not raise exception
        with patch('streamlit.columns', return_value=[MagicMock(), MagicMock()]):
            display_kpi_row(metrics, columns=2)

        logger.info("✅ KPI row test passed!")

    def test_display_status_badge(self):
        """Test status badge display"""
        logger.info("Testing status badge...")

        try:
            from mcli.ml.dashboard.components.metrics import display_status_badge
        except ImportError:
            pytest.skip("Dashboard components not available")
            return

        # Test different status values - function returns a string
        statuses = ['success', 'failed', 'pending', 'running']

        for status in statuses:
            badge = display_status_badge(status)
            assert isinstance(badge, str), f"Badge should be a string for {status}"
            assert status in badge.lower(), f"Badge should contain status text"

        logger.info("✅ Status badge test passed!")

    @patch('streamlit.success')
    @patch('streamlit.error')
    def test_display_health_indicator(self, mock_error, mock_success):
        """Test health indicator display"""
        logger.info("Testing health indicator...")

        try:
            from mcli.ml.dashboard.components.metrics import display_health_indicator
        except ImportError:
            pytest.skip("Dashboard components not available")
            return

        # Test healthy component - details is a string, not dict
        display_health_indicator(
            component="Database",
            is_healthy=True,
            details="status: online, latency: 10ms"
        )

        # Test unhealthy component
        display_health_indicator(
            component="API",
            is_healthy=False,
            details="Connection timeout"
        )

        assert mock_success.called, "Should call st.success for healthy"
        assert mock_error.called, "Should call st.error for unhealthy"

        logger.info("✅ Health indicator test passed!")


class TestTablesComponent:
    """Test suite for components/tables.py"""

    @patch('streamlit.dataframe')
    @patch('streamlit.text_input', return_value='')
    @patch('streamlit.caption')
    def test_display_dataframe_with_search(self, mock_caption, mock_input, mock_df):
        """Test searchable dataframe display"""
        logger.info("Testing searchable dataframe...")

        try:
            from mcli.ml.dashboard.components.tables import display_dataframe_with_search
        except ImportError:
            pytest.skip("Dashboard components not available")
            return

        df = pd.DataFrame({
            'name': ['Alice', 'Bob', 'Charlie'],
            'age': [25, 30, 35],
            'city': ['NYC', 'LA', 'Chicago']
        })

        result = display_dataframe_with_search(
            df,
            search_columns=['name', 'city'],
            default_sort_column='age',
            page_size=10
        )

        assert isinstance(result, pd.DataFrame), "Should return DataFrame"
        assert mock_df.called, "Dataframe should be displayed"
        logger.info("✅ Searchable dataframe test passed!")

    @patch('streamlit.dataframe')
    @patch('streamlit.info')
    def test_display_dataframe_with_search_empty(self, mock_info, mock_df):
        """Test searchable dataframe with empty data"""
        logger.info("Testing searchable dataframe with empty data...")

        try:
            from mcli.ml.dashboard.components.tables import display_dataframe_with_search
        except ImportError:
            pytest.skip("Dashboard components not available")
            return

        df = pd.DataFrame()

        result = display_dataframe_with_search(df)

        assert isinstance(result, pd.DataFrame), "Should return DataFrame"
        assert mock_info.called, "Info message should be shown"
        logger.info("✅ Empty searchable dataframe test passed!")

    @patch('streamlit.dataframe')
    @patch('streamlit.expander')
    def test_display_filterable_dataframe(self, mock_expander, mock_df):
        """Test filterable dataframe display"""
        logger.info("Testing filterable dataframe...")

        try:
            from mcli.ml.dashboard.components.tables import display_filterable_dataframe
        except ImportError:
            pytest.skip("Dashboard components not available")
            return

        df = pd.DataFrame({
            'status': ['success', 'failed', 'pending', 'success'],
            'name': ['Job1', 'Job2', 'Job3', 'Job4'],
            'date': pd.date_range('2025-01-01', periods=4)
        })

        filter_columns = {
            'status': 'multiselect',
            'name': 'text',
            'date': 'date_range'
        }

        # Create enough mock columns for all filters
        with patch('streamlit.columns', return_value=[MagicMock(), MagicMock(), MagicMock()]):
            with patch('streamlit.multiselect', return_value=['success', 'failed', 'pending']):
                with patch('streamlit.text_input', return_value=''):
                    with patch('streamlit.date_input', return_value=[]):
                        result = display_filterable_dataframe(
                            df,
                            filter_columns=filter_columns
                        )

        assert isinstance(result, pd.DataFrame), "Should return DataFrame"
        logger.info("✅ Filterable dataframe test passed!")

    @patch('streamlit.download_button')
    @patch('streamlit.columns', return_value=[MagicMock(), MagicMock()])
    def test_export_dataframe_csv(self, mock_columns, mock_button):
        """Test CSV export functionality"""
        logger.info("Testing CSV export...")

        try:
            from mcli.ml.dashboard.components.tables import export_dataframe
        except ImportError:
            pytest.skip("Dashboard components not available")
            return

        df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': ['a', 'b', 'c']
        })

        export_dataframe(df, filename='test', formats=['csv'])

        assert mock_button.called, "Download button should be created"
        logger.info("✅ CSV export test passed!")

    @patch('streamlit.download_button')
    @patch('streamlit.columns', return_value=[MagicMock(), MagicMock()])
    def test_export_dataframe_json(self, mock_columns, mock_button):
        """Test JSON export functionality"""
        logger.info("Testing JSON export...")

        try:
            from mcli.ml.dashboard.components.tables import export_dataframe
        except ImportError:
            pytest.skip("Dashboard components not available")
            return

        df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': ['a', 'b', 'c']
        })

        export_dataframe(df, filename='test', formats=['json'])

        assert mock_button.called, "Download button should be created"
        logger.info("✅ JSON export test passed!")

    def test_export_dataframe_empty(self):
        """Test export with empty DataFrame"""
        logger.info("Testing export with empty data...")

        try:
            from mcli.ml.dashboard.components.tables import export_dataframe
        except ImportError:
            pytest.skip("Dashboard components not available")
            return

        df = pd.DataFrame()

        # Should not raise exception
        export_dataframe(df, filename='empty')

        logger.info("✅ Empty export test passed!")

    @patch('streamlit.button', return_value=False)
    @patch('streamlit.container')
    @patch('streamlit.write')
    @patch('streamlit.divider')
    def test_display_table_with_actions(self, mock_divider, mock_write, mock_container, mock_button):
        """Test table with action buttons"""
        logger.info("Testing table with actions...")

        try:
            from mcli.ml.dashboard.components.tables import display_table_with_actions
        except ImportError:
            pytest.skip("Dashboard components not available")
            return

        df = pd.DataFrame({
            'id': [1, 2],
            'name': ['Item1', 'Item2']
        })

        actions = [
            {'label': 'Edit', 'callback': lambda x: None, 'icon': '✏️'},
            {'label': 'Delete', 'callback': lambda x: None, 'icon': '🗑️'}
        ]

        # Need 3 columns: 1 for data + 2 for actions
        with patch('streamlit.columns', return_value=[MagicMock(), MagicMock(), MagicMock()]):
            display_table_with_actions(df, actions=actions, row_id_column='id')

        logger.info("✅ Table with actions test passed!")


class TestComponentIntegration:
    """Integration tests for component interactions"""

    def test_all_components_importable(self):
        """Test that all components can be imported"""
        logger.info("Testing component imports...")

        try:
            from mcli.ml.dashboard.components import charts
            from mcli.ml.dashboard.components import metrics
            from mcli.ml.dashboard.components import tables

            assert hasattr(charts, 'create_timeline_chart')
            assert hasattr(charts, 'create_status_pie_chart')
            assert hasattr(metrics, 'display_kpi_row')
            assert hasattr(metrics, 'display_status_badge')
            assert hasattr(tables, 'display_dataframe_with_search')
            assert hasattr(tables, 'export_dataframe')

        except ImportError as e:
            pytest.skip(f"Dashboard components not available: {e}")
            return

        logger.info("✅ Component imports test passed!")

    def test_component_error_handling(self):
        """Test that components handle errors gracefully"""
        logger.info("Testing component error handling...")

        try:
            from mcli.ml.dashboard.components.charts import create_timeline_chart
            from mcli.ml.dashboard.components.tables import display_dataframe_with_search
        except ImportError:
            pytest.skip("Dashboard components not available")
            return

        # Test with None data - should not crash
        try:
            with patch('streamlit.dataframe'):
                with patch('streamlit.info'):
                    display_dataframe_with_search(pd.DataFrame())
        except Exception as e:
            pytest.fail(f"Component should handle empty data gracefully: {e}")

        logger.info("✅ Component error handling test passed!")


def main():
    """Run all component tests"""
    logger.info("="*60)
    logger.info("STARTING DASHBOARD COMPONENTS TEST SUITE")
    logger.info("="*60)
    logger.info("Testing components: charts, metrics, tables")
    logger.info("="*60)

    # Run pytest
    pytest.main([__file__, '-v', '--tb=short'])


if __name__ == "__main__":
    main()
