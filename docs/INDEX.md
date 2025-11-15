# MCLI Framework Documentation Index

Welcome to the MCLI Framework documentation! This index helps you find the documentation you need quickly.

**Current Version**: 7.14.4
**Last Updated**: 2025-11-15

---

## 📚 Table of Contents

- [Quick Start](#quick-start)
- [Setup & Installation](#setup--installation)
- [User Guides](#user-guides)
- [Development](#development)
- [Features](#features)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Release Notes](#release-notes)
- [Contributing](#contributing)

---

## 🚀 Quick Start

**New to MCLI?** Start here:

| Document | Description |
|----------|-------------|
| [README.md](../README.md) | Project overview, quick start, and core concepts |
| [Quick Start (Self-Hosted)](guides/QUICK_START_SELF_HOSTED.md) | Self-hosting guide for MCLI |
| [Installation Guide](setup/INSTALL.md) | Detailed installation instructions |

---

## 🔧 Setup & Installation

| Document | Description |
|----------|-------------|
| [Installation Guide](setup/INSTALL.md) | PyPI, Homebrew, and development installation |
| [Setup Instructions](setup/SETUP_INSTRUCTIONS.md) | Environment setup and configuration |
| [Streamlit Deployment](setup/STREAMLIT_DEPLOYMENT.md) | Deploy Streamlit dashboards |
| [Streamlit Cloud Troubleshooting](setup/STREAMLIT_CLOUD_TROUBLESHOOTING.md) | Fix common Streamlit deployment issues |
| [Trading Schema Setup](setup/TRADING_SCHEMA_SETUP.md) | Database schema for trading features |

---

## 📖 User Guides

### Workflow Management
| Document | Description |
|----------|-------------|
| [Custom Commands](custom-commands.md) | Creating and managing custom workflows |
| [Portable Commands Guide](PORTABLE_COMMANDS_GUIDE.md) | Portable workflow management |
| [Shell Workflows Guide](guides/SHELL_WORKFLOWS.md) | Creating bash/shell-based workflows |
| [Workflow Notebooks](workflow-notebooks.md) | Visual editing with VSCode extension |

### Dashboards
| Document | Description |
|----------|-------------|
| [Dashboard Guide](guides/DASHBOARD.md) | Using ML and trading dashboards |
| [Trading Dashboard Guide](TRADING_DASHBOARD_GUIDE.md) | Politician trading dashboard |
| [Dashboard Makefile Usage](dashboard_makefile_usage.md) | Building dashboards with Make |
| [Streamlit Deployment Guide](guides/STREAMLIT_DEPLOYMENT_GUIDE.md) | Deploy dashboards to cloud |

### Other Features
| Document | Description |
|----------|-------------|
| [Model Training Guide](model_training_guide.md) | Train ML models with MCLI |
| [Prediction Engine](prediction_engine.md) | Using the prediction engine |
| [Visualization Features](VISUALIZATION_FEATURES.md) | Data visualization capabilities |

---

## 👨‍💻 Development

### Getting Started
| Document | Description |
|----------|-------------|
| [CONTRIBUTING.md](../CONTRIBUTING.md) | How to contribute to MCLI |
| [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) | Community guidelines |
| [CLAUDE.md](../CLAUDE.md) | Guide for Claude Code AI assistant |

### Code Quality
| Document | Description |
|----------|-------------|
| [Testing Guide](development/TESTING.md) | Writing and running tests |
| [Linting Guide](development/LINTING.md) | Code style and linting tools |
| [Performance Optimizations](development/PERFORMANCE_OPTIMIZATIONS.md) | Performance best practices |

### CI/CD & Infrastructure
| Document | Description |
|----------|-------------|
| [CI Fix Recommendations](development/CI_FIX_RECOMMENDATIONS.md) | Fixing CI/CD issues |
| [Checkpoint: Politician Names Fix](development/CHECKPOINT_politician_names_fix.md) | Example bug fix checkpoint |

---

## ✨ Features

### Core Features
| Document | Description |
|----------|-------------|
| [Shell Commands](features/SHELL_COMMANDS.md) | Available shell commands |
| [Shell Completion](features/SHELL_COMPLETION.md) | Tab completion for bash/zsh/fish |
| [Optional Dependencies](guides/OPTIONAL_DEPENDENCIES.md) | Managing optional features |

### Advanced Features
| Document | Description |
|----------|-------------|
| [OpenAI Adapter Implementation](features/OPENAI_ADAPTER_IMPLEMENTATION.md) | OpenAI integration |
| [Gravity Visualization](features/GRAVITY_VIZ_README.md) | Gravity-based data visualization |
| [Repo Cleanup](features/REPO_CLEANUP.md) | Repository maintenance features |

---

## ⚙️ Configuration

| Document | Description |
|----------|-------------|
| [Environment Variables](configuration/ENV.md) | Configuration via .env files |
| [mcli.toml Example](configuration/mcli.toml.example) | Configuration file example |

---

## 🚀 Deployment

| Document | Description |
|----------|-------------|
| [Deployment Guide (Complete)](DEPLOYMENT_GUIDE_COMPLETE.md) | Full deployment guide |
| [Deployment Status](DEPLOYMENT_STATUS.md) | Current deployment status |
| [Azure Deployment](deployment/AZURE-DEPLOYMENT.md) | Deploying to Azure |
| [LSH Deployment Guide](lsh_deployment_guide.md) | Deploy with LSH framework |
| [LSH Job Registry Setup](lsh_job_registry_setup.md) | LSH job registry configuration |
| [Secrets Deployment](SECRETS_DEPLOYMENT.md) | Managing secrets in production |
| [Streamlit Deployment](streamlit_deployment.md) | Streamlit-specific deployment |
| [Streamlit Cloud Deployment](streamlit_cloud_deployment.md) | Deploy to Streamlit Cloud |

### Infrastructure
| Document | Description |
|----------|-------------|
| [Public Model Service Setup](PUBLIC_MODEL_SERVICE_SETUP.md) | Public model serving setup |
| [Router Nginx Setup](ROUTER_NGINX_SETUP.md) | Nginx reverse proxy setup |
| [Router SSL Setup](ROUTER_SSL_SETUP.md) | SSL/TLS configuration |
| [Model Service README](README_MODEL_SERVICE.md) | Model serving documentation |

---

## 📋 Release Notes

### Latest Releases
| Version | Date | Highlights |
|---------|------|------------|
| [7.14.4](releases/7.14.4.md) | 2025-11-15 | Added `mcli run` alias for `mcli workflows` command |
| [7.14.3](releases/7.14.3.md) | 2025-11-14 | Documentation improvements, CI/CD enhancements, Azure deployment fix |
| [7.14.2](releases/7.14.2.md) | 2025-11-14 | Documentation updates, workflow migration, bug fixes |
| [7.14.0](releases/7.14.0.md) | 2025-11-06 | Command naming simplification |
| [7.12.2](releases/7.12.2.md) | 2025-11-01 | Workflow code validation in verify command |
| [7.12.1](releases/7.12.1.md) | 2025-11-01 | Version command moved to self group |
| [7.12.0](releases/7.12.0.md) | 2025-11-01 | Command structure reorganization |
| [7.10.2](releases/7.10.2.md) | 2025-10-30 | Test suite 100% pass rate, security enhancements |

### Major Version History
| Version Range | Description |
|---------------|-------------|
| [7.9.x](releases/) | VSCode extension, marketplace preparation |
| [7.8.x](releases/) | Testing improvements, Streamlit enhancements |
| [7.7.x](releases/) | Dashboard features, model service updates |
| [7.6.x](releases/) | Model service enhancements |
| [7.1.x](releases/) | ML features, trading dashboard |
| [7.0.x](releases/) | Major architecture update |
| [0.8.x](releases/) | Early releases |

### Special Release Notes
| Document | Description |
|----------|-------------|
| [Phase 2 Complete](releases/PHASE-2-COMPLETE.md) | Phase 2 milestone summary |
| [Extension Marketplace Ready](releases/EXTENSION-MARKETPLACE-READY.md) | VSCode extension publication |

---

## 🤝 Contributing

| Document | Description |
|----------|-------------|
| [Contributing Guide](../CONTRIBUTING.md) | How to contribute |
| [Code of Conduct](../CODE_OF_CONDUCT.md) | Community standards |
| [Security Policy](../SECURITY.md) | Security reporting guidelines |

---

## 📂 Additional Documentation

### Debugging & Troubleshooting
| Document | Description |
|----------|-------------|
| [Supabase Connection Fix](debugging/supabase_connection_fix.md) | Fix Supabase connection issues |
| [Dashboard Fixes](dashboard_fixes.md) | Common dashboard issues |

### Bug Reports
| Document | Description |
|----------|-------------|
| [Bug Report: Politician Names](bug-reports/BUG_REPORT_politician_names.md) | Example bug report |

### Migration Guides
| Document | Description |
|----------|-------------|
| [Politician Trading Migration](MIGRATION_POLITICIAN_TRADING.md) | Migrate to standalone tracker |
| [Streamlit Migration Plan](STREAMLIT_MIGRATION_PLAN.md) | Dashboard migration |
| [Streamlit Migration Summary](STREAMLIT_MIGRATION_SUMMARY.md) | Migration results |

### Architecture
| Document | Description |
|----------|-------------|
| [Architecture Comparison](ARCHITECTURE_COMPARISON.md) | Design decisions and comparisons |
| [Command Consolidation](COMMAND_CONSOLIDATION.md) | Command structure changes |
| [Clean Command Enhancement](CLEAN_COMMAND_ENHANCEMENT.md) | Clean command improvements |
| [Implementation Complete](IMPLEMENTATION_COMPLETE.md) | Feature implementation status |

### Issue Tracking
| Document | Description |
|----------|-------------|
| [Issue 70 Progress](issue_70_progress.md) | Example issue progress tracking |

### VSCode Extension
| Document | Description |
|----------|-------------|
| [VSCode Extension Sync Strategy](vscode-extension/SYNC_STRATEGY.md) | Python/JSON/Notebook sync |
| [Monaco Setup](../README-MONACO-SETUP.md) | Monaco editor integration |

---

## 🔍 Quick Links

### GitHub
- **Repository**: https://github.com/gwicho38/mcli
- **Issues**: https://github.com/gwicho38/mcli/issues
- **Pull Requests**: https://github.com/gwicho38/mcli/pulls
- **Releases**: https://github.com/gwicho38/mcli/releases

### Package Managers
- **PyPI**: https://pypi.org/project/mcli-framework/
- **Homebrew Tap**: https://github.com/gwicho38/homebrew-mcli

### CI/CD
- **GitHub Actions**: https://github.com/gwicho38/mcli/actions
- **Codecov**: https://codecov.io/gh/gwicho38/mcli

---

## 📝 Documentation Standards

When contributing to documentation:

1. **Format**: Use Markdown with consistent headers
2. **Links**: Use relative links for internal docs
3. **Code Blocks**: Include language identifiers for syntax highlighting
4. **Examples**: Provide working examples
5. **Version**: Note version compatibility when relevant
6. **Updates**: Update this index when adding new docs

---

## 🆘 Getting Help

Need help? Try these resources:

1. **Documentation**: Check this index and linked docs
2. **GitHub Issues**: Search existing issues or create new one
3. **README**: Review the [main README](../README.md)
4. **Contributing**: See [contributing guide](../CONTRIBUTING.md)

---

## 📧 Contact

- **Issues & Questions**: [GitHub Issues](https://github.com/gwicho38/mcli/issues)
- **Author**: Luis Fernandez de la Vara
- **Email**: luis@lefv.io

---

**Last Updated**: 2025-11-01
**Version**: 7.12.2
**Maintained By**: MCLI Contributors
