<?php

namespace App\Jobs;

use App\Models\Analysis;
use App\Models\AnalysisLog;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\Http;

class TriggerAiReviewJob implements ShouldQueue
{
    use Queueable;

    public int $tries = 1;

    public int $timeout = 120;

    public function __construct(public int $analysisId)
    {
    }

    public function handle(): void
    {
        $analysis = Analysis::query()->find($this->analysisId);

        if (! $analysis) {
            return;
        }

        if (in_array($analysis->status, ['done', 'failed'], true)) {
            return;
        }

        $analysis->update([
            'status' => 'processing',
            'error_message' => null,
        ]);

        AnalysisLog::create([
            'analysis_id' => $analysis->id,
            'step' => 'queue_dispatch',
            'status' => 'processing',
            'message' => 'Mengirim dokumen ke AI Agent untuk diproses.',
        ]);

        $internalBaseUrl = rtrim((string) config('services.internal.base_url'), '/');
        $fileUrl = $internalBaseUrl.'/api/v1/internal/analyses/'.$analysis->id.'/file';

        $aiAgentUrl = rtrim((string) config('services.ai_agent.url'), '/');

        try {
            $timeout = (int) config('services.ai_agent.timeout', 600);
            $response = Http::acceptJson()
                ->connectTimeout(15)
                ->timeout($timeout)
                ->withHeaders([
                    'X-Internal-Key' => (string) config('services.internal.key'),
                ])
                ->post($aiAgentUrl.'/api-agent/evaluate', [
                    'analysis_id' => (string) $analysis->id,
                    'doc_type' => $analysis->doc_type,
                    'file_url' => $fileUrl,
                ]);

            if (! $response->successful()) {
                throw new \RuntimeException('AI Agent request failed: '.$response->status());
            }

            $taskId = data_get($response->json(), 'task_id');

            if (! is_string($taskId) || trim($taskId) === '') {
                throw new \RuntimeException('AI Agent response missing valid task_id.');
            }

            $analysis->update([
                'task_id' => $taskId,
            ]);

            AnalysisLog::create([
                'analysis_id' => $analysis->id,
                'step' => 'queue_dispatch',
                'status' => 'done',
                'message' => 'Dokumen berhasil masuk antrean AI Agent.',
            ]);
        } catch (\Throwable $exception) {
            $analysis->update([
                'status' => 'failed',
                'error_message' => $exception->getMessage(),
                'completed_at' => now(),
            ]);

            AnalysisLog::create([
                'analysis_id' => $analysis->id,
                'step' => 'queue_dispatch',
                'status' => 'failed',
                'message' => 'Gagal mengirim dokumen ke AI Agent.',
                'metadata_json' => [
                    'error' => $exception->getMessage(),
                ],
            ]);
        }
    }
}
