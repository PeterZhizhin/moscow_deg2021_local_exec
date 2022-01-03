<?php

return [
    "amqp" => [
        "queue" => "mgik_queue",
        "host" => "localhost",
        "port" => "5672",
        "login" => "guest",
        "pass" => "guest",
    ],
    # Секрет формы, должен быть один и тот же в ballot и form
    "cert" => "1d27d4c682afbe95667e6af121911da3a34b5a73800c14aa3e51dc3cbe4bfeb3",
];
