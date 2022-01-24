<?php

return [
    "source" => "Doesn't matter",
    "timeout" => 60,
    "token" => env('TELEGRAM_BOT_SECRET'),
    "url" => env("SUDIR_SEND_TELEGRAM_MESSAGE_URL"),
];
