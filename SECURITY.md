# Security Policy

## Overview

MCLI (Portable Workflow Framework) is a modular CLI framework that enables workflow automation, AI chat integration, and extensible command execution. As MCLI handles user workflows, API credentials, and integrates with external services (OpenAI, Anthropic, Supabase, MLflow), security is paramount.

## Supported Versions

The following versions of MCLI are currently supported with security updates:

| Version | Supported          | Notes                                    |
| ------- | ------------------ | ---------------------------------------- |
| 7.9.x   | :white_check_mark: | Current stable release                   |
| 7.8.x   | :white_check_mark: | Previous stable release                  |
| 7.7.x   | :warning:          | Critical security patches only           |
| < 7.7   | :x:                | No longer supported - upgrade required   |

**Security Update Policy:**
- Current minor version (7.9.x) receives immediate security patches
- Previous minor version (7.8.x) receives critical and high-severity patches for 90 days
- Two versions back (7.7.x) receives critical-only patches for 30 days
- Older versions receive no security updates - users must upgrade

**Python Version Support:**
- Python 3.9-3.12 supported
- Security patches will be tested on all supported Python versions
- EOL Python versions may lose support in future releases

## Security Features

MCLI implements security controls across multiple layers:

### Command Execution & Validation
- **Workflow sandboxing** - User workflows execute in isolated contexts
- **Input validation** - All CLI arguments and options are validated before processing
- **Command injection prevention** - Shell commands are properly escaped and validated
- **Path traversal protection** - File operations validate paths to prevent directory traversal

### API & Credentials Management
- **Environment-based secrets** - API keys stored in `.env` files (not committed to git)
- **API key validation** - Required credentials validated at startup
- **OAuth support** - For services requiring OAuth flows
- **Token rotation** - Support for token refresh and rotation mechanisms
- **Secure storage** - Credentials never logged or exposed in error messages

### Network Security
- **HTTPS enforcement** - All external API calls use HTTPS
- **TLS verification** - Certificate validation enabled by default
- **Rate limiting** - Client-side rate limiting for API calls
- **Timeout controls** - Network requests have configurable timeouts
- **Proxy support** - Respects HTTP_PROXY/HTTPS_PROXY environment variables

### Data Protection
- **No telemetry by default** - User workflows and data stay local
- **Opt-in analytics** - Any analytics require explicit user consent
- **Data encryption** - Sensitive data encrypted at rest when using database features
- **Secure temporary files** - Temporary files created with secure permissions (0600)
- **Memory cleanup** - Sensitive data cleared from memory after use

### Dependency Security
- **Dependency pinning** - All dependencies version-pinned in `pyproject.toml`
- **Security scanning** - Automated scans via Bandit, Safety, and GitHub Actions
- **Regular updates** - Dependencies updated regularly for security patches
- **Minimal dependencies** - Core functionality has minimal required dependencies
- **Optional extras** - Heavy/risky dependencies are optional (ml, gpu, monitoring)

### Build & Distribution
- **Signed releases** - PyPI releases signed and verified
- **Hash verification** - Package hashes published with releases
- **Reproducible builds** - Build process documented and reproducible
- **Binary security** - Portable executables built with security flags enabled

## Reporting a Vulnerability

We take security reports seriously and appreciate responsible disclosure. If you discover a security vulnerability in MCLI, please follow these guidelines:

### Where to Report

**DO NOT** create public GitHub issues for security vulnerabilities. Use private channels:

1. **GitHub Security Advisories** (Preferred):
   - Navigate to https://github.com/gwicho38/mcli/security/advisories
   - Click "Report a vulnerability"
   - Complete the security advisory form with detailed information

2. **Email**: luis@lefv.io
   - Subject line: "[SECURITY] MCLI Vulnerability Report"
   - Include "SECURITY" tag for priority routing
   - PGP encryption available upon request for sensitive disclosures

### What to Include

To help us understand and address the issue effectively, please provide:

- **Vulnerability Description**
  - Clear explanation of the security issue
  - Attack vector and exploitation scenario
  - Potential impact on users

- **Affected Components**
  - Affected versions (e.g., "all versions >= 7.0.0")
  - Specific modules/commands affected
  - Platform/OS specifics (if applicable)

- **Reproduction Steps**
  - Detailed step-by-step instructions
  - Sample code or commands to reproduce
  - Required environment setup
  - Expected vs. actual behavior

- **Proof of Concept**
  - Working exploit code (if available)
  - Screenshots or video demonstration
  - Sample vulnerable workflows
  - Attack payloads or test cases

- **Impact Assessment**
  - Severity rating (if you have one)
  - Confidentiality/Integrity/Availability impact
  - Likelihood of exploitation
  - Potential mitigations

- **Your Information**
  - Name/handle for credit (optional - can remain anonymous)
  - Contact information for follow-up
  - Affiliation (if applicable)
  - Preferred disclosure timeline

### Response Timeline

We commit to the following response times:

| Timeline        | Action                                                          |
| --------------- | --------------------------------------------------------------- |
| **24 hours**    | Initial acknowledgment of report receipt                        |
| **72 hours**    | Preliminary assessment and severity classification              |
| **5 days**      | Detailed response with fix timeline or rejection reason         |
| **14 days**     | Patch development for critical vulnerabilities                  |
| **30 days**     | Patch release for critical vulnerabilities                      |
| **60 days**     | Patch release for high-severity vulnerabilities                 |
| **90 days**     | Patch release for medium/low vulnerabilities                    |

**Note:** Critical vulnerabilities being actively exploited will be expedited (target: 7-day patch release).

### Severity Classification

We follow CVSS 3.1 scoring with the following severity levels:

**Critical (9.0-10.0)**
- Remote code execution without authentication
- Complete system compromise
- Mass data exfiltration
- Credential theft affecting all users

**High (7.0-8.9)**
- Remote code execution requiring authentication
- Authentication bypass vulnerabilities
- Privilege escalation to admin/root
- Sensitive data exposure (API keys, credentials)
- SQL injection or command injection

**Medium (4.0-6.9)**
- Cross-site scripting (XSS) in dashboards
- CSRF vulnerabilities
- Information disclosure (limited scope)
- Denial of service (local)
- Workflow sandbox escape

**Low (0.1-3.9)**
- Security misconfigurations
- Minor information leaks
- Non-exploitable crashes
- Theoretical vulnerabilities requiring unlikely preconditions

### What to Expect

**If the vulnerability is accepted:**

1. **Acknowledgment Phase**
   - We confirm receipt and begin triage
   - We may ask clarifying questions
   - We establish a communication channel for updates

2. **Investigation Phase**
   - We reproduce the vulnerability in our test environment
   - We assess the full scope and impact
   - We identify affected versions and components
   - We develop a fix and test thoroughly

3. **Coordination Phase**
   - We coordinate disclosure timeline with you
   - We prepare security advisory and CVE request (if applicable)
   - We develop patch and backport to supported versions
   - We prepare mitigation guidance for users

4. **Release Phase**
   - We release patched versions to PyPI
   - We publish security advisory with details
   - We credit you in advisory and CHANGELOG (unless you prefer anonymity)
   - We notify users via GitHub releases and security mailing list

5. **Post-Release**
   - We monitor for exploit attempts
   - We provide additional guidance if needed
   - We incorporate lessons learned into development practices

**If the vulnerability is declined:**

1. We provide a detailed explanation of why it doesn't meet our security criteria
2. We may still implement hardening measures if it's security-adjacent
3. We may improve documentation to clarify expected behavior
4. You are free to publish after 7 days (we request advance notice)

### Coordinated Disclosure

We practice coordinated vulnerability disclosure:

- **Default embargo**: 90 days from initial report
- **Negotiable timelines**: We're flexible based on severity and circumstances
- **Early disclosure**: Critical vulnerabilities may be disclosed earlier if actively exploited
- **Public disclosure**: After patch release, we publish full details in security advisory
- **Acknowledgment**: Security researchers are credited unless they prefer anonymity

### Bug Bounty Program

MCLI does not currently have a paid bug bounty program. However, we offer:

- **Public recognition** in security advisories and CHANGELOG
- **Hall of Fame** listing in SECURITY.md (if desired)
- **Early access** to new features and beta releases
- **Direct collaboration** with maintainers on security improvements

We may introduce a paid bounty program in the future as the project grows.

## Security Best Practices for Users

### Installation & Updates

**Secure Installation:**
```bash
# Install from official PyPI only
pip install mcli-framework

# Or with UV (recommended)
uv pip install mcli-framework

# Verify installation
mcli version
```

**Verify Package Integrity:**
```bash
# Check for security vulnerabilities in dependencies
pip check

# Audit installed packages
pip-audit  # If pip-audit is installed
```

**Keep MCLI Updated:**
```bash
# Update to latest version
pip install --upgrade mcli-framework

# Or with mcli self-update
mcli self update

# Subscribe to security advisories
# Watch https://github.com/gwicho38/mcli/security/advisories
```

### Environment Configuration

**Protect API Credentials:**
```bash
# Create .env from example
cp .env.example .env

# Set secure file permissions
chmod 600 .env

# NEVER commit .env to version control
echo ".env" >> .gitignore

# Use environment-specific files
.env.development
.env.staging
.env.production  # Most restrictive permissions
```

**Required Environment Variables (Production):**
```bash
# Set environment
MCLI_ENV=production

# Disable debug mode
DEBUG=false

# API credentials (generate securely)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Database credentials (if using database features)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key  # Keep highly secure

# Disable tracing in production
MCLI_TRACE_LEVEL=0
```

**Security Hardening:**
```bash
# Restrict network access (if applicable)
MCLI_ALLOW_EXTERNAL_COMMANDS=false

# Enable auto-optimization (includes security checks)
MCLI_AUTO_OPTIMIZE=true

# Set strict timeouts
MCLI_REQUEST_TIMEOUT=30
```

### Workflow Security

**Secure Workflow Development:**

1. **Validate Input**: Always validate and sanitize user input in workflows
   ```python
   import click
   import re

   @click.command()
   @click.argument('filename')
   def my_workflow(filename):
       # Validate filename to prevent path traversal
       if '..' in filename or filename.startswith('/'):
           raise click.BadParameter('Invalid filename')
       # Process file safely
   ```

2. **Avoid Shell Injection**: Use Python APIs instead of shell commands
   ```python
   # BAD - vulnerable to injection
   import os
   os.system(f"rm {user_input}")

   # GOOD - safe API
   import pathlib
   pathlib.Path(user_input).unlink()
   ```

3. **Secrets in Workflows**: Never hardcode secrets in workflow files
   ```python
   # BAD
   API_KEY = "sk-1234567890"

   # GOOD - use environment variables
   import os
   API_KEY = os.getenv('API_KEY')
   if not API_KEY:
       raise ValueError('API_KEY not set')
   ```

4. **Validate Workflow Imports**: Review imported workflows before executing
   ```bash
   # Review workflow before importing
   cat untrusted-workflow.json

   # Import only from trusted sources
   mcli commands import trusted-workflows.json

   # Verify lockfile matches
   mcli commands verify
   ```

### Daemon & Scheduler Security

**Secure Daemon Configuration:**
```bash
# Run daemon with minimal privileges
# Don't run as root/administrator

# Review scheduled workflows before adding
mcli workflow scheduler list

# Audit daemon logs regularly
cat ~/.mcli/logs/daemon.log
```

**Scheduler Best Practices:**
- Only schedule workflows from trusted sources
- Review scheduled commands before activation
- Use absolute paths in scheduled commands
- Set appropriate timeouts for scheduled jobs
- Monitor scheduler logs for anomalies

### Dashboard Security

**When using ML/Streamlit dashboards:**

```bash
# Bind to localhost only (not 0.0.0.0)
STREAMLIT_SERVER_ADDRESS=127.0.0.1

# Use authentication if exposing dashboard
# Enable HTTPS if accessible remotely
# Use VPN or SSH tunnel for remote access
```

### Database Security

**Supabase/PostgreSQL Best Practices:**

- Use **service role key** only in trusted environments
- Prefer **anon key** with Row Level Security (RLS) policies
- Enable **SSL/TLS** for database connections
- Use **connection pooling** to prevent exhaustion attacks
- Implement **rate limiting** on database operations
- **Encrypt backups** of database credentials

### Development Best Practices

**For MCLI Developers:**

1. **Code Review**: All changes reviewed for security implications
2. **Dependency Audits**: Run `make security-check` before commits
3. **Static Analysis**: Use Bandit, MyPy, and Ruff for security scanning
4. **Input Validation**: Validate all external input (CLI args, API responses, file contents)
5. **Error Handling**: Never expose sensitive data in error messages
6. **Logging**: Don't log credentials, API keys, or sensitive user data
7. **Testing**: Include security test cases for all features

**Pre-commit Checklist:**
```bash
make lint              # Code quality checks
make type-check        # Type safety validation
make security-check    # Security scanning (bandit, safety)
make test-cov          # Test coverage (80% minimum)
```

## Security Measures

### Automated Scanning

MCLI uses multiple security tools:

1. **Dependabot**: Automated dependency updates
2. **Bandit**: Python security linter
3. **Safety**: Known vulnerability checker
4. **Trivy**: Container and filesystem scanner
5. **TruffleHog**: Secret scanning
6. **detect-secrets**: Pre-commit secret detection

### Pre-commit Hooks

Security checks run automatically before each commit:
```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### CI/CD Security

All pull requests and commits to main branch trigger:
- Dependency vulnerability scanning
- Code security analysis
- Secret detection
- SARIF upload to GitHub Security

## Known Security Considerations

### Architecture & Design Limitations

1. **Workflow Execution Trust Model**
   - MCLI executes workflows with the same privileges as the user
   - No sandbox isolation between workflows
   - Workflows can access the entire filesystem
   - **Mitigation**: Only import workflows from trusted sources

2. **API Key Storage**
   - API keys stored in plaintext `.env` files
   - Environment variables visible to all user processes
   - **Mitigation**: Use OS-level encryption (FileVault, BitLocker), restrict `.env` permissions (chmod 600)

3. **Command Discovery Mechanism**
   - Commands auto-discovered from specific directories
   - Malicious files in `~/.mcli/commands/` could be executed
   - **Mitigation**: Review all imported workflows, use lockfile verification

4. **External Service Dependencies**
   - Security depends on third-party APIs (OpenAI, Anthropic, Supabase)
   - Network compromise could expose API calls
   - **Mitigation**: Use HTTPS, verify TLS certificates, monitor for unauthorized access

5. **Python Code Execution**
   - Workflows are Python code executed directly
   - No static analysis before execution
   - **Mitigation**: Code review before importing, use `mcli commands info` to inspect workflows

6. **ML Model Security**
   - ML models loaded from disk can execute arbitrary code (pickle)
   - Adversarial inputs could poison models
   - **Mitigation**: Only load models from trusted sources, use safetensors format when possible

### Optional Dependencies

MCLI uses optional dependencies (ollama, redis, etc.). If not installed:
- Features gracefully degrade
- Clear error messages are shown
- No security implications from missing dependencies

### ML Features

When using `mcli[ml]` extras:
- Review model inputs for injection attacks
- Validate financial data sources
- Use secure connections to databases
- Enable authentication for model serving
- Monitor for data poisoning attempts

### Out of Scope

The following are **not** covered by this security policy:

- **Operating system vulnerabilities** (keep your OS updated)
- **Python interpreter vulnerabilities** (use supported Python versions)
- **Third-party service breaches** (OpenAI, Anthropic, Supabase, etc.)
- **Social engineering** targeting users to run malicious workflows
- **Physical access attacks** to user's machine
- **Denial of service via resource exhaustion** (use OS-level resource limits)
- **Vulnerabilities in user-written workflows** (user's responsibility to secure)
- **Supply chain attacks on PyPI** (use pip verification tools)
- **Compromised dependencies** (we address via audits, but can't prevent all scenarios)

## Security Disclosure History

Public security advisories will be listed here after coordinated disclosure:

- **No security advisories yet** - MCLI is under active security hardening

Future advisories will include:
- CVE identifier (if applicable)
- Affected versions
- Severity rating
- Description and impact
- Patches and mitigations
- Credit to reporter(s)

See our [CHANGELOG](CHANGELOG.md) for all security-related fixes and improvements.

## Security Hall of Fame

We recognize security researchers who have helped improve MCLI's security:

- *List will be populated as vulnerabilities are reported and fixed*

Thank you to all researchers who practice responsible disclosure!

## Security Configurations

### Production Deployment

When deploying to production:

1. ✅ Use `.env.production.example` as a template
2. ✅ Store secrets in a secrets manager
3. ✅ Enable SSL/TLS
4. ✅ Set `DEBUG=false`
5. ✅ Restrict CORS origins
6. ✅ Enable authentication
7. ✅ Use strong passwords and secrets
8. ✅ Configure monitoring and alerts
9. ✅ Enable audit logging
10. ✅ Regular security updates

### API Key Management

- Store in environment variables, not in code
- Use different keys for dev/staging/production
- Rotate keys quarterly or after any suspected compromise
- Monitor usage for anomalies
- Revoke unused or old keys

## Security Resources

### Internal Resources
- **Contributing Guide**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Development Guide**: [CLAUDE.md](CLAUDE.md)
- **Issue Tracker**: https://github.com/gwicho38/mcli/issues (non-security only)

### External Resources
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CWE Database**: https://cwe.mitre.org/
- **CVSS Calculator**: https://www.first.org/cvss/calculator/3.1
- **Python Security**: https://python.readthedocs.io/en/stable/library/security_warnings.html

### Security Tools
- **Bandit**: Python security scanner (included in dev dependencies)
- **Safety**: Dependency vulnerability scanner
- **pip-audit**: Audit Python packages for vulnerabilities
- **Trivy**: Container and filesystem vulnerability scanner

## Security Contact

- **Security Lead**: Luis Fernandez de la Vara (luis@lefv.io)
- **GitHub Security**: https://github.com/gwicho38/mcli/security/advisories
- **General Issues**: https://github.com/gwicho38/mcli/issues (non-security only)
- **Documentation**: https://github.com/gwicho38/mcli#readme

## Acknowledgments

We are committed to security through:
- **Transparent disclosure** of all security issues
- **Timely patches** for supported versions
- **Community collaboration** with security researchers
- **Continuous improvement** of security practices

Thank you for helping keep MCLI and its users secure!

---

**Last Updated**: 2025-10-19
**Policy Version**: 1.0.0
**MCLI Version**: 7.9.6
