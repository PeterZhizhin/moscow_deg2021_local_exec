FROM openswoole/swoole:4.12

RUN apt-get update && apt-get install -y git

RUN git clone https://github.com/sjinks/php-stribog && ( \
    cd php-stribog \
    && phpize \
    && ./configure \
    && make -j "$(nproc)" \
    && make install \
) && rm -r php-stribog \ 
&& docker-php-ext-enable stribog

WORKDIR /app

COPY hmac_server.php .

CMD ["php", "hmac_server.php"]
