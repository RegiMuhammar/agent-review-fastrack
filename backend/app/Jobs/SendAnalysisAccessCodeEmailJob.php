<?php

namespace App\Jobs;

use App\Mail\AnalysisAccessCodeMail;
use App\Models\Analysis;
use App\Models\AnalysisLog;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\Mail;

class SendAnalysisAccessCodeEmailJob implements ShouldQueue
{
    use Queueable;

    public int $tries = 3;

    public int $timeout = 60;

    public function __construct(
        public int $analysisId,
        public string $accessCode,
    ) {
    }

    public function handle(): void
    {
        $analysis = Analysis::query()->with('user')->find($this->analysisId);

        if (! $analysis || ! $analysis->user?->email) {
            return;
        }

        $frontendUrl = rtrim((string) config('services.frontend.url'), '/');
        $resultUrl = $frontendUrl !== '' ? $frontendUrl.'/buka-hasil' : null;

        Mail::to($analysis->user->email)->send(new AnalysisAccessCodeMail(
            analysis: $analysis,
            accessCode: $this->accessCode,
            resultUrl: $resultUrl,
        ));

        $analysis->update([
            'access_code_sent_at' => now(),
        ]);

        AnalysisLog::create([
            'analysis_id' => $analysis->id,
            'step' => 'notify_email',
            'status' => 'done',
            'message' => 'Kode akses hasil analisis berhasil dikirim ke email user.',
        ]);
    }

    public function failed(\Throwable $exception): void
    {
        AnalysisLog::create([
            'analysis_id' => $this->analysisId,
            'step' => 'notify_email',
            'status' => 'failed',
            'message' => 'Gagal mengirim kode akses ke email user.',
            'metadata_json' => [
                'error' => $exception->getMessage(),
            ],
        ]);
    }
}
