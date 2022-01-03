<?php

return [
    "backurl" => env("APP_URL") . '/got_authorize',
    "login_url" => "http://localhost:8025/oauth/authorize",
    "token_url" => "http://localhost:8025/oauth/token",
    "user_data" => "http://localhost:8025/api/me",
    "client_id" => "deg_client_id",
    "client_secret" => "deg_client_secret",
];
