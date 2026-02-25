<?php
/*
Plugin Name: MassAffect Request Profiler (MU)
Description: Lightweight per-request instrumentation for WordPress.
*/

if (php_sapi_name() === 'cli') {
    return;
}

/* -----------------------------------------------------------
   Enable query timing (only if not already enabled)
----------------------------------------------------------- */
if (!defined('SAVEQUERIES')) {
    define('SAVEQUERIES', true);
}

/* -----------------------------------------------------------
   Correlation ID
----------------------------------------------------------- */

$__ma_request_id = bin2hex(random_bytes(8));
header("X-MA-Request-ID: $__ma_request_id");

/* -----------------------------------------------------------
   Capture request start state
----------------------------------------------------------- */

$__ma_start_time = microtime(true);
$__ma_start_ru   = function_exists('getrusage') ? getrusage() : null;

function __ma_ru_time($ru, $index) {
    return ($ru["ru_{$index}.tv_sec"] * 1e6) + $ru["ru_{$index}.tv_usec"];
}

/* -----------------------------------------------------------
   Shutdown profiler
----------------------------------------------------------- */

function massaffect_send(array $payload) {
    if (!extension_loaded('sockets')) {
        return;
    }

    $sock = @socket_create(AF_UNIX, SOCK_STREAM, 0);
    if ($sock === false) {
        return;
    }

    // Very short timeout (fail fast)
    socket_set_option($sock, SOL_SOCKET, SO_SNDTIMEO, [
        'sec'  => 0,
        'usec' => 200000   // 200ms
    ]);

    $addr = "\0massaffect";

    if (@socket_connect($sock, $addr)) {
        $json = json_encode($payload, JSON_UNESCAPED_SLASHES) . "\n";
        @socket_write($sock, $json, strlen($json));
    }

    socket_close($sock);
}

register_shutdown_function(function () use ($__ma_start_time, $__ma_start_ru, $__ma_request_id) {
    $end_time  = microtime(true);
    $duration  = $end_time - $__ma_start_time;
    $peak_mem  = memory_get_peak_usage(true);

    /* ---------------- CPU ---------------- */

    $cpu_user = null;
    $cpu_sys  = null;
    $cpu_total = null;

    if ($__ma_start_ru && function_exists('getrusage')) {
        $end_ru = getrusage();

        $cpu_user = (__ma_ru_time($end_ru, "utime") - __ma_ru_time($__ma_start_ru, "utime")) / 1e6;
        $cpu_sys  = (__ma_ru_time($end_ru, "stime") - __ma_ru_time($__ma_start_ru, "stime")) / 1e6;
        $cpu_total = $cpu_user + $cpu_sys;
    }

    /* ---------------- DB ---------------- */

    global $wpdb;

    $query_count = function_exists('get_num_queries') ? get_num_queries() : 0;

    $total_query_time = 0.0;
    $slowest_query_time = 0.0;
    $slowest_query_sql = null;

    if (!empty($wpdb->queries)) {
        foreach ($wpdb->queries as $q) {
            $time = (float)$q[1];
            $total_query_time += $time;

            if ($time > $slowest_query_time) {
                $slowest_query_time = $time;
                $slowest_query_sql = substr($q[0], 0, 300);
            }
        }
    }

    /* ---------------- Composition ---------------- */

    $other_time = null;
    if ($cpu_total !== null) {
        $other_time = max(0, $duration - $cpu_total - $total_query_time);
    }

    /* ---------------- Environment ---------------- */

    $theme = null;
    if (function_exists('wp_get_theme')) {
        $t = wp_get_theme();
        $theme = $t ? $t->get('Name') : null;
    }

    $active_plugins = function_exists('get_option') ? get_option('active_plugins') : null;

    /* ---------------- Access-log style fields ---------------- */

    $remote_addr   = $_SERVER['REMOTE_ADDR'] ?? null;
    $forwarded_for = $_SERVER['HTTP_X_FORWARDED_FOR'] ?? null;
    $host          = $_SERVER['HTTP_HOST'] ?? null;
    $protocol      = $_SERVER['SERVER_PROTOCOL'] ?? null;
    $referer       = $_SERVER['HTTP_REFERER'] ?? null;
    $user_agent    = $_SERVER['HTTP_USER_AGENT'] ?? null;
    $content_len   = $_SERVER['CONTENT_LENGTH'] ?? null;

    /* ---------------- Build log entry ---------------- */

    $data = [
        'request_id'     => $__ma_request_id,

        'ts'             => date('c'),
        'remote_addr'    => $remote_addr,
        'forwarded_for'  => $forwarded_for,
        'host'           => $host,
        'method'         => $_SERVER['REQUEST_METHOD'] ?? null,
        'uri'            => $_SERVER['REQUEST_URI'] ?? null,
        'protocol'       => $protocol,
        'status'         => http_response_code(),
        'referer'        => $referer,
        'user_agent'     => $user_agent,
        'content_len'    => $content_len,

        'duration_s'     => round($duration, 6),

        'cpu_user_s'     => $cpu_user,
        'cpu_sys_s'      => $cpu_sys,
        'cpu_total_s'    => $cpu_total,

        'db_time_s'      => round($total_query_time, 6),
        'db_slowest_s'   => round($slowest_query_time, 6),
        'db_slowest_sql' => $slowest_query_sql,

        'other_time_s'   => $other_time,

        'mem_peak_mb'    => round($peak_mem / 1048576, 2),
        'queries'        => $query_count,

        'user_id'        => function_exists('get_current_user_id') ? get_current_user_id() : null,
        'is_admin'       => function_exists('is_admin') ? is_admin() : null,
        'is_ajax'        => defined('DOING_AJAX') && DOING_AJAX,
        'is_rest'        => defined('REST_REQUEST') && REST_REQUEST,

        'wp_version'     => get_bloginfo('version'),
        'theme'          => $theme,
        // 'plugins'        => $active_plugins,
    ];

    // TODO: Decide whether to use massaffect_send()!

    $logfile = WP_CONTENT_DIR . '/massaffect.log';

    error_log(json_encode($data) . PHP_EOL, 3, $logfile);
});

