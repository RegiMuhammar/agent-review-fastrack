<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

#[Fillable([
    'user_id',
    'doc_name',
    'doc_type',
    'file_path',
    'status',
    'task_id',
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
            'completed_at' => 'datetime',
        ];
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }
}
