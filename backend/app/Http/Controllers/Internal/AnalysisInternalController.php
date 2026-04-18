<?php

namespace App\Http\Controllers\Internal;

use App\Http\Controllers\Controller;
use App\Models\Analysis;
use App\Models\AnalysisLog;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\Validation\Rule;
use Symfony\Component\HttpFoundation\BinaryFileResponse;

class AnalysisInternalController extends Controller
{
    public function log(Request $request): JsonResponse
    {
        $normalizedStatus = match ($request->input('status')) {
            'running' => 'processing',
            'error' => 'failed',
            default => $request->input('status'),
        };

        $request->merge([
            'status' => $normalizedStatus,
        ]);

        $validated = $request->validate([
            'analysis_id' => ['required', 'integer', 'exists:analyses,id'],
            'step' => ['required', 'string', 'max:50'],
            'status' => ['required', Rule::in(['pending', 'processing', 'done', 'failed'])],
            'message' => ['nullable', 'string'],
            'metadata_json' => ['nullable', 'array'],
        ]);

        AnalysisLog::create($validated);

        return response()->json([
            'success' => true,
            'message' => 'Analysis log saved.',
        ]);
    }

    public function callback(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'analysis_id' => ['required', 'integer', 'exists:analyses,id'],
            'status' => ['required', Rule::in(['done', 'failed'])],
            'result' => ['nullable', 'array'],
            'error_message' => ['nullable', 'string'],
        ]);

        $analysis = Analysis::query()->findOrFail($validated['analysis_id']);
        $rawErrorMessage = (string) ($validated['error_message'] ?? '');
        $friendlyErrorMessage = $this->toFriendlyErrorMessage($rawErrorMessage);

        if ($validated['status'] === 'done') {
            $result = $validated['result'] ?? [];
            $scoreOverall = data_get($result, 'score_overall');

            $analysis->update([
                'status' => 'done',
                'result_json' => $result,
                'score_overall' => is_numeric($scoreOverall) ? (float) $scoreOverall : null,
                'error_message' => null,
                'completed_at' => now(),
            ]);

            AnalysisLog::create([
                'analysis_id' => $analysis->id,
                'step' => 'done',
                'status' => 'done',
                'message' => 'Analisis selesai dan hasil berhasil disimpan.',
            ]);

            return response()->json([
                'success' => true,
                'message' => 'Analysis callback processed.',
            ]);
        }

        $analysis->update([
            'status' => 'failed',
            'result_json' => null,
            'score_overall' => null,
            'error_message' => $friendlyErrorMessage,
            'completed_at' => now(),
        ]);

        AnalysisLog::create([
            'analysis_id' => $analysis->id,
            'step' => 'failed',
            'status' => 'failed',
            'message' => $friendlyErrorMessage,
            'metadata_json' => $rawErrorMessage !== '' ? [
                'raw_error' => $rawErrorMessage,
            ] : null,
        ]);

        return response()->json([
            'success' => true,
            'message' => 'Analysis callback processed.',
        ]);
    }

    private function toFriendlyErrorMessage(string $rawMessage): string
    {
        $trimmed = trim($rawMessage);

        if ($trimmed === '') {
            return 'Proses analisis gagal. Silakan coba lagi beberapa saat.';
        }

        $lowered = strtolower($trimmed);
        if (str_contains($lowered, 'groq_api_key') || str_contains($lowered, 'api_key client option must be set')) {
            return 'Layanan AI belum terkonfigurasi. Silakan hubungi admin untuk mengatur API key.';
        }

        $firstLine = trim(explode("\n", $trimmed)[0]);

        if (mb_strlen($firstLine) > 220) {
            return mb_substr($firstLine, 0, 217).'...';
        }

        return $firstLine;
    }

    public function file(int $analysis): BinaryFileResponse
    {
        $analysisData = Analysis::query()->findOrFail($analysis);

        abort_unless(
            Storage::disk('local')->exists($analysisData->file_path),
            404,
            'File dokumen tidak ditemukan.'
        );

        return response()->file(
            Storage::disk('local')->path($analysisData->file_path),
            [
                'Content-Type' => 'application/pdf',
                'Content-Disposition' => 'inline; filename="'.basename($analysisData->file_path).'"',
            ]
        );
    }
}
