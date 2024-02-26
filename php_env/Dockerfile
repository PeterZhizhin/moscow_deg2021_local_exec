FROM deg_php_base_context

COPY ./src /app

RUN cd /app && composer install

RUN mkdir /app/storage \
&& mkdir /app/storage/logs \
&& mkdir /app/storage/framework \
&& mkdir /app/storage/framework/cache \
&& mkdir /app/storage/framework/sessions \
&& mkdir /app/storage/framework/smarty \
&& mkdir /app/storage/framework/views

CMD ["/wait-and-create-dependencies.sh", "php", "/app/artisan", "swoole:http", "start"]
