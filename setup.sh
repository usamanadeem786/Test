#! /bin/bash

set -e

hatch env create
npm install

cp .env.local .env
echo "ENCRYPTION_KEY=$(hatch run python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode('utf-8'), end='')")" >> .env
hatch run python -m auth.cli migrate

set +e
hatch run translations.compile
hatch run python -m auth.cli create-admin --user-email anne@bretagne.duchy --user-password herminetincture
set -e
