#!/bin/sh
# wait for rabbit mq

set -e

host=$RABBIT_MQ_HOSTNAME

until nc -z $host 5672 ; do
  >&2 echo "RabbitMQ is unavailable - sleeping"
  sleep 1
done

>&2 echo "Executing command"

exec "$@"
