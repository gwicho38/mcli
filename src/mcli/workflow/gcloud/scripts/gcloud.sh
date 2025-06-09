#! /usr/bin/env bash



start() {
  echo "Stopping gcloud..."
  gcloud workstations start \
  --project=remote-ws-88 \
  --cluster=cluster-cirrus-ws \
  --config=config-cirrus-ws \
  --region=us-west1 \
  apps-luis-fernandez-de-la-vara
}

stop() {
  echo "Stopping gcloud..."
  gcloud alpha workstations stop \
    --project=remote-ws-88 \
    --cluster=cluster-cirrus-ws \
    --config=config-cirrus-ws \
    --region=us-west1 \
    apps-luis-fernandez-de-la-vara;
}

tunnel() {

  echo "${1} and ${2}"

  # gcloud alpha workstations start-tcp-tunnel \
  #   --project=remote-ws-88 \
  #   --cluster=cluster-cirrus-ws \
  #   --config=config-cirrus-ws \
  #   --region=us-west1 \
  #   apps-luis-fernandez-de-la-vara 22 \
  #   --local-host-port=:2222

  gcloud alpha workstations start-tcp-tunnel \
    --project=remote-ws-88 \
    --cluster=cluster-cirrus-ws \
    --config=config-cirrus-ws \
    --region=us-west1 \
    apps-luis-fernandez-de-la-vara ${1} \
    --local-host-port=:"${2}"
}

login() {
  echo "Logging into gcloud..."
  gcloud auth login;
}

describe() {
  gcloud alpha workstations describe \
  --project=remote-ws-88 \
  --cluster=cluster-cirrus-ws \
  --config=config-cirrus-ws \
  --region=us-west1 \
  apps-luis-fernandez-de-la-vara;
}

# Call the appropriate function if it's provided as an argument
if [ -n "$1" ]; then
  "$@"
fi
