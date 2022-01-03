<?php

return [
    # Параметры подключения RabbitMQ
    "amqp" => [
        "queue" => "mgik_queue",
        "host" => "localhost",
        "port" => "5672",
        "login" => "guest",
        "pass" => "guest",
    ],
    # host для сервиса ballot, порт задаётся через .env переменную BALLOT_EXTERNAL_PORT
    "host" => "http://localhost",
    "url" => "http://localhost:8003/ballot/getGuid",

    # Если false, то всегда разрешает пользователю переголосовать (?)
    # То есть, снимается ограничение на время. Полезно для дебага.
    "lock_enabled" => false,

    # Подпись формы, должен быть один и тот же в ballot и form
    # В ballot указывается внутри config/Encryption.php
    "cert" => "1d27d4c682afbe95667e6af121911da3a34b5a73800c14aa3e51dc3cbe4bfeb3",

    # Секрет Mpgu, им в form подписывается hashGroup mpgu внутри getGuid
    # Потом проверяется в ballot, что правильно подписалось с этим секретом.
    #
    # Должна совпадать с FORM_SECRET в .env ballot.
    "secret" => "5af588cc4cafc09fb1ad845671d80f7ce4ad52c980d57c977baf32b102f9d793",

    # system_auth:get_guid внутри ballot/config/SystemAuth.php
    "system" => "TestSystem",
    "system_token" => "TOKEN_SECRET",
];
