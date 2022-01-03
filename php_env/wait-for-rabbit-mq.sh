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

>&2 echo "Executing command"

exec "$@"
