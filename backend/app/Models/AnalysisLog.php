<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

#[Fillable([
    'analysis_id',
    'step',
    'status',
    'message',
    'metadata_json',
])]
class AnalysisLog extends Model
{
    protected $table = 'analysis_logs';

    public const UPDATED_AT = null;

    protected function casts(): array
    {
        return [
            'metadata_json' => 'array',
        ];
    }

    public function analysis(): BelongsTo
    {
        return $this->belongsTo(Analysis::class);
    }
}
