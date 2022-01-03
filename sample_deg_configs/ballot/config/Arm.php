<?php

return [
    "transport" => "not_ampq",
    "connstring" => "fake_connstring",

    "serviceVoiting" => [
        "ref" => env("ARM_VOITING_REF"),
        "url" => env("ARM_VOITING_URL"),
        "system" => "ballot",
        "token" => "test_token",
    ],
];
