#!/usr/bin/env bash
#
# ibkr-flex-query.sh
#
# Run an Interactive Brokers Flex Web Service query by account and local query
# name.
#
# Usage:
#   ibkr-flex-query.sh ACCOUNT_ID QUERY_NAME
#
# Example:
#   ibkr-flex-query.sh U14269513 portfolio
#
# Configuration:
#   ~/.ibkr/flex-queries.csv
#     ACCOUNT_ID,QUERY_NAME,QUERY_ID
#
#   ~/.ibkr/flex-tokens.csv
#     ACCOUNT_ID,QUERY_TOKEN
#
# The script finds QUERY_ID from flex-queries.csv and QUERY_TOKEN from
# flex-tokens.csv, sends the Flex query request to IBKR, then downloads the
# generated statement to stdout. The statement format is controlled by the
# configured IBKR Flex query; the local portfolio query is expected to return
# CSV.

set -euo pipefail

readonly SCRIPT_NAME="$(basename "$0")"
readonly IBKR_DIR="${IBKR_DIR:-$HOME/.ibkr}"
readonly FLEX_QUERIES_FILE="${FLEX_QUERIES_FILE:-$IBKR_DIR/flex-queries.csv}"
readonly FLEX_TOKENS_FILE="${FLEX_TOKENS_FILE:-$IBKR_DIR/flex-tokens.csv}"
readonly IBKR_FLEX_BASE_URL="${IBKR_FLEX_BASE_URL:-https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService}"
readonly SEND_REQUEST_URL="$IBKR_FLEX_BASE_URL/SendRequest"
readonly GET_STATEMENT_URL="$IBKR_FLEX_BASE_URL/GetStatement"
readonly FLEX_API_VERSION="${FLEX_API_VERSION:-3}"

usage() {
  cat <<USAGE
Usage:
  $SCRIPT_NAME ACCOUNT_ID QUERY_NAME

Runs an Interactive Brokers Flex Web Service query and writes the generated
statement to stdout.

The output format is controlled by the configured IBKR Flex query. The local
portfolio query is expected to return CSV.

Arguments:
  ACCOUNT_ID   IBKR account id, for example U14269513.
  QUERY_NAME   Local query name from $FLEX_QUERIES_FILE, for example portfolio.

Configuration files:
  $FLEX_QUERIES_FILE
    CSV columns: account_id,query_name,query_id

  $FLEX_TOKENS_FILE
    CSV columns: account_id,query_token

Example:
  $SCRIPT_NAME U14269513 portfolio
USAGE
}

error() {
  printf '%s: %s\n' "$SCRIPT_NAME" "$*" >&2
}

die() {
  error "$@"
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command '$1' was not found"
}

require_readable_file() {
  local file="$1"
  local description="$2"

  [[ -e "$file" ]] || die "missing $description: $file"
  [[ -f "$file" ]] || die "$description is not a regular file: $file"
  [[ -r "$file" ]] || die "$description is not readable: $file"
}

lookup_csv_value() {
  local file="$1"
  local key1="$2"
  local key2="$3"
  local value_column="$4"

  awk -F',' -v key1="$key1" -v key2="$key2" -v value_column="$value_column" '
    function trim(value) {
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      return value
    }
    {
      first = trim($1)
      second = trim($2)

      if (first == key1 && (key2 == "" || second == key2)) {
        print trim($value_column)
        exit
      }
    }
  ' "$file"
}

extract_xml_value() {
  local tag="$1"
  local xml="$2"

  printf '%s' "$xml" | sed -n "s:.*<$tag>\\([^<]*\\)</$tag>.*:\\1:p" | head -n 1
}

require_two_arguments() {
  if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
  fi

  if [[ $# -lt 2 ]]; then
    usage >&2
    die "missing required arguments: ACCOUNT_ID and QUERY_NAME"
  fi

  if [[ $# -gt 2 ]]; then
    usage >&2
    die "too many arguments; expected exactly ACCOUNT_ID and QUERY_NAME"
  fi
}

main() {
  require_two_arguments "$@"
  require_command curl
  require_command awk
  require_command sed

  local account_id="$1"
  local query_name="$2"

  require_readable_file "$FLEX_QUERIES_FILE" "Flex queries file"
  require_readable_file "$FLEX_TOKENS_FILE" "Flex tokens file"

  local query_id
  query_id="$(lookup_csv_value "$FLEX_QUERIES_FILE" "$account_id" "$query_name" 3)"
  [[ -n "$query_id" ]] || die "no query_id found in $FLEX_QUERIES_FILE for account_id '$account_id' and query_name '$query_name'"

  local query_token
  query_token="$(lookup_csv_value "$FLEX_TOKENS_FILE" "$account_id" "" 2)"
  [[ -n "$query_token" ]] || die "no query token found in $FLEX_TOKENS_FILE for account_id '$account_id'"

  local send_response
  send_response="$(
    curl --fail --silent --show-error --get \
      --data-urlencode "t=$query_token" \
      --data-urlencode "q=$query_id" \
      --data-urlencode "v=$FLEX_API_VERSION" \
      "$SEND_REQUEST_URL"
  )" || die "failed to send Flex query request to IBKR"

  local status
  status="$(extract_xml_value Status "$send_response")"

  if [[ "$status" != "Success" ]]; then
    local error_code error_message
    error_code="$(extract_xml_value ErrorCode "$send_response")"
    error_message="$(extract_xml_value ErrorMessage "$send_response")"

    [[ -n "$error_code" ]] || error_code="$(extract_xml_value code "$send_response")"
    [[ -n "$error_message" ]] || error_message="$(extract_xml_value message "$send_response")"

    if [[ -n "$error_code" || -n "$error_message" ]]; then
      die "IBKR rejected the Flex query request${error_code:+ (code $error_code)}${error_message:+: $error_message}"
    fi

    die "IBKR Flex query request did not return Success"
  fi

  local reference_code
  reference_code="$(extract_xml_value ReferenceCode "$send_response")"
  [[ -n "$reference_code" ]] || die "IBKR Flex query response did not include a ReferenceCode"

  curl --fail --silent --show-error --get \
    --data-urlencode "t=$query_token" \
    --data-urlencode "q=$reference_code" \
    --data-urlencode "v=$FLEX_API_VERSION" \
    "$GET_STATEMENT_URL" || die "failed to download Flex statement from IBKR"
}

main "$@"
