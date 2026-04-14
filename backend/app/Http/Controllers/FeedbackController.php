<?php

namespace App\Http\Controllers;

use App\Models\Analysis;
use App\Models\Feedback;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class FeedbackController extends Controller
{
    public function publicIndex(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'page' => ['nullable', 'integer', 'min:1'],
            'limit' => ['nullable', 'integer', 'min:3', 'max:24'],
        ]);

        $page = (int) ($validated['page'] ?? 1);
        $limit = (int) ($validated['limit'] ?? 6);

        $paginator = Feedback::query()
            ->with('user:id,name')
            ->latest('created_at')
            ->paginate($limit, ['*'], 'page', $page);

        $feedbacks = collect($paginator->items())
            ->map(function (Feedback $feedback): array {
                return [
                    'name' => $feedback->user?->name ?? 'Pengguna',
                    'rating' => $feedback->rating,
                    'comment' => $feedback->comment,
                ];
            })
            ->values();

        return response()->json([
            'success' => true,
            'message' => 'Daftar feedback publik berhasil diambil.',
            'data' => [
                'feedbacks' => $feedbacks,
                'pagination' => [
                    'current_page' => $paginator->currentPage(),
                    'last_page' => $paginator->lastPage(),
                    'per_page' => $paginator->perPage(),
                    'total' => $paginator->total(),
                    'has_more_pages' => $paginator->hasMorePages(),
                ],
            ],
        ]);
    }

    public function store(Request $request, int $analysis): JsonResponse
    {
        $validated = $request->validate([
            'rating' => ['required', 'integer', 'between:1,5'],
            'comment' => ['nullable', 'string', 'max:2000'],
        ]);

        $analysisData = Analysis::query()
            ->where('user_id', $request->user()->id)
            ->whereKey($analysis)
            ->firstOrFail();

        $feedback = Feedback::query()->updateOrCreate(
            [
                'analysis_id' => $analysisData->id,
                'user_id' => $request->user()->id,
            ],
            [
                'rating' => $validated['rating'],
                'comment' => $validated['comment'] ?? null,
            ]
        );

        $statusCode = $feedback->wasRecentlyCreated ? 201 : 200;

        return response()->json([
            'success' => true,
            'message' => 'Feedback berhasil disimpan.',
            'data' => [
                'feedback' => $feedback,
            ],
        ], $statusCode);
    }

    public function index(Request $request, int $analysis): JsonResponse
    {
        $analysisData = Analysis::query()
            ->where('user_id', $request->user()->id)
            ->whereKey($analysis)
            ->firstOrFail();

        $feedbacks = Feedback::query()
            ->where('analysis_id', $analysisData->id)
            ->with(['user:id,name,email'])
            ->latest('created_at')
            ->get();

        return response()->json([
            'success' => true,
            'message' => 'Daftar feedback berhasil diambil.',
            'data' => [
                'analysis_id' => $analysisData->id,
                'feedbacks' => $feedbacks,
            ],
        ]);
    }
}
