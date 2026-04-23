<?php

namespace App\Mail;

use App\Models\Analysis;
use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Mail\Mailables\Content;
use Illuminate\Mail\Mailables\Envelope;

class AnalysisAccessCodeMail extends Mailable
{
    use Queueable;

    public function __construct(
        public Analysis $analysis,
        public string $accessCode,
        public ?string $resultUrl = null,
    ) {
    }

    public function envelope(): Envelope
    {
        return new Envelope(
            subject: 'Kode Akses Hasil Analisis Jurnal',
        );
    }

    public function content(): Content
    {
        return new Content(
            view: 'emails.analysis-access-code',
            with: [
                'analysis' => $this->analysis,
                'accessCode' => $this->accessCode,
                'resultUrl' => $this->resultUrl,
            ],
        );
    }
}
