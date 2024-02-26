#!/bin/sh
# wait for rabbit mq

set -e

host=$AMQP_HOST
need_wait=${WAIT_FOR_AMQP:-false}

if [ $need_wait = true ] ; then
  until nc -z $host 5672 ; do
    >&2 echo "RabbitMQ is unavailable - sleeping"
    sleep 1
  done
fi

need_migrate=${RUN_MIGRATIONS:-false}
migrations_file=$CHECK_MIGRATIONS_FILE
if [ $need_migrate = true ]; then
  if [ -z "$migrations_file" ]; then
    >&2 echo "migrations file is not specified, set CHECK_MIGRATIONS_FILE env variable"
    exit 1
  fi
  >&2 echo "Checking if sentinel file is present"
  if test -f "$migrations_file"; then
    >&2 echo "migration file exists, skipping migrations"
  else
    >&2 echo "migration file does not exist, running migrations"
    php /app/artisan migrate:fresh --force

    >&2 echo "migration done, touching migrations file"
    touch $migrations_file
  fi
fi

>&2 echo "Executing command"

exec "$@"
