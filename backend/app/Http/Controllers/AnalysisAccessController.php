<?php

namespace App\Http\Controllers;

use App\Models\Analysis;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class AnalysisAccessController extends Controller
{
    public function showByCode(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'access_code' => ['required', 'string', 'min:6', 'max:64'],
        ]);

        $hash = hash('sha256', strtoupper(trim($validated['access_code'])));

        $analysis = Analysis::query()
            ->with('user:id,name,email')
            ->where('access_code_hash', $hash)
            ->where('status', 'done')
            ->first();

        if (! $analysis) {
            return response()->json([
                'success' => false,
                'message' => 'Kode akses tidak valid atau hasil analisis belum tersedia.',
            ], 404);
        }

        return response()->json([
            'success' => true,
            'message' => 'Hasil analisis berhasil ditemukan.',
            'data' => [
                'analysis' => [
                    'id' => $analysis->id,
                    'doc_name' => $analysis->doc_name,
                    'doc_type' => $analysis->doc_type,
                    'status' => $analysis->status,
                    'score_overall' => $analysis->score_overall,
                    'result_json' => $analysis->result_json,
                    'completed_at' => $analysis->completed_at,
                    'owner_name' => $analysis->user?->name,
                ],
            ],
        ]);
    }
}
