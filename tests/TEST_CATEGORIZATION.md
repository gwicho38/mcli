# Test Categorization Plan

## CLI Tests (tests/cli/)
Commands that test CLI interfaces using Click CliRunner:
- test_self.py → cli/test_self_cmd.py
- test_model_cmd.py → cli/test_model_cmd.py  
- test_chat_cmd.py → cli/test_chat_cmd.py
- test_main_app.py → cli/test_main_app.py
- test_all_cli.py → cli/test_all_commands.py
- test_commands_cmd.py (if exists) → cli/test_commands_cmd.py

## Unit Tests (tests/unit/)
Tests for individual functions/classes:
- test_lib.py → unit/test_lib_utils.py
- test_auth.py → unit/test_lib_auth.py
- test_file.py → unit/test_lib_files.py
- test_utility_functions.py → unit/test_utility_functions.py
- test_utility_functions_simple.py → unit/test_utility_simple.py
- test_command_discovery.py → unit/test_discovery.py
- test_optional_dependencies.py → unit/test_dependencies.py
- test_uv_compatibility.py → unit/test_uv_compat.py
- test_rich.py → unit/test_ui_rich.py
- test_erd_import.py → unit/test_erd_imports.py
- test_erd.py → unit/test_erd_generation.py
- test_generic_erd.py → unit/test_erd_generic.py
- test_generate_graph.py → unit/test_graph_generation.py
- test_preprocessing_simple.py → unit/test_ml_preprocessing.py

## Integration Tests (tests/integration/)
Tests that involve multiple components or external services:
- test_lsh_integration.py → integration/test_lsh_service.py
- test_workflow_integration.py → integration/test_workflow.py
- test_politician_trading_integration.py → integration/test_politician_trading.py
- test_data_pipeline.py → integration/test_ml_data_pipeline.py
- test_ml_pipeline.py → integration/test_ml_pipeline.py
- test_chat_client.py → integration/test_chat_client.py
- test_daemon_client.py → integration/test_daemon_client.py
- test_daemon.py → integration/test_daemon_server.py
- test_lsh_client.py → integration/test_lsh_client.py
- test_ml_auth.py → integration/test_ml_auth.py
- test_ml_models.py → integration/test_ml_models.py
- test_registry.py → integration/test_service_registry.py
- test_webapp.py → integration/test_flask_webapp.py
- test_webapp_comprehensive.py → integration/test_webapp_full.py
- test_gcloud.py → integration/test_gcloud_services.py
- test_wakatime.py → integration/test_wakatime_api.py

## Integration Tests - Scrapers (tests/integration/)
- test_california_scraper.py → integration/test_california_scraper.py
- test_congress_scraper.py → integration/test_congress_scraper.py
- test_uk_scraper.py → integration/test_uk_scraper.py
- test_us_states_scraper.py → integration/test_us_states_scraper.py

## E2E Tests (tests/e2e/)
Full workflow/scenario tests:
- end_to_end_integration_test.py → e2e/test_complete_workflows.py
- simple_integration_test.py → e2e/test_basic_workflows.py

## Tests with Special Handling
Chat/Agent tests need analysis:
- test_chat_system_control.py → integration/test_chat_system.py (has real API calls)
- test_enhanced_chat.py → unit/test_enhanced_chat.py (mostly unit)
- test_agent_functionality.py → integration/test_agent.py
- test_repo.py → integration/test_repo_operations.py
- test_fix.py → unit/test_bug_fixes.py
- test_fixed_issues.py → unit/test_regression.py
- test_oi.py → integration/test_oi_service.py
- test_videos.py → integration/test_video_processing.py

## Demo/Utility Files (keep in tests root or move to scripts/)
- demo_hierarchical_transform.py → scripts/demo_hierarchical.py
- demo_generate_graph.py → scripts/demo_graph.py
- run_tests.py → keep in tests/
- test_harness.py → keep in tests/

## Existing Configs (keep in tests/)
- conftest.py → stays, will be updated
- pytest.ini → stays
- TEST_SUMMARY.md → stays
- test_makefile_full.sh → stays or move to scripts/

