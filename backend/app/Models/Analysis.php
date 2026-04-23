<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

#[Fillable([
    'user_id',
    'doc_name',
    'doc_type',
    'file_path',
    'status',
    'task_id',
    'access_code_hash',
    'access_code_sent_at',
    'result_json',
    'score_overall',
    'error_message',
    'completed_at',
])]
class Analysis extends Model
{
    protected function casts(): array
    {
        return [
            'result_json' => 'array',
            'score_overall' => 'decimal:2',
            'access_code_sent_at' => 'datetime',
            'completed_at' => 'datetime',
        ];
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function feedbacks(): HasMany
    {
        return $this->hasMany(Feedback::class);
    }

    public function logs(): HasMany
    {
        return $this->hasMany(AnalysisLog::class);
    }
}
