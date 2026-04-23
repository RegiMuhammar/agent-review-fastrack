<?php

use App\Http\Controllers\AuthController;
use App\Http\Controllers\AnalysisController;
use App\Http\Controllers\AnalysisAccessController;
use App\Http\Controllers\FeedbackController;
use App\Http\Controllers\Internal\AnalysisInternalController;
use Illuminate\Support\Facades\Route;

Route::prefix('v1')->group(function () {
    Route::get('/feedbacks', [FeedbackController::class, 'publicIndex']);
    Route::post('/analysis/access', [AnalysisAccessController::class, 'showByCode']);

    Route::middleware('internal.key')->prefix('internal')->group(function () {
        Route::get('/analyses/{analysis}/file', [AnalysisInternalController::class, 'file']);
        Route::post('/analysis/log', [AnalysisInternalController::class, 'log']);
        Route::post('/analysis/callback', [AnalysisInternalController::class, 'callback']);
    });

    Route::prefix('auth')->group(function () {
        Route::post('/register', [AuthController::class, 'register']);
        Route::post('/login', [AuthController::class, 'login']);

        Route::middleware('auth:sanctum')->group(function () {
            Route::post('/logout', [AuthController::class, 'logout']);
            Route::get('/me', [AuthController::class, 'me']);
            Route::put('/profile', [AuthController::class, 'updateProfile']);

            Route::get('/analyses', [AnalysisController::class, 'index']);
            Route::post('/analyses', [AnalysisController::class, 'store']);
            Route::get('/analyses/{analysis}', [AnalysisController::class, 'show']);
            Route::get('/analyses/{analysis}/logs', [AnalysisController::class, 'logs']);
            Route::get('/analyses/{analysis}/file', [AnalysisController::class, 'file']);
            Route::delete('/analyses/{analysis}', [AnalysisController::class, 'destroy']);

            Route::post('/analysis/{analysis}/feedback', [FeedbackController::class, 'store']);
            Route::get('/analysis/{analysis}/feedback', [FeedbackController::class, 'index']);
        });
    });
});
