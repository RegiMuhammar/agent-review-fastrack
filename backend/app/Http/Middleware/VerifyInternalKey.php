<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;

class VerifyInternalKey
{
    public function handle(Request $request, Closure $next): mixed
    {
        $internalKey = $request->header('X-Internal-Key');
        $expectedKey = config('services.internal.key');

        if (! is_string($expectedKey) || $expectedKey === '' || $internalKey !== $expectedKey) {
            return response()->json([
                'success' => false,
                'message' => 'Unauthorized internal request.',
            ], 401);
        }

        return $next($request);
    }
}
