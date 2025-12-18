# Dependency Refactoring Plan

## Current Issues
- All 328+ dependencies installed by default
- Heavy ML libraries (torch, tensorflow, streamlit, etc.) always installed
- Large installation size and slow startup
- Security surface area larger than needed

## Proposed Structure

### Core Dependencies (Always Installed)
```
# CLI Framework
click>=8.1.7,<9.0.0
rich>=14.0.0
requests>=2.31.0,<3.0.0
tomli>=2.2.1
python-dotenv>=1.1.1

# Core utilities
watchdog>=3.0.0,<4.0.0
tqdm>=4.66.1,<5.0.0
humanize>=4.9.0,<5.0.0
psutil>=5.9.0,<6.0.0
inquirerpy>=0.3.4,<0.4.0
gitpython>=3.1.40,<4.0.0
prompt-toolkit>=3.0.0,<4.0.0

# Basic HTTP/async support
aiohttp>=3.9.0
httpx>=0.28.1
websockets>=12.0

# Data parsing
beautifulsoup4>=4.13.5
fuzzywuzzy>=0.18.0

# Chat and AI capabilities
openai>=1.3.0,<2.0.0
anthropic>=0.60.0
ipython>=8.12.0,<9.0.0

# Configuration
pydantic-settings>=2.1.0
dynaconf>=3.2.0
```

### Optional Extras

#### `[ml]` - Machine Learning
```
torch>=2.0.0
torchvision>=0.15.0
pytorch-lightning>=2.0.0
scikit-learn>=1.3.0,<2.0.0
mlflow>=2.9.0
dvc>=3.0.0
optuna>=3.4.0
polars>=0.19.0
pyarrow>=14.0.0
numpy>=1.24.0,<2.0.0
pandas>=2.3.1
scipy>=1.10.0
```

#### `[dashboard]` - Dashboards & Visualization
```
streamlit>=1.50.0
altair>=4.2.1,<5.0.0
matplotlib>=3.9.4
plotly>=5.17.0
seaborn>=0.13.0
graphviz>=0.21
pydot>=4.0.1
```

#### `[trading]` - Trading & Finance
```
yfinance>=0.2.18
alpha-vantage>=2.3.1
alpaca-py==0.43.2
cvxpy>=1.4.0
PyPortfolioOpt>=1.5.5
```

#### `[data]` - Data Processing & Documents
```
opencv-python>=4.11.0.86
pillow>=11.2.1
scikit-image>=0.24.0
pypdf2>=3.0.1
pymupdf>=1.26.3
openpyxl>=3.1.5
numpy>=1.24.0,<2.0.0
pandas>=2.3.1
scipy>=1.10.0
```

#### `[database]` - Database Support
```
supabase>=2.8.1
sqlalchemy>=2.0.0
alembic>=1.12.0
psycopg2-binary>=2.9.7
asyncpg>=0.29.0
```

#### `[server]` - API Server & Production
```
fastapi>=0.110.0
uvicorn>=0.27.0
uvloop>=0.19.0
aiosqlite>=0.20.0
redis>=5.0.0
aiohttp-sse-client>=0.2.1
aiomqtt>=2.0.0
gunicorn>=21.2.0
prometheus-client>=0.19.0
structlog>=23.2.0
newrelic>=9.2.0
datadog>=0.49.0
orjson>=3.9.0
kafka-python>=2.0.2
```

#### `[dev]` - Development Tools
```
# All current dev dependencies
pytest>=8.4.1
pytest-cov>=4.1.0,<5.0.0
black>=23.0.0
isort>=5.12.0,<6.0.0
mypy>=1.7.1,<2.0.0
pre-commit>=4.5.1
```

## Implementation Strategy

### Phase 1: Core Dependencies (Week 1)
1. **Identify truly essential dependencies**
2. **Move heavy libraries to appropriate extras**
3. **Test minimal installation**
4. **Ensure core functionality works**

### Phase 2: Feature Detection (Week 2)
1. **Add graceful feature detection**
2. **Helpful error messages when features missing**
3. **Suggest installation commands for missing extras**

### Phase 3: Documentation & UX (Week 3)
1. **Update installation documentation**
2. **Add installation commands to error messages**
3. **Update README with installation options**

## Expected Benefits

### Installation Size
- **Current**: ~500MB+ full installation
- **Core only**: ~50-100MB
- **With extras**: User chooses what to install

### Startup Performance
- **Current**: 2-3 seconds (loading all libraries)
- **Core only**: <1 second for basic commands
- **With extras**: Only when features used

### User Experience
- **New users**: Fast install, basic functionality
- **Power users**: Install only what they need
- **CI/CD**: Install only required dependencies

## Migration Plan

### Backward Compatibility
- Keep current behavior for existing installs
- Default to full installation for pip install
- Add --minimal flag for new installs
- Allow selective extra installation

### Communication
- Update changelog with migration guide
- Add installation options to documentation
- Provide upgrade path for existing users

This refactoring will significantly improve user experience while maintaining full compatibility."