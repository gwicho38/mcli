# shellcheck shell=bash

deleteAllKeys() {
  # shellcheck disable=SC2154
  rm "$PUBLIC_KEY_PATH" 2>/dev/null
  # shellcheck disable=SC2154
  rm "$PRIVATE_KEY_PATH" 2>/dev/null
}

generateKeyPair() {
  mkdir -p ~/.mclidev/keys/
  # shellcheck disable=SC2154
  touch "$TEMP_PUBLIC_KEY_PATH"
  # shellcheck disable=SC2154
  touch "$TEMP_PRIVATE_KEY_PATH"
  openssl genpkey -algorithm RSA-PSS -out "$TEMP_PRIVATE_KEY_PATH" -pkeyopt rsa_pss_keygen_md:sha256 -pkeyopt rsa_pss_keygen_mgf1_md:sha256 -pkeyopt rsa_keygen_bits:4096 -pkeyopt rsa_pss_keygen_saltlen:64 2>/dev/null
  openssl rsa -in "$TEMP_PRIVATE_KEY_PATH" -pubout -out "$TEMP_PUBLIC_KEY_PATH" 2>/dev/null
}

generateSignature() {
  nonce=$(($(date +'%s * 1000 + %-N / 1000000')))
  signature=$(echo $nonce | openssl dgst -hex -sigopt rsa_padding_mode:pss -sha256 -sign "$1")
  signature=$(sed -r 's/SHA2-256\(stdin\)= (.*)/\1/' <<<"$signature")
  nonce=$(echo $nonce | xxd -p)
}

setIdpConfig

# shellcheck disable=SC2154
action=${args[action]}

if [[ "$action" == "delete" ]]; then
  if confirm "Are you sure you want to delete keys?"; then
    deleteAllKeys
  fi
  exit
fi

if [[ -e $PRIVATE_KEY_PATH && -e $PUBLIC_KEY_PATH ]]; then
  if confirm "Keys have already been provisioned. Overwrite?"; then
    echo "Overwriting keys"
    deleteAllKeys
  fi
fi

getRedirectUrl

# shellcheck disable=SC2154
[[ "$new_url" == *'id_token='* ]] || {
  error "No id_token recognized"
  exit 1
}

# ------- parse state and id_token from new_url -------
state=$(sed -r 's/.*[^_]state=([^&]*).*/\1/' <<<"$new_url")
id_token=$(sed -r 's/.*id_token=([^&]*).*/\1/' <<<"$new_url")

#------- send id_token and state to /oidc/login -------
login_url="$MCLI_DOMAIN/oidc/login"
content_type='application/x-www-form-urlencoded'
accept='application/json'
resp=$(curl --header "Content-Type: $content_type" --data-urlencode "id_token=$id_token" --data-urlencode "state=$state" --header "Accept:$accept" "$login_url" -s -i)
session_token=$(echo $resp | awk -F'mcliauth=|;' '{print $2}')
# ------- generate key pair & signature -------
generateKeyPair
generateSignature "$TEMP_PRIVATE_KEY_PATH"

# ------- get current User -------
get_user_url="$MCLI_DOMAIN/api/8/User/myUser"
user=$(curl --header "Accept:$accept" --header "Cookie:mcliauth=$session_token" "$get_user_url" -s)

# ------- send public key to /user/setPublicKey -------
public_key=$(awk '{printf "%s\\n", $0}' "$TEMP_PUBLIC_KEY_PATH")
set_key_url="$MCLI_DOMAIN/api/8/User/setPublicKey"
resp=$(curl --header "Accept:$accept" --header "Cookie:mcliauth=$session_token" --data-raw "[$user,\"$public_key\"]" "$set_key_url" -s -i)
if [[ "$resp" == *'Error'* ]]; then
  echo 'Signature verification failed'
else
  # ------- store userid -------
  userid=$(echo "$user" | jq -r '.id')
  # shellcheck disable=SC2154
  touch "$USER_INFO_PATH"
  echo "$userid" >"$USER_INFO_PATH"
  cat "$TEMP_PUBLIC_KEY_PATH" >"$PUBLIC_KEY_PATH"
  cat "$TEMP_PRIVATE_KEY_PATH" >"$PRIVATE_KEY_PATH"
  echo 'Successfully provisioned keys'
fi

rm "$TEMP_PUBLIC_KEY_PATH"
rm "$TEMP_PRIVATE_KEY_PATH"
