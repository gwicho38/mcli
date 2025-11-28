"""Storage-related constants for MCLI storage abstraction layer."""

from mcli.lib.constants.paths import DirNames


class StorageEnvVars:
    """Environment variable names for storage configuration."""

    # Backend selection
    STORAGE_BACKEND = "STORAGE_BACKEND"  # ipfs, supabase, sqlite

    # Encryption
    ENCRYPTION_KEY = "MCLI_ENCRYPTION_KEY"  # Master encryption key

    # IPFS/Storacha configuration
    STORACHA_ENABLED = "MCLI_STORACHA_ENABLED"  # Enable network sync (default: true)
    STORACHA_EMAIL = "STORACHA_EMAIL"  # User email
    STORACHA_SPACE_DID = "STORACHA_SPACE_DID"  # Space DID
    STORACHA_API_KEY = "STORACHA_API_KEY"  # API key (if required)

    # Supabase (legacy)
    SUPABASE_URL = "SUPABASE_URL"
    SUPABASE_ANON_KEY = "SUPABASE_ANON_KEY"
    SUPABASE_SERVICE_ROLE_KEY = "SUPABASE_SERVICE_ROLE_KEY"


class StoragePaths:
    """Storage-related path constants."""

    # Cache directories (relative to home)
    STORAGE_CACHE_DIR = f"{DirNames.MCLI}/storage-cache"
    STORACHA_CONFIG_FILE = f"{DirNames.MCLI}/storacha-config.json"
    STORAGE_METADATA_FILE = f"{DirNames.MCLI}/storage-metadata.json"


class StorageDefaults:
    """Default values for storage configuration."""

    # Backend defaults
    DEFAULT_BACKEND = "ipfs"
    STORACHA_ENABLED_DEFAULT = "true"

    # IPFS/Storacha
    STORACHA_API_BASE = "https://api.storacha.network"  # Placeholder
    STORACHA_GATEWAY_BASE = "https://{cid}.ipfs.storacha.link"
    STORACHA_HTTP_BRIDGE_URL = "https://up.storacha.network/bridge"

    # Cache settings
    CACHE_MAX_AGE_DAYS = 30
    CACHE_CLEANUP_INTERVAL_HOURS = 24

    # Timeouts
    DOWNLOAD_TIMEOUT_SECONDS = 30
    UPLOAD_TIMEOUT_SECONDS = 60
    HEALTH_CHECK_TIMEOUT_SECONDS = 5


class StorachaBridgeCapabilities:
    """Storacha HTTP Bridge capabilities for UCAN delegation."""

    STORE_ADD = "store/add"
    STORE_LIST = "store/list"
    STORE_REMOVE = "store/remove"
    UPLOAD_ADD = "upload/add"
    UPLOAD_LIST = "upload/list"
    UPLOAD_REMOVE = "upload/remove"
    SPACE_BLOB_ADD = "space/blob/add"
    SPACE_INDEX_ADD = "space/index/add"
    FILECOIN_OFFER = "filecoin/offer"

    # Common capability sets
    UPLOAD_CAPABILITIES = [
        SPACE_BLOB_ADD,
        SPACE_INDEX_ADD,
        FILECOIN_OFFER,
        UPLOAD_ADD,
    ]
    READ_CAPABILITIES = [UPLOAD_LIST, STORE_LIST]
    ALL_CAPABILITIES = UPLOAD_CAPABILITIES + READ_CAPABILITIES + [UPLOAD_REMOVE, STORE_REMOVE]


class StorachaHTTPHeaders:
    """HTTP headers for Storacha bridge API."""

    X_AUTH_SECRET = "X-Auth-Secret"
    AUTHORIZATION = "Authorization"
    CONTENT_TYPE = "Content-Type"
    CONTENT_TYPE_DAG_JSON = "application/vnd.ipld.dag-json"
    CONTENT_TYPE_DAG_CBOR = "application/vnd.ipld.dag-cbor"


class StorageMessages:
    """User-facing messages for storage operations."""

    # Success messages
    CONNECTED_STORACHA = "✅ Connected to Storacha"
    CONNECTED_SUPABASE = "✅ Connected to Supabase"
    UPLOADED_TO_STORACHA = "📤 Uploaded to Storacha: {cid}"
    DOWNLOADED_FROM_STORACHA = "📥 Downloaded from Storacha: {cid}"
    CACHED_LOCALLY = "📦 Cached locally: {cid}"
    STORACHA_ENABLED = "✅ Storacha network sync enabled"
    STORACHA_DISABLED = "⏸️  Storacha network sync disabled (using local cache only)"

    # Info messages
    CACHE_HIT = "Cache hit: {cid} ({size} bytes)"
    CACHE_MISS = "Cache miss: {cid}"
    USING_CACHE_ONLY = "Storacha disabled, using local cache only"
    NOT_AUTHENTICATED = "Not authenticated, using local cache only"
    GATEWAY_URL = "   Gateway: {url}"
    REGISTRY_UPLOADED = "   📝 Registry uploaded for {repo}/{env}"

    # Warning messages
    STORACHA_UPLOAD_FAILED = "⚠️  Storacha upload failed: {error}"
    DATA_CACHED_LOCALLY = "   Data is cached locally"
    NOT_AUTHENTICATED_WARNING = "Not authenticated with Storacha. Run: mcli storage login <email>"
    NO_ENCRYPTION_KEY = (
        "No MCLI_ENCRYPTION_KEY found, generating random key.\n"
        "💡 Set MCLI_ENCRYPTION_KEY to use the same key across sessions."
    )
    INVALID_BACKEND = "Invalid STORAGE_BACKEND: {backend}, defaulting to IPFS"

    # Storacha CLI integration
    STORACHA_CLI_NOT_FOUND = "Storacha CLI not found. Install with: npm install -g @storacha/cli"
    STORACHA_SENDING_VERIFICATION = "📧 Sending verification email to {email}..."
    STORACHA_CHECK_EMAIL = "   Check your inbox and click the verification link."
    STORACHA_LOGIN_SUCCESS = "✅ Successfully logged in to Storacha"
    STORACHA_LOGIN_FAILED = "❌ Login failed: {error}"
    STORACHA_SPACE_CREATED = "✅ Created space: {space_did}"
    STORACHA_SPACE_SELECTED = "✅ Selected space: {space_did}"
    STORACHA_NO_SPACES = "No spaces found. Create one with: mcli storage space create"
    STORACHA_TOKENS_GENERATED = "✅ Bridge tokens generated and saved"
    STORACHA_TOKENS_EXPIRED = "⚠️  Bridge tokens expired, regenerating..."
    STORACHA_AGENT_DID = "Agent DID: {did}"
    STORACHA_SPACE_DID = "Space DID: {did}"

    # Error messages
    STORACHA_LOGIN_NOT_IMPLEMENTED = (
        "Storacha login requires the storacha CLI.\n\n"
        "📦 Install: npm install -g @storacha/cli\n"
        "🔐 Login:   storacha login {email}\n"
        "📁 Create:  storacha space create\n"
        "🔗 Generate tokens: mcli storage setup"
    )
    STORACHA_UPLOAD_NOT_IMPLEMENTED = (
        "Storacha upload not yet implemented.\n\n"
        "📝 TODO: Implement Storacha HTTP API upload\n"
        "   See: https://docs.storacha.network/how-to/http-bridge/"
    )
    BACKEND_NOT_IMPLEMENTED = "{backend} backend not yet implemented"
    ENCRYPTION_FAILED = "Encryption failed: {error}"
    DECRYPTION_FAILED = "Decryption failed: {error}"
    INVALID_ENCRYPTED_FORMAT = "Invalid encrypted data format: expected 'IV:data'"
    CACHE_STORE_FAILED = "Failed to store in cache: {error}"
    CACHE_RETRIEVE_FAILED = "Failed to retrieve from cache: {error}"
    GATEWAY_DOWNLOAD_FAILED = "Gateway download failed for {cid}: {error}"
    DATA_NOT_FOUND = "Data not in cache and Storacha unavailable: {cid}"


class StorageContentTypes:
    """Content types for stored data."""

    # Data types
    TRADING_DISCLOSURE = "trading_disclosure"
    POLITICIAN_INFO = "politician_info"
    ML_PREDICTION = "ml_prediction"
    ML_MODEL = "ml_model"
    PORTFOLIO_DATA = "portfolio_data"
    DATA_PULL_JOB = "data_pull_job"

    # Registry
    REGISTRY = "registry"

    # Generic
    ENCRYPTED_BINARY = "encrypted_binary"
    JSON_DATA = "json_data"
