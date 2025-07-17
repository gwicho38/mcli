#!/bin/bash

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

DB_PATH="$HOME/.local/mcli/vector-store/vector_store.db"
DOCS_PATH="$HOME/.local/mcli/documents"
LOG_PATH="./app.log"
API_URL="http://localhost:3004/api/documents"

print_section() {
  echo -e "\n${BLUE}========== $1 ==========${NC}"
}

print_section "All Documents in Vector Store"
if [ -f "$DB_PATH" ]; then
  sqlite3 "$DB_PATH" "SELECT id, filename, processing_status, upload_date FROM documents;" || echo -e "${RED}No documents found${NC}"
else
  echo -e "${RED}Vector store database not found at $DB_PATH${NC}"
fi

print_section "All Embeddings in Vector Store"
if [ -f "$DB_PATH" ]; then
  sqlite3 "$DB_PATH" "SELECT id, document_id, chunk_index, LENGTH(text_chunk) as text_length FROM embeddings ORDER BY created_at DESC LIMIT 10;" || echo -e "${RED}No embeddings found${NC}"
else
  echo -e "${RED}Vector store database not found at $DB_PATH${NC}"
fi

print_section "Most Recent Document"
if [ -f "$DB_PATH" ]; then
  sqlite3 "$DB_PATH" "SELECT id, filename, processing_status, upload_date FROM documents ORDER BY created_at DESC LIMIT 1;" || echo -e "${RED}No documents found${NC}"
fi

print_section "Documents with Non-Completed Status"
if [ -f "$DB_PATH" ]; then
  sqlite3 "$DB_PATH" "SELECT id, filename, processing_status, upload_date FROM documents WHERE processing_status != 'completed';" || echo -e "${GREEN}All documents completed${NC}"
fi

print_section "Files in Documents Directory"
if [ -d "$DOCS_PATH" ]; then
  ls -lh "$DOCS_PATH"
else
  echo -e "${YELLOW}Documents directory not found at $DOCS_PATH${NC}"
fi

print_section "Vector Store Database File Info"
if [ -f "$DB_PATH" ]; then
  ls -lh "$DB_PATH"
else
  echo -e "${RED}Vector store database not found at $DB_PATH${NC}"
fi

print_section "Last 20 Lines of myAi App Log"
if [ -f "$LOG_PATH" ]; then
  tail -n 20 "$LOG_PATH"
else
  echo -e "${YELLOW}App log not found at $LOG_PATH${NC}"
fi

print_section "Output of /api/documents Endpoint"
curl -s "$API_URL" | jq . || curl -s "$API_URL"

print_section "Output of /api/documents Endpoint After 2s Wait"
sleep 2
curl -s "$API_URL" | jq . || curl -s "$API_URL" 