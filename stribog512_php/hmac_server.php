<?php

use Swoole\Http\Server as HttpServer;
use Swoole\Http\Request as Request;
use Swoole\Http\Response as Response;

// Function to handle HMAC-STRIBOG512 hashing
function stribogHmac($data, $secret) {
  return hash_hmac('stribog512', $data, $secret);
}

$port = getenv('PORT') ?: 8080;

// Start the Swoole server
$server = new HttpServer("0.0.0.0", $port);

// Handle incoming requests
$server->on('request', function (Request $request, Response $response) {
  $inputData = $request->post['data'] ?? ''; // Get data from POST request
  $inputSecret = $request->post['secret']; // Get secret from POST request

  // Validate input data presence
  if (empty($inputData)) {
    $response->status = 400;
    $response->end('Missing data in request');
    return;
  }

  // Perform HMAC-STRIBOG512 hashing
  $hash = stribogHmac($inputData, $inputSecret);
  $response->end($hash);
});

// Start the server
$server->start();

?>

